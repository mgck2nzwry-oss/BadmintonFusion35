# Legacy reference; NOT a universal participant pipeline. See ../README.md.
# Local path configuration replaced; recorded session windows are not published.
from legacy_config import LEGACY_ROOT, load_windows
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt


ROOT = LEGACY_ROOT

IMU_DIR = ROOT / "P01_IMU_Merged"

MAPPING_FILE = (
    ROOT
    / "P01_IMU_Alignment"
    / "P01_visual_IMU_repetition_mapping.csv"
)

OUTPUT_FILE = (
    ROOT
    / "P01_IMU_Alignment"
    / "P01_IMU_repetition_metrics.csv"
)

AUDIT_FILE = (
    ROOT
    / "P01_IMU_Alignment"
    / "P01_IMU_repetition_metrics_audit.csv"
)


TARGET_RATE_HZ = 50.0
DT = 1.0 / TARGET_RATE_HZ

FILTER_CUTOFF_HZ = 10.0
FILTER_ORDER = 4

# 大于0.12秒的缺口不插值
MAX_INTERPOLATION_GAP_S = 0.12


DEVICES = {
    "WTRhand": "Right hand",
    "WTLhand": "Left hand",
    "WTRknee": "Right knee",
    "WTLknee": "Left knee",
}


ACC_COLUMNS = [
    "加速度X(g)",
    "加速度Y(g)",
    "加速度Z(g)",
]

GYRO_COLUMNS = [
    "角速度X(°/s)",
    "角速度Y(°/s)",
    "角速度Z(°/s)",
]


# 用于判断该IMU是否可与相应视觉指标比较。
# 视觉遮挡不删除IMU数据本身。
COMPARISON_JOINTS = {
    "WTRhand": {
        "RWrist",
        "RElbow",
    },
    "WTLhand": {
        "LWrist",
        "LElbow",
    },
    "WTRknee": {
        "RKnee",
        "RAnkle",
    },
    "WTLknee": {
        "LKnee",
        "LAnkle",
    },
}


def split_invalid_joints(value):
    if pd.isna(value):
        return set()

    return {
        item.strip()
        for item in str(value).split(";")
        if item.strip()
    }


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


mapping = pd.read_csv(
    MAPPING_FILE
)

if len(mapping) != 100:
    raise RuntimeError(
        f"映射表应有100行，实际为{len(mapping)}行。"
    )


device_data = {}

for device in DEVICES:
    path = (
        IMU_DIR
        / f"P01_{device}_merged.csv"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"找不到：{path}"
        )

    dataframe = pd.read_csv(
        path,
        low_memory=False,
    )

    required = [
        "SessionTime_s",
        *ACC_COLUMNS,
        *GYRO_COLUMNS,
    ]

    missing = [
        column
        for column in required
        if column not in dataframe.columns
    ]

    if missing:
        raise RuntimeError(
            f"{device}缺少字段：{missing}"
        )

    for column in required:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    dataframe = (
        dataframe.sort_values(
            "SessionTime_s",
            kind="stable",
        )
        .reset_index(drop=True)
    )

    device_data[device] = dataframe


records = []


