from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import shutil

import numpy as np
import pandas as pd

from .alignment.nearest import nearest_time_mapping
from .calibration.audit import audit_residual_table
from .calibration.control_points import read_control_points, validate_control_points
from .imu.filtering import filter_contiguous_segments
from .io.trc import read_trc


KEYPOINTS_26 = (
    "Nose", "LEye", "REye", "LEar", "REar", "LShoulder", "RShoulder",
    "LElbow", "RElbow", "LWrist", "RWrist", "LHip", "RHip", "LKnee",
    "RKnee", "LAnkle", "RAnkle", "Head", "Neck", "Hip", "LBigToe",
    "RBigToe", "LSmallToe", "RSmallToe", "LHeel", "RHeel",
)
SYNC_SOURCE_OFFSETS = {"cam01": 0, "cam02": 5, "cam03": 9, "cam04": 14}
DEVICES = ("WTLhand", "WTLknee", "WTRhand", "WTRknee")
ACC_COLUMNS = ("加速度X(g)", "加速度Y(g)", "加速度Z(g)")
GYRO_COLUMNS = ("角速度X(°/s)", "角速度Y(°/s)", "角速度Z(°/s)")


@dataclass(frozen=True)
class TrialSelection:
    action: str = "A10"
    repeat: int = 10
    start_frame: int = 3979
    end_frame: int = 4181
    visual_rate_hz: float = 60.0

    @property
    def trial_id(self) -> str:
        return f"{self.action}-R{self.repeat:02d}"


def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _export_2d(project: Path, selection: TrialSelection, output: Path) -> dict[str, object]:
    records: list[dict[str, object]] = []
    source_hashes: dict[str, str] = {}
    for camera, offset in SYNC_SOURCE_OFFSETS.items():
        camera_dir = project / selection.action / "pose-sync" / f"{camera}_json"
        source_dir = project / selection.action / "pose" / f"{camera}_json"
        aggregate = sha256()
        for sync_frame in range(selection.start_frame, selection.end_frame + 1):
            path = camera_dir / f"{camera}_{sync_frame:06d}.json"
            raw = path.read_bytes()
            source_path = source_dir / f"{camera}_{sync_frame + offset:06d}.json"
            if raw != source_path.read_bytes():
                raise ValueError(
                    f"Locked synchronization offset failed for {camera} at frame {sync_frame}"
                )
            aggregate.update(raw)
            payload = json.loads(raw)
            people = payload.get("people", [])
            values = people[0].get("pose_keypoints_2d", []) if people else []
            if len(values) != len(KEYPOINTS_26) * 3:
                raise ValueError(f"Expected 26 keypoints in {path}; found {len(values) // 3}")
            relative_frame = sync_frame - selection.start_frame
            for index, name in enumerate(KEYPOINTS_26):
                records.append({
                    "trial_id": selection.trial_id, "camera": camera,
                    "sync_frame": sync_frame, "source_frame": sync_frame + offset,
                    "relative_frame": relative_frame,
                    "relative_time_s": relative_frame / selection.visual_rate_hz,
                    "keypoint_id": index, "keypoint": name,
                    "x_px": values[index * 3], "y_px": values[index * 3 + 1],
                    "confidence": values[index * 3 + 2],
                })
        source_hashes[camera] = aggregate.hexdigest()
    frame = pd.DataFrame(records)
    path = output / "visual" / "keypoints_2d.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")
    return {
        "rows": len(frame),
        "frames_per_camera": selection.end_frame - selection.start_frame + 1,
        "keypoints": len(KEYPOINTS_26),
        "sync_to_source_frame_offsets": SYNC_SOURCE_OFFSETS,
        "offset_mapping_verified_by_exact_file_content": True,
        "selected_source_content_sha256": source_hashes,
    }


def _export_3d(project: Path, selection: TrialSelection, output: Path) -> dict[str, object]:
    source = project / selection.action / "pose-3d" / f"{selection.action}_1-5024_filt_butterworth.trc"
    wide = read_trc(source)
    selected = wide.loc[(wide["Frame"] >= selection.start_frame) & (wide["Frame"] <= selection.end_frame)].copy()
    if len(selected) != selection.end_frame - selection.start_frame + 1:
        raise ValueError("The selected 3D frame interval is incomplete")
    marker_names = [column[:-2] for column in wide.columns if column.endswith("_X")]
    records: list[dict[str, object]] = []
    for _, row in selected.iterrows():
        source_frame = int(row["Frame"])
        relative_frame = source_frame - selection.start_frame
        for marker in marker_names:
            records.append({
                "trial_id": selection.trial_id, "source_frame": source_frame,
                "relative_frame": relative_frame,
                "relative_time_s": relative_frame / selection.visual_rate_hz,
                "keypoint": marker, "x_m": row[f"{marker}_X"],
                "y_m": row[f"{marker}_Y"], "z_m": row[f"{marker}_Z"],
            })
    result = pd.DataFrame(records)
    path = output / "visual" / "keypoints_3d_filtered.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(path, index=False, encoding="utf-8")
    return {
        "rows": len(result), "frames": len(selected), "markers": len(marker_names),
        "units": "m", "filter": "Pose2Sim fourth-order zero-phase Butterworth, 6 Hz",
        "source_sha256": _hash(source),
    }


