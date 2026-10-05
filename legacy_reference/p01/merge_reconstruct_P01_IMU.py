# Legacy reference; NOT a universal participant pipeline. See ../README.md.
# Local path configuration replaced; recorded session windows are not published.
from legacy_config import LEGACY_ROOT, load_windows
from pathlib import Path
import re

import numpy as np
import pandas as pd


INPUT_DIR = (LEGACY_ROOT / 'P01_IMU_Cleaned')

OUTPUT_DIR = (LEGACY_ROOT / 'P01_IMU_Merged')

SUMMARY_PATH = (LEGACY_ROOT / 'P01_IMU_merged_summary.csv')

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DEVICES = [
    "WTRhand",
    "WTLhand",
    "WTRknee",
    "WTLknee",
]

NOMINAL_RATES = np.array(
    [25.0, 50.0, 100.0, 200.0]
)


def source_part(path: Path) -> int:
    match = re.search(
        r"data_(\d+)",
        path.name,
    )

    if match:
        return int(match.group(1))

    return 999999


def reconstruct_timestamp(
    host_time: np.ndarray,
) -> np.ndarray:
    """
    将批量写入、存在大量相同值的电脑时间戳
    重建为逐样本单调时间轴。

    不删除相同时间戳的样本。
    """
    host_time = np.asarray(
        host_time,
        dtype=float,
    )

    sample_index = np.arange(
        len(host_time),
        dtype=float,
    )

    finite = np.isfinite(host_time)

    if finite.sum() < 2:
        raise RuntimeError(
            "有效电脑时间戳不足，无法重建时间轴。"
        )

    # 补齐偶发缺失时间戳
    host_filled = np.interp(
        sample_index,
        sample_index[finite],
        host_time[finite],
    )

    # 处理跨午夜
    host_unwrapped = host_filled.copy()
    day_offset = 0.0

    for index in range(1, len(host_unwrapped)):
        current = host_filled[index] + day_offset
        previous = host_unwrapped[index - 1]

        if current < previous - 43200:
            day_offset += 86400.0
            current = host_filled[index] + day_offset

        host_unwrapped[index] = current

    # 少数网络包可能乱序，保证主时间轴不倒退
    host_monotonic = np.maximum.accumulate(
        host_unwrapped
    )

    # 将连续相同时间戳视为一个批次，
    # 以该批次的中心样本作为时间锚点
    change_points = np.flatnonzero(
        np.r_[
            True,
            np.diff(host_monotonic) > 1e-9,
        ]
    )

    run_ends = np.r_[
        change_points[1:] - 1,
        len(host_monotonic) - 1,
    ]

    anchor_index = (
        change_points + run_ends
    ) / 2.0

    anchor_time = host_monotonic[
        change_points
    ]

    # 只保留严格递增的时间锚点
    increasing = np.r_[
        True,
        np.diff(anchor_time) > 0,
    ]

    anchor_index = anchor_index[
        increasing
    ]

    anchor_time = anchor_time[
        increasing
    ]

    if len(anchor_time) < 2:
        raise RuntimeError(
            "严格递增的电脑时间锚点不足。"
        )

    # 向开头和结尾外推，避免np.interp端点变平
    first_slope = (
        anchor_time[1] - anchor_time[0]
    ) / (
        anchor_index[1] - anchor_index[0]
    )

    last_slope = (
        anchor_time[-1] - anchor_time[-2]
    ) / (
        anchor_index[-1] - anchor_index[-2]
    )

    if anchor_index[0] > 0:
        start_time = (
            anchor_time[0]
            - first_slope * anchor_index[0]
        )

        anchor_index = np.r_[
            0.0,
            anchor_index,
        ]

        anchor_time = np.r_[
            start_time,
            anchor_time,
        ]

    last_sample = len(host_time) - 1

    if anchor_index[-1] < last_sample:
        end_time = (
            anchor_time[-1]
            + last_slope
            * (
                last_sample
                - anchor_index[-1]
            )
        )

        anchor_index = np.r_[
            anchor_index,
            float(last_sample),
        ]

        anchor_time = np.r_[
            anchor_time,
            end_time,
        ]

    reconstructed = np.interp(
        sample_index,
        anchor_index,
        anchor_time,
    )

    return reconstructed


# 先读取全部设备数据
device_data = {}

for device in DEVICES:
    files = sorted(
        INPUT_DIR.glob(
            f"data_*__{device}_clean.csv"
        ),
        key=source_part,
    )

    if not files:
        raise FileNotFoundError(
            f"没有找到{device}的清洗数据。"
        )

    parts = []

    for path in files:
        dataframe = pd.read_csv(
            path,
            low_memory=False,
        )

        dataframe["SourcePart"] = (
            source_part(path)
        )

        dataframe["SourceCleanFile"] = (
            path.name
        )

        if "OriginalRow" not in dataframe:
            dataframe["OriginalRow"] = (
                np.arange(len(dataframe))
            )

        parts.append(dataframe)

    merged = pd.concat(
        parts,
        ignore_index=True,
    )

    merged["HostTime_s"] = pd.to_numeric(
        merged["HostTime_s"],
        errors="coerce",
    )

    merged["OriginalRow"] = pd.to_numeric(
        merged["OriginalRow"],
        errors="coerce",
    )

    merged = merged.sort_values(
        [
            "SourcePart",
            "OriginalRow",
        ],
        kind="stable",
    ).reset_index(drop=True)

    device_data[device] = merged


