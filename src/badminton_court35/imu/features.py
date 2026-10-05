"""Reference per-repetition IMU primitives; original 50 Hz / 10 Hz parameters.

Short finite blocks are returned unfiltered when sosfiltfilt cannot operate.
This behavior is retained and must not be described as filtering every sample.
See legacy_reference/p01/extract_P01_IMU_repetition_metrics.py for orchestration.
"""
import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt

TARGET_RATE_HZ = 50.0
DT = 1.0 / TARGET_RATE_HZ
FILTER_CUTOFF_HZ = 10.0
FILTER_ORDER = 4
MAX_INTERPOLATION_GAP_S = 0.12

def interpolate_with_gap_limit(
    source_time,
    source_values,
    target_time,
):
    source_time = np.asarray(
        source_time,
        dtype=float,
    )

    source_values = np.asarray(
        source_values,
        dtype=float,
    )

    target_time = np.asarray(
        target_time,
        dtype=float,
    )

    valid = (
        np.isfinite(source_time)
        & np.isfinite(source_values)
    )

    if valid.sum() < 2:
        return np.full(
            len(target_time),
            np.nan,
            dtype=float,
        )

    temporary = pd.DataFrame(
        {
            "Time": source_time[valid],
            "Value": source_values[valid],
        }
    )

    # 同一重建时间点若存在多个值，取均值
    temporary = (
        temporary.groupby(
            "Time",
            as_index=False,
            sort=True,
        )["Value"]
        .mean()
    )

    time = temporary[
        "Time"
    ].to_numpy(dtype=float)

    values = temporary[
        "Value"
    ].to_numpy(dtype=float)

    result = np.interp(
        target_time,
        time,
        values,
    )

    result[
        (target_time < time[0])
        | (target_time > time[-1])
    ] = np.nan

    intervals = np.diff(time)

    long_gaps = np.flatnonzero(
        intervals
        > MAX_INTERPOLATION_GAP_S
    )

    for index in long_gaps:
        inside_gap = (
            (target_time > time[index])
            & (
                target_time
                < time[index + 1]
            )
        )

        result[inside_gap] = np.nan

    return result


def filter_valid_blocks(values):
    """
    分段进行零相位Butterworth滤波。
    不跨越NaN长缺口滤波。
    """
    values = np.asarray(
        values,
        dtype=float,
    )

    output = np.full_like(
        values,
        np.nan,
        dtype=float,
    )

    valid = np.isfinite(values)

    if not valid.any():
        return output

    sos = butter(
        FILTER_ORDER,
        FILTER_CUTOFF_HZ,
        btype="low",
        fs=TARGET_RATE_HZ,
        output="sos",
    )

    boundaries = np.flatnonzero(
        np.diff(
            np.r_[
                False,
                valid,
                False,
            ].astype(int)
        )
    )

    for start, end in zip(
        boundaries[0::2],
        boundaries[1::2],
    ):
        block = values[start:end]

        if len(block) < 15:
            output[start:end] = block
            continue

        try:
            output[start:end] = (
                sosfiltfilt(
                    sos,
                    block,
                )
            )
        except ValueError:
            output[start:end] = block

    return output


def rms(values):
    values = np.asarray(
        values,
        dtype=float,
    )

    values = values[
        np.isfinite(values)
    ]

    if len(values) == 0:
        return np.nan

    return float(
        np.sqrt(
            np.mean(values ** 2)
        )
    )


def safe_percentile(values, percentile):
    values = np.asarray(
        values,
        dtype=float,
    )

    values = values[
        np.isfinite(values)
    ]

    if len(values) == 0:
        return np.nan

    return float(
        np.percentile(
            values,
            percentile,
        )
    )


def peak_value_and_time(
    values,
    relative_time,
):
    values = np.asarray(
        values,
        dtype=float,
    )

    valid_indices = np.flatnonzero(
        np.isfinite(values)
    )

    if len(valid_indices) == 0:
        return np.nan, np.nan

    local_index = int(
        np.nanargmax(
            values[valid_indices]
        )
    )

    index = int(
        valid_indices[local_index]
    )

    return (
        float(values[index]),
        float(relative_time[index]),
    )


def missing_gap_statistics(valid_mask):
    valid_mask = np.asarray(
        valid_mask,
        dtype=bool,
    )

    missing = ~valid_mask

    if not missing.any():
        return 0, 0.0

    boundaries = np.flatnonzero(
        np.diff(
            np.r_[
                False,
                missing,
                False,
            ].astype(int)
        )
    )

    lengths = (
        boundaries[1::2]
        - boundaries[0::2]
    )

    return (
        int(len(lengths)),
        float(
            lengths.max() * DT
        ),
    )
