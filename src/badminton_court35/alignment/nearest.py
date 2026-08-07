from __future__ import annotations

import numpy as np
import pandas as pd


def nearest_time_mapping(
    visual_time_s: np.ndarray,
    imu_time_s: np.ndarray,
    *,
    max_abs_error_ms: float = 10.000001,
) -> tuple[pd.DataFrame, dict[str, object]]:
    visual = np.asarray(visual_time_s, dtype=float)
    imu = np.asarray(imu_time_s, dtype=float)
    if visual.ndim != 1 or imu.ndim != 1 or not len(visual) or not len(imu):
        raise ValueError("visual_time_s and imu_time_s must be non-empty one-dimensional arrays")
    if not np.isfinite(visual).all() or not np.isfinite(imu).all():
        raise ValueError("Time arrays must be finite")
    if np.any(np.diff(visual) <= 0) or np.any(np.diff(imu) <= 0):
        raise ValueError("Time arrays must be strictly increasing")

    right = np.searchsorted(imu, visual, side="left")
    right = np.clip(right, 0, len(imu) - 1)
    left = np.clip(right - 1, 0, len(imu) - 1)
    choose_right = np.abs(imu[right] - visual) < np.abs(imu[left] - visual)
    nearest = np.where(choose_right, right, left)
    signed_error_s = imu[nearest] - visual
    counts = np.bincount(nearest, minlength=len(imu))
    reuse = counts[nearest]
    mapping = pd.DataFrame(
        {
            "visual_sample_index": np.arange(len(visual), dtype=int),
            "visual_time_s": visual,
            "imu_nearest_sample_index": nearest,
            "imu_nearest_time_s": imu[nearest],
            "timing_error_s": signed_error_s,
            "timing_error_ms": signed_error_s * 1000.0,
            "abs_timing_error_ms": np.abs(signed_error_s) * 1000.0,
            "imu_sample_reuse_count": reuse,
        }
    )
    maximum = float(mapping["abs_timing_error_ms"].max())
    audit = {
        "status": "PASS" if maximum <= max_abs_error_ms else "FAIL",
        "visual_samples": int(len(visual)),
        "unique_imu_samples": int(np.unique(nearest).size),
        "max_abs_timing_error_ms": maximum,
        "mean_abs_timing_error_ms": float(mapping["abs_timing_error_ms"].mean()),
        "p95_abs_timing_error_ms": float(mapping["abs_timing_error_ms"].quantile(0.95)),
        "max_imu_reuse_count": int(reuse.max()),
        "mapping_method": "nearest_sample_no_interpolation",
    }
    return mapping, audit


def merge_visual_imu(
    visual: pd.DataFrame,
    imu: pd.DataFrame,
    mapping: pd.DataFrame,
    *,
    visual_prefix: str = "VIS__",
    imu_prefix: str = "IMU__",
) -> pd.DataFrame:
    if len(visual) != len(mapping):
        raise ValueError("Visual row count must equal mapping row count")
    indices = mapping["imu_nearest_sample_index"].to_numpy(dtype=int)
    if indices.min(initial=0) < 0 or indices.max(initial=-1) >= len(imu):
        raise IndexError("Mapping refers to an IMU row outside the input table")
    visual_payload = visual.reset_index(drop=True).add_prefix(visual_prefix)
    imu_payload = imu.iloc[indices].reset_index(drop=True).add_prefix(imu_prefix)
    return pd.concat([mapping.reset_index(drop=True), visual_payload, imu_payload], axis=1)
