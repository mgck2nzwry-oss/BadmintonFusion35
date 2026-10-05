# Legacy reference; NOT a universal participant pipeline. See ../README.md.
# Local path configuration replaced; recorded session windows are not published.
from legacy_config import LEGACY_ROOT, load_windows
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = LEGACY_ROOT
INPUT_DIR = ROOT / "P01_IMU_Merged"
OUTPUT_DIR = ROOT / "P01_IMU_Alignment"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_RATE = 50.0
TARGET_STEP = 1.0 / TARGET_RATE

# 仅用于生成同步预览：
# 小于等于0.12秒的短间断允许线性补齐；
# 更长间断保留NaN，不强行连接。
MAX_INTERPOLATION_GAP_S = 0.12

DEVICES = [
    "WTRhand",
    "WTLhand",
    "WTRknee",
    "WTLknee",
]

GYRO_COLUMNS = [
    "角速度X(°/s)",
    "角速度Y(°/s)",
    "角速度Z(°/s)",
]


def gap_aware_interpolate(
    source_time,
    source_value,
    target_time,
    maximum_gap,
):
    source_time = np.asarray(source_time, dtype=float)
    source_value = np.asarray(source_value, dtype=float)

    valid = (
        np.isfinite(source_time)
        & np.isfinite(source_value)
    )

    source_time = source_time[valid]
    source_value = source_value[valid]

    if len(source_time) < 2:
        return np.full(
            len(target_time),
            np.nan,
            dtype=float,
        )

    order = np.argsort(
        source_time,
        kind="stable",
    )

    source_time = source_time[order]
    source_value = source_value[order]

    # 极少数重复重建时间取均值，不删除原始文件中的样本
    temporary = pd.DataFrame(
        {
            "Time": source_time,
            "Value": source_value,
        }
    )

    temporary = (
        temporary.groupby(
            "Time",
            as_index=False,
            sort=True,
        )["Value"]
        .mean()
    )

    source_time = temporary["Time"].to_numpy()
    source_value = temporary["Value"].to_numpy()

    result = np.interp(
        target_time,
        source_time,
        source_value,
    )

    result[
        (target_time < source_time[0])
        | (target_time > source_time[-1])
    ] = np.nan

    intervals = np.diff(source_time)

    long_gap_indices = np.flatnonzero(
        intervals > maximum_gap
    )

    for index in long_gap_indices:
        gap_mask = (
            (target_time > source_time[index])
            & (
                target_time
                < source_time[index + 1]
            )
        )

        result[gap_mask] = np.nan

    return result


def robust_normalize(values):
    values = np.asarray(values, dtype=float)

    finite = values[np.isfinite(values)]

    if len(finite) < 10:
        return np.full_like(
            values,
            np.nan,
            dtype=float,
        )

    lower = np.percentile(finite, 5)
    upper = np.percentile(finite, 95)

    scale = upper - lower

    if not np.isfinite(scale) or scale <= 0:
        return np.zeros_like(
            values,
            dtype=float,
        )

    normalized = (
        values - lower
    ) / scale

    return np.clip(
        normalized,
        0,
        3,
    )


device_data = {}
minimum_times = []
maximum_times = []

