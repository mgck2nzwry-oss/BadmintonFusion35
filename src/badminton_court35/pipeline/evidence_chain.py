"""Trial-level evidence-chain audit for a four-camera visual--IMU recording.

The module deliberately distinguishes *verified existing outputs* from a new
Pose2Sim execution.  It creates an auditable evidence record; it never turns
pixel residuals into a claim of centimetre-level spatial accuracy.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd

from ..calibration.audit import audit_residual_table
from ..calibration.control_points import read_control_points, validate_control_points
from ..io.trc import read_trc


CAMERAS = ("cam01", "cam02", "cam03", "cam04")
SYNC_PATTERN = re.compile(
    r"--> Camera cam01 and (cam0[234]):\s*(-?\d+) frames offset .*?correlation\s+([0-9]+(?:\.[0-9]+)?)",
    re.IGNORECASE,
)


def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _identity(path: Path, *, checksum: bool = False) -> dict[str, Any]:
    item: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
    if path.is_file():
        stats = path.stat()
        item.update({"bytes": stats.st_size, "modified_utc": pd.Timestamp(stats.st_mtime, unit="s", tz="UTC").isoformat()})
        if checksum:
            item["sha256"] = _hash(path)
    return item


def _stage(identifier: str, status: str, detail: dict[str, Any]) -> dict[str, Any]:
    return {"id": identifier, "status": status, **detail}


def _mapping(project: Path, action: str, repeat: int) -> pd.Series:
    source = project / "P01_IMU_Alignment" / "P01_visual_IMU_repetition_mapping.csv"
    mapping = pd.read_csv(source, low_memory=False)
    selected = mapping.loc[(mapping["Trial"].astype(str) == action) & (mapping["Repeat"].astype(int) == repeat)]
    if len(selected) != 1:
        raise ValueError(f"Expected one visual--IMU mapping row for {action} repeat {repeat}; found {len(selected)}")
    return selected.iloc[0]


def _final_sync_offsets(log_path: Path) -> dict[str, Any]:
    matches = SYNC_PATTERN.findall(log_path.read_text(encoding="utf-8", errors="replace"))
    latest: dict[str, tuple[int, float]] = {}
    for camera, offset, correlation in matches:
        latest[camera.lower()] = (int(offset), float(correlation))
    missing = sorted(set(CAMERAS[1:]) - set(latest))
    return {
        "status": "PASS" if not missing else "FAIL",
        "camera01_reference_offsets_frames": {"cam01": 0, **{camera: latest[camera][0] for camera in latest}},
        "correlations": {camera: latest[camera][1] for camera in latest},
        "missing_cameras": missing,
        "source": _identity(log_path),
        "rule": "The last complete cam01-referenced synchronization block in the Pose2Sim log is retained.",
    }


def _pose_2d(project: Path, action: str, start_frame: int, end_frame: int) -> dict[str, Any]:
    by_camera: dict[str, Any] = {}
    expected = end_frame - start_frame + 1
    for camera in CAMERAS:
        folder = project / action / "pose-sync" / f"{camera}_json"
        valid_frames = 0
        detections = 0
        confidence_values: list[float] = []
        for frame in range(start_frame, end_frame + 1):
            source = folder / f"{camera}_{frame:06d}.json"
            if not source.is_file():
                continue
            valid_frames += 1
            payload = json.loads(source.read_text(encoding="utf-8"))
            people = payload.get("people", [])
            if not people:
                continue
            keypoints = people[0].get("pose_keypoints_2d", [])
            if len(keypoints) >= 3:
                detections += 1
                confidence_values.extend(float(value) for value in keypoints[2::3] if np.isfinite(float(value)))
        coverage = valid_frames / expected if expected else 0.0
        by_camera[camera] = {
            "json_frames_present": valid_frames,
            "expected_frames": expected,
            "frame_coverage": round(coverage, 6),
            "person_detected_frames": detections,
            "mean_keypoint_confidence": round(float(np.mean(confidence_values)), 6) if confidence_values else None,
        }
    status = "PASS" if all(item["frame_coverage"] == 1.0 and item["person_detected_frames"] > 0 for item in by_camera.values()) else "FAIL"
    return _stage("pose2d_existing_output", status, {
        "verification_type": "EXISTING_POSE2SIM_OUTPUT_VERIFIED_NOT_RERUN",
        "cameras": by_camera,
        "source_directory": str(project / action / "pose-sync"),
    })


def _trc_3d(project: Path, action: str, start_frame: int, end_frame: int) -> dict[str, Any]:
    candidates = sorted((project / action / "pose-3d").glob("*_filt_butterworth.trc"))
    if not candidates:
        raise FileNotFoundError(f"No filtered Pose2Sim TRC was found for {action}")
    source = candidates[0]
    frame = read_trc(source)
    selected = frame.loc[(frame["Frame"] >= start_frame) & (frame["Frame"] <= end_frame)].copy()
    expected = end_frame - start_frame + 1
    coordinate_columns = [column for column in selected.columns if column.endswith(("_X", "_Y", "_Z"))]
    finite_fraction = float(np.isfinite(selected[coordinate_columns].to_numpy(dtype=float)).mean()) if coordinate_columns and len(selected) else 0.0
    required = {"RHip_X", "RKnee_X", "RAnkle_X", "RWrist_X"}
    missing = sorted(required - set(selected.columns))
    return _stage("triangulation_and_filtering_existing_output", "PASS" if len(selected) == expected and not missing else "FAIL", {
        "verification_type": "EXISTING_POSE2SIM_OUTPUT_VERIFIED_NOT_RERUN",
        "source": _identity(source, checksum=True),
        "frames": int(len(selected)), "expected_frames": expected,
        "coordinate_columns": len(coordinate_columns), "finite_coordinate_fraction": round(finite_fraction, 6),
        "required_marker_columns_missing": missing,
        "filter_record": "Existing filtered TRC; its provenance is retained in the Pose2Sim log/configuration.",
    })


def _imu_alignment(project: Path, row: pd.Series) -> dict[str, Any]:
    source = project / "P01_IMU_Alignment" / "P01_IMU_50Hz_alignment_preview.csv"
    data = pd.read_csv(source, low_memory=False)
    start, end = float(row["MappedIMUStart_s"]), float(row["MappedIMUEnd_s"])
    selected = data.loc[(pd.to_numeric(data["SessionTime_s"], errors="coerce") >= start) & (pd.to_numeric(data["SessionTime_s"], errors="coerce") <= end)]
    sample_target = int(row["IMUSamples_50Hz"])
    status = "PASS" if str(row.get("AlignmentStatus", row.get("MappingStatus", ""))).upper() == "OK" and len(selected) == sample_target else "REVIEW_REQUIRED"
    return _stage("visual_imu_alignment", status, {
        "source": _identity(source, checksum=True),
        "formula": "imu_time_s = mapping_offset_s + time_scale * visual_time_s",
        "mapping_offset_s": float(row["MappingOffset_s"]),
        "time_scale": float(row["TimeScale_IMU_per_Visual"]),
        "maximum_correlation": float(row["MaxCorrelation"]),
        "correlation_margin": float(row["CorrelationMargin"]),
        "alignment_status": str(row.get("AlignmentStatus", row.get("MappingStatus", ""))),
        "selected_preview_samples": int(len(selected)), "expected_50hz_samples": sample_target,
        "selected_imu_interval_s": [start, end],
    })


def build_evidence_chain(
    project_root: str | Path,
    output_dir: str | Path,
    *,
    action: str = "A01",
    repeat: int = 1,
) -> dict[str, Any]:
    """Audit the observed evidence chain for one already processed trial."""
    project, output = Path(project_root).resolve(), Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    row = _mapping(project, action, repeat)
    start_frame, end_frame = int(row["StartFrame"]), int(row["EndFrame"])
    calibration = project / "calibration"
    control_csv = calibration / "scene_points_click_order.csv"
    control_trc = calibration / "Object_points.trc"
    residuals = calibration / "extrinsics_point_residuals.csv"
    points = validate_control_points(read_control_points(control_csv))
    residual_summary, residual_report = audit_residual_table(residuals)
    residual_summary.to_csv(output / "calibration_residual_summary.csv", index=False, encoding="utf-8-sig")
    sync_detail = _final_sync_offsets(project / action / "logs.txt")
    stages = [
        _stage("raw_four_camera_inputs", "PASS" if all((project / action / "videos" / f"{camera}.mp4").is_file() for camera in CAMERAS) else "FAIL", {
            "videos": [_identity(project / action / "videos" / f"{camera}.mp4") for camera in CAMERAS],
            "recording_rate_hz": 60.0,
        }),
        _stage("court35_calibration", points["status"], {
            "control_point_audit": points,
            "control_points_csv": _identity(control_csv, checksum=True),
            "control_points_trc": _identity(control_trc, checksum=True),
        }),
        _stage("calibration_residual_quality_gate", residual_report["status"], {
            "audit": residual_report, "residual_table": _identity(residuals, checksum=True),
            "summary_csv": str(output / "calibration_residual_summary.csv"),
            "claim_boundary": "Review-level pixel residual diagnostic only; it does not establish absolute 3D spatial accuracy.",
        }),
        _stage("camera_synchronization", sync_detail.pop("status"), sync_detail),
        _pose_2d(project, action, start_frame, end_frame),
        _trc_3d(project, action, start_frame, end_frame),
        _imu_alignment(project, row),
    ]
    failed = [stage["id"] for stage in stages if stage["status"] == "FAIL"]
    reviews = [stage["id"] for stage in stages if stage["status"] == "REVIEW_REQUIRED"]
    report: dict[str, Any] = {
        "schema_version": "badmintonfusion35.evidence-chain.v1",
        "status": "BLOCKED" if failed else "COMPLETE_WITH_REVIEW_REQUIRED" if reviews else "COMPLETE",
        "trial": {"action": action, "repeat": repeat, "trial_id": f"{action}-R{repeat:02d}", "visual_interval_frames_inclusive": [start_frame, end_frame], "duration_s": float(row["Duration_s"])},
        "architecture": ["raw videos", "court35 calibration", "camera synchronization", "Pose2Sim 2D", "Pose2Sim 3D/filtering", "IMU alignment", "quality audit", "desktop player"],
        "stages": stages,
        "failed_stages": failed,
        "review_required_stages": reviews,
        "reproduction_commands": {
            "audit": f'court35 build-evidence-chain --project-root "{project}" --action {action} --repeat {repeat} --output-dir "{output}"',
            "pose2sim_dry_run": f'court35 pose2sim --config "{project / action / "Config.toml"}" --stages calibration poseEstimation synchronization triangulation filtering',
            "pose2sim_execute": "Add --execute only after reviewing the dry-run plan; executing reruns Pose2Sim stages and may create or replace derived outputs.",
            "desktop_player": "Run desktop_app\\run_a01_demo.ps1 after the audit passes its operational stages.",
        },
        "scientific_boundaries": [
            "Existing Pose2Sim results are checked for presence and internal coverage; this audit does not rerun model inference unless the separate explicit Pose2Sim command is used.",
            "Pixel residuals and Pose2Sim log estimates must not be represented as independent centimetre-level spatial validation.",
            "The evidence chain establishes software/data provenance and operational QC, not a new causal or accuracy result.",
        ],
    }
    report_path = output / "evidence_chain.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    report["report"] = str(report_path)
    return report
