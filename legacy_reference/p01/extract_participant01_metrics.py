# Legacy reference; NOT a universal participant pipeline. See ../README.md.
# Local path configuration replaced; recorded session windows are not published.
from legacy_config import LEGACY_ROOT, load_windows
from pathlib import Path
import math

import numpy as np
import pandas as pd

from segment_repetitions import ROOT, read_trc


PARTICIPANT = "P01"

SEGMENT_FILE = ROOT / "Participant01_repetition_segments.csv"

MARKERS = [
    "Hip",
    "RHip", "LHip",
    "RKnee", "LKnee",
    "RAnkle", "LAnkle",
    "RShoulder", "LShoulder",
    "RElbow", "LElbow",
    "RWrist", "LWrist",
]

ANGLE_DEFINITIONS = {
    "RKneeAngle": ("RHip", "RKnee", "RAnkle"),
    "LKneeAngle": ("LHip", "LKnee", "LAnkle"),
    "RElbowAngle": ("RShoulder", "RElbow", "RWrist"),
    "LElbowAngle": ("LShoulder", "LElbow", "LWrist"),
}


def split_invalid_joints(value) -> set[str]:
    if pd.isna(value):
        return set()

    return {
        item.strip()
        for item in str(value).split(";")
        if item.strip()
    }


def marker_columns(marker: str) -> list[str]:
    return [
        f"{marker}_X",
        f"{marker}_Y",
        f"{marker}_Z",
    ]


def safe_stat(values: np.ndarray, function) -> float:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]

    if values.size == 0:
        return np.nan

    return float(function(values))


def calculate_marker_metrics(
    segment: pd.DataFrame,
    marker: str,
) -> dict:
    columns = marker_columns(marker)

    if not all(column in segment.columns for column in columns):
        return {
            "Status": "MarkerMissing",
            "Samples": len(segment),
            "ValidSamples": 0,
            "ValidFraction": 0.0,
        }

    coordinates = segment[columns].to_numpy(dtype=float)
    times = segment["Time"].to_numpy(dtype=float)

    valid = (
        np.isfinite(coordinates).all(axis=1)
        & np.isfinite(times)
    )

    valid_count = int(valid.sum())
    total_count = int(len(segment))

    result = {
        "Status": "Valid" if valid_count >= 3 else "InsufficientData",
        "Samples": total_count,
        "ValidSamples": valid_count,
        "ValidFraction": (
            valid_count / total_count
            if total_count > 0
            else 0.0
        ),
    }

    if valid_count < 3:
        return result

    xyz = coordinates[valid]
    t = times[valid]

    # 只使用时间连续且有效的相邻点计算轨迹长度和速度
    delta_xyz = np.diff(xyz, axis=0)
    delta_t = np.diff(t)

    valid_steps = (
        np.isfinite(delta_xyz).all(axis=1)
        & np.isfinite(delta_t)
        & (delta_t > 0)
    )

    step_distance = np.linalg.norm(
        delta_xyz[valid_steps],
        axis=1,
    )

    step_time = delta_t[valid_steps]

    speeds = (
        step_distance / step_time
        if step_distance.size
        else np.array([], dtype=float)
    )

    displacement = float(
        np.linalg.norm(xyz[-1] - xyz[0])
    )

    path_length = float(
        np.nansum(step_distance)
    )

    result.update(
        {
            "StartEndDisplacement_m": displacement,
            "PathLength_m": path_length,
            "MeanSpeed_m_s": safe_stat(speeds, np.mean),
            "PeakSpeed_m_s": safe_stat(speeds, np.max),
            "P95Speed_m_s": safe_stat(
                speeds,
                lambda values: np.percentile(values, 95),
            ),
            "XRange_m": safe_stat(
                xyz[:, 0],
                lambda values: np.max(values) - np.min(values),
            ),
            "YRange_m": safe_stat(
                xyz[:, 1],
                lambda values: np.max(values) - np.min(values),
            ),
            "ZRange_m": safe_stat(
                xyz[:, 2],
                lambda values: np.max(values) - np.min(values),
            ),
        }
    )

    return result


def calculate_angle_series(
    segment: pd.DataFrame,
    proximal: str,
    centre: str,
    distal: str,
) -> tuple[np.ndarray, np.ndarray]:
    required = (
        marker_columns(proximal)
        + marker_columns(centre)
        + marker_columns(distal)
    )

    if not all(column in segment.columns for column in required):
        return np.array([]), np.array([])

    p1 = segment[marker_columns(proximal)].to_numpy(dtype=float)
    p2 = segment[marker_columns(centre)].to_numpy(dtype=float)
    p3 = segment[marker_columns(distal)].to_numpy(dtype=float)
    times = segment["Time"].to_numpy(dtype=float)

    vector_1 = p1 - p2
    vector_2 = p3 - p2

    norm_1 = np.linalg.norm(vector_1, axis=1)
    norm_2 = np.linalg.norm(vector_2, axis=1)

    denominator = norm_1 * norm_2

    valid = (
        np.isfinite(vector_1).all(axis=1)
        & np.isfinite(vector_2).all(axis=1)
        & np.isfinite(times)
        & np.isfinite(denominator)
        & (denominator > 1e-12)
    )

    angles = np.full(len(segment), np.nan, dtype=float)

    dot_product = np.einsum(
        "ij,ij->i",
        vector_1,
        vector_2,
    )

    cosine = np.full(len(segment), np.nan, dtype=float)
    cosine[valid] = (
        dot_product[valid] / denominator[valid]
    )

    cosine = np.clip(cosine, -1.0, 1.0)
    angles[valid] = np.degrees(np.arccos(cosine[valid]))

    return times, angles


