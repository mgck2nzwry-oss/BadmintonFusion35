from __future__ import annotations

import numpy as np


def reconstruct_timestamp(host_time_s: np.ndarray, *, midnight_threshold_s: float = 43200.0) -> np.ndarray:
    """Reconstruct a monotonic per-sample timeline from batched host timestamps.

    Repeated timestamp runs are retained and represented by run-centre anchors.
    A clock wrap larger than ``midnight_threshold_s`` is treated as midnight.
    """
    host_time = np.asarray(host_time_s, dtype=float)
    if host_time.ndim != 1 or len(host_time) < 2:
        raise ValueError("host_time_s must be a one-dimensional array with at least two samples")
    index = np.arange(len(host_time), dtype=float)
    finite = np.isfinite(host_time)
    if int(finite.sum()) < 2:
        raise ValueError("At least two finite timestamps are required")
    filled = np.interp(index, index[finite], host_time[finite])

    unwrapped = filled.copy()
    day_offset = 0.0
    for position in range(1, len(unwrapped)):
        current = filled[position] + day_offset
        if current < unwrapped[position - 1] - midnight_threshold_s:
            day_offset += 86400.0
            current = filled[position] + day_offset
        unwrapped[position] = current
    monotonic = np.maximum.accumulate(unwrapped)

    starts = np.flatnonzero(np.r_[True, np.diff(monotonic) > 1e-9])
    ends = np.r_[starts[1:] - 1, len(monotonic) - 1]
    anchor_index = (starts + ends) / 2.0
    anchor_time = monotonic[starts]
    increasing = np.r_[True, np.diff(anchor_time) > 0]
    anchor_index = anchor_index[increasing]
    anchor_time = anchor_time[increasing]
    if len(anchor_time) < 2:
        raise ValueError("Fewer than two strictly increasing timestamp anchors remain")

    first_slope = (anchor_time[1] - anchor_time[0]) / (anchor_index[1] - anchor_index[0])
    last_slope = (anchor_time[-1] - anchor_time[-2]) / (anchor_index[-1] - anchor_index[-2])
    if first_slope <= 0 or last_slope <= 0:
        raise ValueError("Timestamp anchors imply a non-positive sampling interval")
    if anchor_index[0] > 0:
        anchor_time = np.r_[anchor_time[0] - first_slope * anchor_index[0], anchor_time]
        anchor_index = np.r_[0.0, anchor_index]
    last_index = float(len(host_time) - 1)
    if anchor_index[-1] < last_index:
        anchor_time = np.r_[anchor_time, anchor_time[-1] + last_slope * (last_index - anchor_index[-1])]
        anchor_index = np.r_[anchor_index, last_index]
    reconstructed = np.interp(index, anchor_index, anchor_time)
    if np.any(np.diff(reconstructed) <= 0):
        raise ValueError("Reconstructed time is not strictly increasing")
    return reconstructed


def timebase_audit(reconstructed_s: np.ndarray) -> dict[str, float | int | str]:
    values = np.asarray(reconstructed_s, dtype=float)
    delta = np.diff(values)
    finite = delta[np.isfinite(delta)]
    if not len(finite):
        return {"status": "FAIL", "sample_count": int(len(values))}
    median_dt = float(np.median(finite))
    return {
        "status": "PASS" if np.all(finite > 0) else "FAIL",
        "sample_count": int(len(values)),
        "median_dt_s": median_dt,
        "estimated_rate_hz": 1.0 / median_dt if median_dt > 0 else float("nan"),
        "max_dt_s": float(np.max(finite)),
        "min_dt_s": float(np.min(finite)),
    }