for _, repetition in mapping.iterrows():

    trial = str(repetition["Trial"])
    repeat = int(repetition["Repeat"])

    start_time = float(
        repetition[
            "IMUStartTime_50Hz_s"
        ]
    )

    end_time = float(
        repetition[
            "IMUEndTime_50Hz_s"
        ]
    )

    if end_time <= start_time:
        raise RuntimeError(
            f"{trial} Repeat {repeat}时间范围无效。"
        )

    target_time = np.arange(
        start_time,
        end_time + DT / 2,
        DT,
    )

    relative_time = (
        target_time - start_time
    )

    invalid_joints = split_invalid_joints(
        repetition.get(
            "InvalidJoint",
            "",
        )
    )


    for device, body_location in DEVICES.items():

        source = device_data[device]

        source_time = source[
            "SessionTime_s"
        ].to_numpy(dtype=float)

        acceleration_axes = []

        for column in ACC_COLUMNS:
            values = source[
                column
            ].to_numpy(dtype=float)

            resampled = (
                interpolate_with_gap_limit(
                    source_time,
                    values,
                    target_time,
                )
            )

            acceleration_axes.append(
                filter_valid_blocks(
                    resampled
                )
            )


        gyroscope_axes = []

        for column in GYRO_COLUMNS:
            values = source[
                column
            ].to_numpy(dtype=float)

            resampled = (
                interpolate_with_gap_limit(
                    source_time,
                    values,
                    target_time,
                )
            )

            gyroscope_axes.append(
                filter_valid_blocks(
                    resampled
                )
            )


        acceleration = np.column_stack(
            acceleration_axes
        )

        gyroscope = np.column_stack(
            gyroscope_axes
        )


        valid_acceleration = np.isfinite(
            acceleration
        ).all(axis=1)

        valid_gyroscope = np.isfinite(
            gyroscope
        ).all(axis=1)

        valid_all = (
            valid_acceleration
            & valid_gyroscope
        )


        acceleration_magnitude = np.full(
            len(target_time),
            np.nan,
            dtype=float,
        )

        acceleration_magnitude[
            valid_acceleration
        ] = np.linalg.norm(
            acceleration[
                valid_acceleration
            ],
            axis=1,
        )


        # 方向不变的重力参照动态加速度代理量。
        # 这不是严格的世界坐标线性加速度。
        dynamic_acceleration = np.abs(
            acceleration_magnitude
            - 1.0
        )


        gyro_magnitude = np.full(
            len(target_time),
            np.nan,
            dtype=float,
        )

        gyro_magnitude[
            valid_gyroscope
        ] = np.linalg.norm(
            gyroscope[
                valid_gyroscope
            ],
            axis=1,
        )


        consecutive_dynamic = (
            np.isfinite(
                dynamic_acceleration[:-1]
            )
            & np.isfinite(
                dynamic_acceleration[1:]
            )
        )

        jerk = np.full(
            len(target_time) - 1,
            np.nan,
            dtype=float,
        )

        jerk[
            consecutive_dynamic
        ] = (
            np.diff(
                dynamic_acceleration
            )[
                consecutive_dynamic
            ]
            / DT
        )


        dynamic_peak, dynamic_peak_time = (
            peak_value_and_time(
                dynamic_acceleration,
                relative_time,
            )
        )

        gyro_peak, gyro_peak_time = (
            peak_value_and_time(
                gyro_magnitude,
                relative_time,
            )
        )


        missing_gap_count, maximum_missing_gap = (
            missing_gap_statistics(
                valid_all
            )
        )


        valid_fraction = float(
            valid_all.mean()
        )

        if repetition[
            "MappingStatus"
        ] != "OK":
            status = "CHECK_MAPPING"

        elif valid_fraction >= 0.95:
            status = "OK"

        elif valid_fraction >= 0.90:
            status = "REVIEW"

        else:
            status = "CHECK"


        affected_visual_joints = sorted(
            invalid_joints.intersection(
                COMPARISON_JOINTS[
                    device
                ]
            )
        )

        comparison_eligible = (
            len(
                affected_visual_joints
            )
            == 0
        )


        records.append(
            {
                "Participant": "P01",
                "Trial": trial,
                "Repeat": repeat,
                "Device": device,
                "BodyLocation": body_location,

                "IMUStartTime_s": start_time,
                "IMUEndTime_s": end_time,
                "Duration_s": float(
                    end_time - start_time
                ),

                "TargetRate_Hz": (
                    TARGET_RATE_HZ
                ),
                "TargetSamples": int(
                    len(target_time)
                ),
                "ValidSamples": int(
                    valid_all.sum()
                ),
                "ValidFraction": (
                    valid_fraction
                ),
                "ValidPercent": (
                    valid_fraction * 100
                ),

                "MissingGapCount": (
                    missing_gap_count
                ),
                "MaxMissingGap_s": (
                    maximum_missing_gap
                ),

                "AccelerationMagnitudeMean_g": (
                    float(
                        np.nanmean(
                            acceleration_magnitude
                        )
                    )
                    if np.isfinite(
                        acceleration_magnitude
                    ).any()
                    else np.nan
                ),

                "DynamicAccelerationRMS_g": (
                    rms(
                        dynamic_acceleration
                    )
                ),
                "DynamicAccelerationPeak_g": (
                    dynamic_peak
                ),
                "DynamicAccelerationP95_g": (
                    safe_percentile(
                        dynamic_acceleration,
                        95,
                    )
                ),
                "DynamicAccelerationIntegral_g_s": (
                    float(
                        np.nansum(
                            dynamic_acceleration
                        )
                        * DT
                    )
                ),
                "DynamicAccelerationPeakTime_s": (
                    dynamic_peak_time
                ),

                "GyroMagnitudeMean_deg_s": (
                    float(
                        np.nanmean(
                            gyro_magnitude
                        )
                    )
                    if np.isfinite(
                        gyro_magnitude
                    ).any()
                    else np.nan
                ),
                "GyroMagnitudeRMS_deg_s": (
                    rms(
                        gyro_magnitude
                    )
                ),
                "GyroMagnitudePeak_deg_s": (
                    gyro_peak
                ),
                "GyroMagnitudeP95_deg_s": (
                    safe_percentile(
                        gyro_magnitude,
                        95,
                    )
                ),
                "AngularActivity_deg": (
                    float(
                        np.nansum(
                            gyro_magnitude
                        )
                        * DT
                    )
                ),
                "GyroPeakTime_s": (
                    gyro_peak_time
                ),

                "DynamicAccelerationJerkRMS_g_s": (
                    rms(jerk)
                ),

                "OpticalInvalidJoint": (
                    repetition.get(
                        "InvalidJoint",
                        "",
                    )
                ),
                "OpticalComparisonEligible": (
                    comparison_eligible
                ),
                "OpticalComparisonExclusion": (
                    ";".join(
                        affected_visual_joints
                    )
                ),

                "MappingCorrelation": float(
                    repetition[
                        "MaxCorrelation"
                    ]
                ),
                "MetricStatus": status,
            }
        )