def _interpolate_gap_limited(time: np.ndarray, values: np.ndarray, target: np.ndarray) -> np.ndarray:
    valid = np.isfinite(time) & np.isfinite(values)
    if valid.sum() < 2:
        return np.full(len(target), np.nan)
    grouped = pd.DataFrame({"time": time[valid], "value": values[valid]}).groupby(
        "time", as_index=False, sort=True
    )["value"].mean()
    source_time = grouped["time"].to_numpy(dtype=float)
    source_values = grouped["value"].to_numpy(dtype=float)
    result = np.interp(target, source_time, source_values)
    result[(target < source_time[0]) | (target > source_time[-1])] = np.nan
    for index in np.flatnonzero(np.diff(source_time) > 0.12):
        result[(target > source_time[index]) & (target < source_time[index + 1])] = np.nan
    return result


def _export_imu(project: Path, mapping_row: pd.Series, output: Path) -> dict[str, object]:
    start = float(mapping_row["IMUStartTime_50Hz_s"])
    end = float(mapping_row["IMUEndTime_50Hz_s"])
    target = np.arange(start, end + 0.01, 0.02)
    records: list[dict[str, object]] = []
    source_hashes: dict[str, str] = {}
    for device in DEVICES:
        source = project / "P01_IMU_Merged" / f"P01_{device}_merged.csv"
        data = pd.read_csv(source, low_memory=False)
        source_time = pd.to_numeric(data["SessionTime_s"], errors="coerce").to_numpy(dtype=float)
        channels: dict[str, np.ndarray] = {}
        for column in (*ACC_COLUMNS, *GYRO_COLUMNS):
            values = pd.to_numeric(data[column], errors="coerce").to_numpy(dtype=float)
            resampled = _interpolate_gap_limited(source_time, values, target)
            filtered, _ = filter_contiguous_segments(resampled, sampling_rate_hz=50.0, cutoff_hz=10.0, order=4)
            channels[column] = filtered
        acc = np.column_stack([channels[column] for column in ACC_COLUMNS])
        gyro = np.column_stack([channels[column] for column in GYRO_COLUMNS])
        for index, absolute_time in enumerate(target):
            valid = bool(np.isfinite(acc[index]).all() and np.isfinite(gyro[index]).all())
            records.append({
                "trial_id": "A10-R10", "device": device, "sample": index,
                "relative_time_s": round(float(absolute_time - start), 9), "valid": valid,
                "acc_x_g": acc[index, 0], "acc_y_g": acc[index, 1], "acc_z_g": acc[index, 2],
                "gyro_x_deg_s": gyro[index, 0], "gyro_y_deg_s": gyro[index, 1],
                "gyro_z_deg_s": gyro[index, 2],
                "dynamic_acceleration_proxy_g": abs(np.linalg.norm(acc[index]) - 1.0) if valid else np.nan,
                "gyro_magnitude_deg_s": np.linalg.norm(gyro[index]) if valid else np.nan,
            })
        source_hashes[device] = _hash(source)
    frame = pd.DataFrame(records)
    path = output / "imu" / "imu_50hz_filtered.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")
    return {
        "rows": len(frame), "samples_per_device": len(target), "rate_hz": 50.0,
        "filter": "fourth-order zero-phase Butterworth, 10 Hz; gaps >0.12 s not interpolated",
        "source_sha256": source_hashes,
    }