# 四个设备共同的电脑端记录起点
all_host_starts = []

for dataframe in device_data.values():
    values = dataframe[
        "HostTime_s"
    ].dropna()

    if not values.empty:
        all_host_starts.append(
            float(values.min())
        )

global_session_start = min(
    all_host_starts
)

summary_records = []


for device, dataframe in device_data.items():
    print("")
    print("=" * 76)
    print("设备：", device)

    host_time = dataframe[
        "HostTime_s"
    ].to_numpy(dtype=float)

    reconstructed_absolute = (
        reconstruct_timestamp(
            host_time
        )
    )

    dataframe[
        "ReconstructedHostTime_s"
    ] = reconstructed_absolute

    dataframe["SessionTime_s"] = (
        reconstructed_absolute
        - global_session_start
    )

    dataframe["DeviceTime_s"] = (
        reconstructed_absolute
        - reconstructed_absolute[0]
    )

    interval = np.diff(
        dataframe["DeviceTime_s"]
        .to_numpy(dtype=float)
    )

    interval = interval[
        np.isfinite(interval)
        & (interval > 0)
    ]

    duration = float(
        dataframe["DeviceTime_s"].iloc[-1]
    )

    effective_rate = (
        (len(dataframe) - 1) / duration
        if duration > 0
        else np.nan
    )

    nominal_rate = float(
        NOMINAL_RATES[
            np.argmin(
                np.abs(
                    NOMINAL_RATES
                    - effective_rate
                )
            )
        ]
    )

    expected_samples = int(
        round(
            duration * nominal_rate
        )
        + 1
    )

    estimated_missing = max(
        0,
        expected_samples
        - len(dataframe),
    )

    completeness_percent = (
        len(dataframe)
        / expected_samples
        * 100
        if expected_samples > 0
        else np.nan
    )

    raw_difference = np.diff(
        host_time
    )

    duplicate_timestamp_count = int(
        np.sum(raw_difference == 0)
    )

    backward_timestamp_count = int(
        np.sum(raw_difference < 0)
    )

    # 检查data_0至data_1的文件边界
    part_statistics = (
        dataframe.groupby(
            "SourcePart"
        )["HostTime_s"]
        .agg(["min", "max", "count"])
        .sort_index()
    )

    boundary_gaps = []

    part_numbers = list(
        part_statistics.index
    )

    for index in range(
        len(part_numbers) - 1
    ):
        current_part = part_numbers[index]
        next_part = part_numbers[index + 1]

        gap = float(
            part_statistics.loc[
                next_part,
                "min",
            ]
            - part_statistics.loc[
                current_part,
                "max",
            ]
        )

        boundary_gaps.append(gap)

    maximum_boundary_gap = (
        max(boundary_gaps)
        if boundary_gaps
        else np.nan
    )

    output_path = (
        OUTPUT_DIR
        / f"P01_{device}_merged.csv"
    )

    dataframe.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    summary_records.append(
        {
            "Participant": "P01",
            "Device": device,
            "BodyLocation": {
                "WTRhand": "Right hand",
                "WTLhand": "Left hand",
                "WTRknee": "Right knee",
                "WTLknee": "Left knee",
            }[device],
            "Rows": len(dataframe),
            "Duration_s": duration,
            "EffectiveRate_Hz": effective_rate,
            "NominalRate_Hz": nominal_rate,
            "ExpectedSamples": expected_samples,
            "EstimatedMissingSamples": (
                estimated_missing
            ),
            "Completeness_percent": (
                completeness_percent
            ),
            "MedianReconstructedInterval_ms": (
                np.median(interval) * 1000
                if len(interval)
                else np.nan
            ),
            "DuplicateHostTimestamps": (
                duplicate_timestamp_count
            ),
            "BackwardHostTimestamps": (
                backward_timestamp_count
            ),
            "MaximumFileBoundaryGap_s": (
                maximum_boundary_gap
            ),
            "MergedFile": output_path.name,
        }
    )

    print("合并样本数：", len(dataframe))
    print(
        "记录时长：",
        round(duration, 3),
        "s",
    )
    print(
        "平均有效采样率：",
        round(effective_rate, 3),
        "Hz",
    )
    print(
        "推测标称采样率：",
        nominal_rate,
        "Hz",
    )
    print(
        "估算数据完整率：",
        round(completeness_percent, 2),
        "%",
    )
    print(
        "估算缺少样本：",
        estimated_missing,
    )
    print(
        "data_0/data_1最大边界间隔：",
        (
            round(
                maximum_boundary_gap,
                4,
            )
            if np.isfinite(
                maximum_boundary_gap
            )
            else "N/A"
        ),
        "s",
    )
    print("输出：", output_path)


summary = pd.DataFrame(
    summary_records
)

summary.to_csv(
    SUMMARY_PATH,
    index=False,
    encoding="utf-8-sig",
)

print("")
print("=" * 76)
print("P01 IMU合并与时间轴重建完成")
print("=" * 76)

print(SUMMARY_PATH)
print(OUTPUT_DIR)

print("")
print(
    summary[
        [
            "Device",
            "Rows",
            "Duration_s",
            "EffectiveRate_Hz",
            "NominalRate_Hz",
            "EstimatedMissingSamples",
            "Completeness_percent",
            "MaximumFileBoundaryGap_s",
        ]
    ]
    .round(4)
    .to_string(index=False)
)