metrics = pd.DataFrame(
    records
)

metrics = metrics.sort_values(
    [
        "Trial",
        "Repeat",
        "Device",
    ]
).reset_index(drop=True)


metrics.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig",
)


audit_rows = []

for (
    trial,
    device,
), group in metrics.groupby(
    [
        "Trial",
        "Device",
    ],
    sort=True,
):

    audit_rows.append(
        {
            "Participant": "P01",
            "Trial": trial,
            "Device": device,
            "Repetitions": int(
                group["Repeat"].nunique()
            ),
            "OKCount": int(
                (
                    group[
                        "MetricStatus"
                    ]
                    == "OK"
                ).sum()
            ),
            "ReviewCount": int(
                (
                    group[
                        "MetricStatus"
                    ]
                    == "REVIEW"
                ).sum()
            ),
            "CheckCount": int(
                group[
                    "MetricStatus"
                ].str.startswith(
                    "CHECK"
                ).sum()
            ),
            "MeanValidPercent": float(
                group[
                    "ValidPercent"
                ].mean()
            ),
            "MinValidPercent": float(
                group[
                    "ValidPercent"
                ].min()
            ),
            "ComparisonEligibleRepeats": int(
                group[
                    "OpticalComparisonEligible"
                ].sum()
            ),
            "Status": (
                "OK"
                if (
                    len(group) == 10
                    and not group[
                        "MetricStatus"
                    ].str.startswith(
                        "CHECK"
                    ).any()
                )
                else "CHECK"
            ),
        }
    )


audit = pd.DataFrame(
    audit_rows
)

audit.to_csv(
    AUDIT_FILE,
    index=False,
    encoding="utf-8-sig",
)


print("")
print("=" * 76)
print("P01 IMU逐重复指标提取完成")
print("=" * 76)

print(OUTPUT_FILE)
print(AUDIT_FILE)

print("")
print("指标行数：", len(metrics))

print("")
print(
    audit[
        [
            "Trial",
            "Device",
            "Repetitions",
            "OKCount",
            "ReviewCount",
            "CheckCount",
            "MeanValidPercent",
            "MinValidPercent",
            "ComparisonEligibleRepeats",
            "Status",
        ]
    ]
    .round(3)
    .to_string(index=False)
)