def export_a10_r10(project_root: str | Path, output_dir: str | Path) -> dict[str, object]:
    project, output = Path(project_root), Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    selection = TrialSelection()
    mapping_path = project / "P01_IMU_Alignment" / "P01_visual_IMU_repetition_mapping.csv"
    mapping = pd.read_csv(mapping_path)
    selected = mapping.loc[(mapping["Trial"] == selection.action) & (mapping["Repeat"] == selection.repeat)]
    if len(selected) != 1:
        raise ValueError("Expected exactly one A10 repeat-10 mapping row")
    mapping_row = selected.iloc[0]
    if int(mapping_row["StartFrame"]) != selection.start_frame or int(mapping_row["EndFrame"]) != selection.end_frame:
        raise ValueError("A10-R10 frame interval does not match the locked selection")

    calibration_dir = output / "calibration"
    calibration_dir.mkdir(parents=True, exist_ok=True)
    calibration_sources = {
        "Calib_scene.toml": project / "calibration" / "Calib_scene.toml",
        "Image_points.json": project / "calibration" / "Image_points.json",
        "Object_points.trc": project / "calibration" / "Object_points.trc",
        "scene_points_click_order.csv": project / "calibration" / "scene_points_click_order.csv",
        "extrinsics_point_residuals.csv": project / "calibration" / "extrinsics_point_residuals.csv",
    }
    calibration_hashes: dict[str, str] = {}
    for name, source in calibration_sources.items():
        shutil.copy2(source, calibration_dir / name)
        calibration_hashes[name] = _hash(source)
    point_audit = validate_control_points(read_control_points(calibration_sources["scene_points_click_order.csv"]))
    residual_summary, residual_audit = audit_residual_table(calibration_sources["extrinsics_point_residuals.csv"])
    residual_summary.to_csv(calibration_dir / "residual_summary.csv", index=False, encoding="utf-8")
    _write_json(calibration_dir / "residual_audit.json", residual_audit)

    two_d = _export_2d(project, selection, output)
    three_d = _export_3d(project, selection, output)
    imu = _export_imu(project, mapping_row, output)
    visual_time = np.arange(selection.end_frame - selection.start_frame + 1) / 60.0
    imu_time = np.arange(int(mapping_row["IMUSamples_50Hz"])) / 50.0
    nearest, nearest_audit = nearest_time_mapping(visual_time, imu_time)
    nearest.insert(0, "trial_id", selection.trial_id)
    nearest.insert(1, "relative_visual_frame", np.arange(len(nearest)))
    nearest.to_csv(output / "visual_imu_time_mapping.csv", index=False, encoding="utf-8")

    metrics_source = project / "P01_IMU_Alignment" / "P01_IMU_repetition_metrics.csv"
    metrics = pd.read_csv(metrics_source)
    metrics = metrics.loc[(metrics["Trial"] == "A10") & (metrics["Repeat"] == 10)].copy()
    metrics = metrics.drop(columns=["Participant", "IMUStartTime_s", "IMUEndTime_s"], errors="ignore")
    metrics.insert(0, "trial_id", selection.trial_id)
    metrics.to_csv(output / "imu" / "repetition_metrics.csv", index=False, encoding="utf-8")

    metadata = {
        "schema_version": "1.0", "trial_id": selection.trial_id,
        "action": "A10", "repeat": 10,
        "participant_scope": "single consenting author-participant",
        "visual": {
            "synchronized_frame_interval_inclusive": [selection.start_frame, selection.end_frame],
            "frames": selection.end_frame - selection.start_frame + 1,
            "rate_hz": 60.0, "duration_s": (selection.end_frame - selection.start_frame) / 60.0,
            "two_dimensional": two_d, "three_dimensional": three_d,
        },
        "visual_imu_alignment": {
            "formula": "imu_time_s = offset_s + scale * visual_time_s",
            "offset_s": float(mapping_row["MappingOffset_s"]),
            "scale": float(mapping_row["TimeScale_IMU_per_Visual"]),
            "clock_drift_percent": (float(mapping_row["TimeScale_IMU_per_Visual"]) - 1.0) * 100,
            "maximum_correlation": float(mapping_row["MaxCorrelation"]),
            "correlation_margin": float(mapping_row["CorrelationMargin"]),
            "status": str(mapping_row["MappingStatus"]), "nearest_sample_audit": nearest_audit,
        },
        "imu": imu,
        "calibration": {
            "control_point_audit": point_audit, "pixel_residual_audit": residual_audit,
            "source_sha256": calibration_hashes,
            "accuracy_boundary": "Pixel residuals do not establish centimetre-level 3D accuracy; independent held-out spatial validation is still required.",
        },
        "privacy": "No names, raw host paths, raw IMU dumps or additional participant trials are included.",
    }
    _write_json(output / "metadata.json", metadata)
    files = sorted(path for path in output.rglob("*") if path.is_file() and path.name != "checksums.sha256")
    checksum_lines = [f"{_hash(path)}  {path.relative_to(output).as_posix()}" for path in files]
    (output / "checksums.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    return {
        "status": "PASS", "trial_id": selection.trial_id, "output_dir": output.as_posix(),
        "published_files": len(files) + 1, "calibration_status": point_audit["status"],
        "pixel_residual_status": residual_audit["status"],
        "nearest_mapping_status": nearest_audit["status"],
    }
