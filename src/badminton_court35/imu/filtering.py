from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt


def _finite_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    padded = np.r_[False, mask, False].astype(np.int8)
    changes = np.diff(padded)
    return list(zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1), strict=True))


def filter_contiguous_segments(
    values: np.ndarray,
    *,
    sampling_rate_hz: float = 50.0,
    cutoff_hz: float = 10.0,
    order: int = 4,
    minimum_segment_samples: int | None = None,
) -> tuple[np.ndarray, dict[str, object]]:
    """Zero-phase Butterworth filtering without interpolating across gaps."""
    signal = np.asarray(values, dtype=float)
    if signal.ndim != 1:
        raise ValueError("values must be one-dimensional")
    if not 0 < cutoff_hz < sampling_rate_hz / 2:
        raise ValueError("cutoff_hz must lie between zero and the Nyquist frequency")
    sos = butter(order, cutoff_hz, btype="lowpass", fs=sampling_rate_hz, output="sos")
    minimum = minimum_segment_samples or max(15, 3 * (2 * len(sos) + 1))
    output = np.full(signal.shape, np.nan, dtype=float)
    filtered_runs = 0
    short_runs = 0
    for start, end in _finite_runs(np.isfinite(signal)):
        segment = signal[start:end]
        if len(segment) < minimum:
            output[start:end] = segment
            short_runs += 1
            continue
        output[start:end] = sosfiltfilt(sos, segment)
        filtered_runs += 1
    audit = {
        "status": "PASS",
        "sampling_rate_hz": sampling_rate_hz,
        "cutoff_hz": cutoff_hz,
        "order": order,
        "finite_samples": int(np.isfinite(signal).sum()),
        "missing_samples_preserved": int((~np.isfinite(output)).sum()),
        "filtered_runs": filtered_runs,
        "short_runs_left_unfiltered": short_runs,
    }
    return output, audit