def calculate_angle_metrics(
    times: np.ndarray,
    angles: np.ndarray,
) -> dict:
    valid = np.isfinite(times) & np.isfinite(angles)

    valid_count = int(valid.sum())
    total_count = int(len(angles))

    result = {
        "Samples": total_count,
        "ValidSamples": valid_count,
        "ValidFraction": (
            valid_count / total_count
            if total_count > 0
            else 0.0
        ),
    }

    if valid_count < 3:
        result["Status"] = "InsufficientData"
        return result

    t = times[valid]
    a = angles[valid]

    delta_angle = np.diff(a)
    delta_time = np.diff(t)

    good_steps = (
        np.isfinite(delta_angle)
        & np.isfinite(delta_time)
        & (delta_time > 0)
    )

    angular_velocity = (
        np.abs(delta_angle[good_steps] / delta_time[good_steps])
        if good_steps.any()
        else np.array([], dtype=float)
    )

    result.update(
        {
            "Status": "Valid",
            "MeanAngle_deg": safe_stat(a, np.mean),
            "MinAngle_deg": safe_stat(a, np.min),
            "MaxAngle_deg": safe_stat(a, np.max),
            "AngleROM_deg": (
                safe_stat(a, np.max) - safe_stat(a, np.min)
            ),
            "PeakAngularVelocity_deg_s": safe_stat(
                angular_velocity,
                np.max,
            ),
            "P95AngularVelocity_deg_s": safe_stat(
                angular_velocity,
                lambda values: np.percentile(values, 95),
            ),
        }
    )

    return result


def main() -> None:
    if not SEGMENT_FILE.exists():
        raise FileNotFoundError(
            f"找不到分段总表：{SEGMENT_FILE}"
        )

    segments = pd.read_csv(SEGMENT_FILE)

    marker_rows = []
    angle_rows = []

    for trial in sorted(segments["Trial"].unique()):
        trial_segments = (
            segments[segments["Trial"] == trial]
            .sort_values("Repeat")
        )

        trc_files = sorted(
            (ROOT / trial / "pose-3d").rglob(
                "*_filt_butterworth.trc"
            )
        )

        if len(trc_files) != 1:
            raise RuntimeError(
                f"{trial}应有1个滤波TRC，"
                f"实际找到{len(trc_files)}个"
            )

        trc = read_trc(trc_files[0])

        for _, repetition in trial_segments.iterrows():
            repeat_number = int(repetition["Repeat"])
            start_frame = int(repetition["StartFrame"])
            end_frame = int(repetition["EndFrame"])

            segment = trc[
                (trc["Frame"] >= start_frame)
                & (trc["Frame"] <= end_frame)
            ].copy()

            invalid_joints = split_invalid_joints(
                repetition.get("InvalidJoint", "")
            )

            base = {
                "Participant": PARTICIPANT,
                "Trial": trial,
                "Repeat": repeat_number,
                "StartFrame": start_frame,
                "EndFrame": end_frame,
                "Duration_s": float(repetition["Duration_s"]),
                "OverallValid": repetition.get(
                    "OverallValid",
                    "Yes",
                ),
            }

            # 标记点指标
            for marker in MARKERS:
                row = dict(base)
                row["Marker"] = marker

                if marker in invalid_joints:
                    row.update(
                        {
                            "Status": "Excluded_Occlusion",
                            "InvalidReason": "Occlusion",
                        }
                    )
                else:
                    row.update(
                        calculate_marker_metrics(
                            segment,
                            marker,
                        )
                    )
                    row["InvalidReason"] = ""

                marker_rows.append(row)

            # 关节角指标
            for angle_name, markers in ANGLE_DEFINITIONS.items():
                proximal, centre, distal = markers

                row = dict(base)
                row["Angle"] = angle_name

                affected = sorted(
                    invalid_joints.intersection(markers)
                )

                if affected:
                    row.update(
                        {
                            "Status": "Excluded_Occlusion",
                            "InvalidReason": (
                                "Occlusion:"
                                + ";".join(affected)
                            ),
                        }
                    )
                else:
                    times, angles = calculate_angle_series(
                        segment,
                        proximal,
                        centre,
                        distal,
                    )

                    row.update(
                        calculate_angle_metrics(
                            times,
                            angles,
                        )
                    )
                    row["InvalidReason"] = ""

                angle_rows.append(row)

    marker_output = (
        ROOT / "Participant01_marker_metrics.csv"
    )

    angle_output = (
        ROOT / "Participant01_joint_angle_metrics.csv"
    )

    marker_dataframe = pd.DataFrame(marker_rows)
    angle_dataframe = pd.DataFrame(angle_rows)

    marker_dataframe.to_csv(
        marker_output,
        index=False,
        encoding="utf-8-sig",
    )

    angle_dataframe.to_csv(
        angle_output,
        index=False,
        encoding="utf-8-sig",
    )

    print("")
    print("=" * 72)
    print("指标提取完成")
    print("=" * 72)
    print(marker_output)
    print(angle_output)

    print("")
    print("Marker rows:", len(marker_dataframe))
    print("Angle rows :", len(angle_dataframe))

    print("")
    print("遮挡排除的标记点记录：")
    print(
        marker_dataframe[
            marker_dataframe["Status"]
            == "Excluded_Occlusion"
        ][
            [
                "Trial",
                "Repeat",
                "Marker",
                "Status",
            ]
        ].to_string(index=False)
    )

    print("")
    print("遮挡排除的关节角记录：")
    print(
        angle_dataframe[
            angle_dataframe["Status"]
            == "Excluded_Occlusion"
        ][
            [
                "Trial",
                "Repeat",
                "Angle",
                "InvalidReason",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
