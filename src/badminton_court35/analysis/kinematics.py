"""Gap-aware visual features extracted from the original base/v2 scripts.

Inputs: Time in seconds and marker XYZ in metres; output angles in degrees.
Only adjacent valid frames enter derivatives. No anatomical accuracy is implied.
v2 base.safe_stat references are redirected to the identical local function.
"""
import numpy as np
import pandas as pd

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


def calculate_marker_metrics(segment, marker):
    columns = [
        f"{marker}_X",
        f"{marker}_Y",
        f"{marker}_Z",
    ]

    if not all(column in segment.columns for column in columns):
        return {
            "Status": "MarkerMissing",
            "Samples": len(segment),
            "ValidSamples": 0,
            "ValidFraction": 0.0,
        }

    coordinates = (
        segment[columns]
        .apply(pd.to_numeric, errors="coerce")
        .to_numpy(dtype=float)
    )

    times = pd.to_numeric(
        segment["Time"],
        errors="coerce",
    ).to_numpy(dtype=float)

    valid = (
        np.isfinite(coordinates).all(axis=1)
        & np.isfinite(times)
    )

    total_count = len(segment)
    valid_count = int(valid.sum())

    result = {
        "Status": (
            "Valid"
            if valid_count >= 3
            else "InsufficientData"
        ),
        "Samples": total_count,
        "ValidSamples": valid_count,
        "ValidFraction": (
            valid_count / total_count
            if total_count
            else 0.0
        ),
    }

    if valid_count < 3:
        return result

    valid_indices = np.flatnonzero(valid)
    first_index = int(valid_indices[0])
    last_index = int(valid_indices[-1])

    displacement = float(
        np.linalg.norm(
            coordinates[last_index]
            - coordinates[first_index]
        )
    )

    delta_xyz = np.diff(coordinates, axis=0)
    delta_time = np.diff(times)

    # 只使用相邻且均有效的帧，不跨越NaN缺口计算速度
    valid_steps = (
        valid[:-1]
        & valid[1:]
        & np.isfinite(delta_xyz).all(axis=1)
        & np.isfinite(delta_time)
        & (delta_time > 0)
    )

    step_distance = np.linalg.norm(
        delta_xyz[valid_steps],
        axis=1,
    )

    step_time = delta_time[valid_steps]

    speeds = (
        step_distance / step_time
        if step_distance.size
        else np.array([], dtype=float)
    )

    xyz_valid = coordinates[valid]

    result.update(
        {
            "StartEndDisplacement_m": displacement,
            "PathLength_m": float(np.sum(step_distance)),
            "MeanSpeed_m_s": safe_stat(
                speeds,
                np.mean,
            ),
            "PeakSpeed_m_s": safe_stat(
                speeds,
                np.max,
            ),
            "P95Speed_m_s": safe_stat(
                speeds,
                lambda values: np.percentile(values, 95),
            ),
            "XRange_m": float(
                np.max(xyz_valid[:, 0])
                - np.min(xyz_valid[:, 0])
            ),
            "YRange_m": float(
                np.max(xyz_valid[:, 1])
                - np.min(xyz_valid[:, 1])
            ),
            "ZRange_m": float(
                np.max(xyz_valid[:, 2])
                - np.min(xyz_valid[:, 2])
            ),
        }
    )

    return result


def calculate_angle_metrics(times, angles):
    times = np.asarray(times, dtype=float)
    angles = np.asarray(angles, dtype=float)

    valid = np.isfinite(times) & np.isfinite(angles)

    total_count = len(angles)
    valid_count = int(valid.sum())

    result = {
        "Samples": total_count,
        "ValidSamples": valid_count,
        "ValidFraction": (
            valid_count / total_count
            if total_count
            else 0.0
        ),
    }

    if valid_count < 3:
        result["Status"] = "InsufficientData"
        return result

    valid_angles = angles[valid]

    delta_angle = np.diff(angles)
    delta_time = np.diff(times)

    # 只计算连续有效帧之间的角速度
    valid_steps = (
        valid[:-1]
        & valid[1:]
        & np.isfinite(delta_angle)
        & np.isfinite(delta_time)
        & (delta_time > 0)
    )

    angular_velocity = np.abs(
        delta_angle[valid_steps]
        / delta_time[valid_steps]
    )

    result.update(
        {
            "Status": "Valid",
            "MeanAngle_deg": float(np.mean(valid_angles)),
            "MinAngle_deg": float(np.min(valid_angles)),
            "MaxAngle_deg": float(np.max(valid_angles)),
            "AngleROM_deg": float(
                np.max(valid_angles)
                - np.min(valid_angles)
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