for device in DEVICES:
    path = (
        INPUT_DIR
        / f"P01_{device}_merged.csv"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"找不到文件：{path}"
        )

    dataframe = pd.read_csv(
        path,
        low_memory=False,
    )

    required = [
        "SessionTime_s",
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

    dataframe["SessionTime_s"] = pd.to_numeric(
        dataframe["SessionTime_s"],
        errors="coerce",
    )

    for column in GYRO_COLUMNS:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    valid_time = dataframe[
        "SessionTime_s"
    ].dropna()

    minimum_times.append(
        float(valid_time.min())
    )

    maximum_times.append(
        float(valid_time.max())
    )

    device_data[device] = dataframe


# 只使用四个设备共同存在的时间范围
common_start = max(minimum_times)
common_end = min(maximum_times)

target_time = np.arange(
    common_start,
    common_end + TARGET_STEP / 2,
    TARGET_STEP,
)

output = pd.DataFrame(
    {
        "SessionTime_s": target_time,
    }
)

quality_records = []
normalized_magnitudes = []


for device in DEVICES:
    dataframe = device_data[device]

    source_time = dataframe[
        "SessionTime_s"
    ].to_numpy(dtype=float)

    resampled_axes = []

    for column in GYRO_COLUMNS:
        values = dataframe[
            column
        ].to_numpy(dtype=float)

        resampled = gap_aware_interpolate(
            source_time,
            values,
            target_time,
            MAX_INTERPOLATION_GAP_S,
        )

        short_name = {
            "角速度X(°/s)": "GyroX_deg_s",
            "角速度Y(°/s)": "GyroY_deg_s",
            "角速度Z(°/s)": "GyroZ_deg_s",
        }[column]

        output[
            f"{device}_{short_name}"
        ] = resampled

        resampled_axes.append(resampled)

    gyro_xyz = np.column_stack(
        resampled_axes
    )

    gyro_magnitude = np.sqrt(
        np.nansum(
            gyro_xyz ** 2,
            axis=1,
        )
    )

    all_axes_valid = np.isfinite(
        gyro_xyz
    ).all(axis=1)

    gyro_magnitude[
        ~all_axes_valid
    ] = np.nan

    # 约0.20秒平滑，只用于查看同步动作块
    gyro_smoothed = (
        pd.Series(gyro_magnitude)
        .rolling(
            window=10,
            center=True,
            min_periods=1,
        )
        .median()
        .to_numpy()
    )

    output[
        f"{device}_GyroMagnitude_deg_s"
    ] = gyro_magnitude

    output[
        f"{device}_GyroMagnitudeSmooth_deg_s"
    ] = gyro_smoothed

    normalized = robust_normalize(
        gyro_smoothed
    )

    output[
        f"{device}_GyroNormalized"
    ] = normalized

    normalized_magnitudes.append(
        normalized
    )

    valid_fraction = float(
        np.isfinite(
            gyro_magnitude
        ).mean()
    )

    quality_records.append(
        {
            "Participant": "P01",
            "Device": device,
            "TargetRate_Hz": TARGET_RATE,
            "CommonStart_s": common_start,
            "CommonEnd_s": common_end,
            "CommonDuration_s": (
                common_end - common_start
            ),
            "TargetSamples": len(target_time),
            "ValidSamples": int(
                np.isfinite(
                    gyro_magnitude
                ).sum()
            ),
            "ValidFraction": valid_fraction,
            "ValidPercent": (
                valid_fraction * 100
            ),
            "MaximumInterpolatedGap_s": (
                MAX_INTERPOLATION_GAP_S
            ),
        }
    )


normalized_matrix = np.vstack(
    normalized_magnitudes
)

combined_energy = np.nanmedian(
    normalized_matrix,
    axis=0,
)

combined_energy = (
    pd.Series(combined_energy)
    .rolling(
        window=15,
        center=True,
        min_periods=1,
    )
    .mean()
    .to_numpy()
)

output[
    "CombinedIMUEnergy"
] = combined_energy


output_path = (
    OUTPUT_DIR
    / "P01_IMU_50Hz_alignment_preview.csv"
)

quality_path = (
    OUTPUT_DIR
    / "P01_IMU_50Hz_alignment_QC.csv"
)

output.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig",
)

quality = pd.DataFrame(
    quality_records
)

quality.to_csv(
    quality_path,
    index=False,
    encoding="utf-8-sig",
)


# 图1：综合运动强度
figure, axis = plt.subplots(
    figsize=(16, 7)
)

axis.plot(
    target_time,
    combined_energy,
    linewidth=1,
)

axis.set_xlabel("Session time (s)")
axis.set_ylabel("Normalized IMU movement energy")
axis.set_title(
    "P01 IMU Continuous Recording — Combined Movement Overview"
)
axis.grid(alpha=0.25)

figure.tight_layout()

combined_figure = (
    OUTPUT_DIR
    / "P01_IMU_01_combined_overview.png"
)

figure.savefig(
    combined_figure,
    dpi=300,
    bbox_inches="tight",
)

plt.close(figure)


# 图2：四个设备分别显示
figure, axis = plt.subplots(
    figsize=(16, 8)
)

for device in DEVICES:
    axis.plot(
        target_time,
        output[
            f"{device}_GyroNormalized"
        ],
        linewidth=0.8,
        label=device,
    )

axis.set_xlabel("Session time (s)")
axis.set_ylabel("Normalized gyroscope magnitude")
axis.set_title(
    "P01 IMU Continuous Recording — Four Sensors"
)
axis.legend()
axis.grid(alpha=0.25)

figure.tight_layout()

device_figure = (
    OUTPUT_DIR
    / "P01_IMU_02_device_overview.png"
)

figure.savefig(
    device_figure,
    dpi=300,
    bbox_inches="tight",
)

plt.close(figure)


print("")
print("=" * 76)
print("P01 IMU同步预览生成完成")
print("=" * 76)

print(output_path)
print(quality_path)
print(combined_figure)
print(device_figure)

print("")
print("===== 50 Hz预览有效率 =====")
print(
    quality[
        [
            "Device",
            "TargetSamples",
            "ValidSamples",
            "ValidPercent",
        ]
    ]
    .round(3)
    .to_string(index=False)
)
