# Legacy reference; NOT a universal participant pipeline. See ../README.md.
# Local path configuration replaced; recorded session windows are not published.
from legacy_config import LEGACY_ROOT, load_windows
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from segment_repetitions import (
    read_trc,
    build_motion_energy,
)


ROOT = LEGACY_ROOT

IMU_DIR = ROOT / "P01_IMU_Alignment"

IMU_PREVIEW = (
    IMU_DIR
    / "P01_IMU_50Hz_alignment_preview.csv"
)

IMU_SEGMENTS = (
    IMU_DIR
    / "P01_IMU_trial_segments.csv"
)

VISUAL_SEGMENTS = (
    ROOT
    / "Participant01_repetition_segments.csv"
)

OUTPUT_DIR = (
    IMU_DIR
    / "Visual_IMU_Alignment"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_TABLE = (
    OUTPUT_DIR
    / "P01_visual_IMU_alignment_summary.csv"
)

TARGET_RATE = 50.0
TARGET_STEP = 1.0 / TARGET_RATE

# 允许估计IMU与视频时钟之间的小幅线性漂移
TIME_SCALES = np.arange(
    0.985,
    1.0151,
    0.0025,
)

SEARCH_STEP_S = 0.02

TRIALS = [
    "A01", "A02", "A03", "A04", "A05",
    "A06", "A07", "A08", "A09", "A10",
]


def interpolate_finite(
    source_time,
    source_value,
    target_time,
):
    source_time = np.asarray(
        source_time,
        dtype=float,
    )

    source_value = np.asarray(
        source_value,
        dtype=float,
    )

    target_time = np.asarray(
        target_time,
        dtype=float,
    )

    valid = (
        np.isfinite(source_time)
        & np.isfinite(source_value)
    )

    if valid.sum() < 3:
        return np.full(
            len(target_time),
            np.nan,
            dtype=float,
        )

    x = source_time[valid]
    y = source_value[valid]

    order = np.argsort(
        x,
        kind="stable",
    )

    x = x[order]
    y = y[order]

    # 重复时间点取均值
    temporary = pd.DataFrame(
        {
            "Time": x,
            "Value": y,
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

    x = temporary[
        "Time"
    ].to_numpy(dtype=float)

    y = temporary[
        "Value"
    ].to_numpy(dtype=float)

    result = np.interp(
        target_time,
        x,
        y,
    )

    result[
        (target_time < x[0])
        | (target_time > x[-1])
    ] = np.nan

    return result


def robust_normalize(values):
    values = np.asarray(
        values,
        dtype=float,
    )

    finite = values[
        np.isfinite(values)
    ]

    if len(finite) < 10:
        return np.full_like(
            values,
            np.nan,
            dtype=float,
        )

    lower = float(
        np.percentile(finite, 5)
    )

    upper = float(
        np.percentile(finite, 95)
    )

    scale = upper - lower

    if (
        not np.isfinite(scale)
        or scale <= 1e-12
    ):
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
        2,
    )


def pearson_correlation(
    first,
    second,
):
    first = np.asarray(
        first,
        dtype=float,
    )

    second = np.asarray(
        second,
        dtype=float,
    )

    valid = (
        np.isfinite(first)
        & np.isfinite(second)
    )

    valid_count = int(
        valid.sum()
    )

    minimum_count = max(
        100,
        int(len(first) * 0.70),
    )

    if valid_count < minimum_count:
        return np.nan, valid_count

    x = first[valid]
    y = second[valid]

    x_sd = float(
        np.std(x)
    )

    y_sd = float(
        np.std(y)
    )

    if (
        x_sd <= 1e-12
        or y_sd <= 1e-12
    ):
        return np.nan, valid_count

    correlation = float(
        np.corrcoef(x, y)[0, 1]
    )

    return correlation, valid_count


imu = pd.read_csv(
    IMU_PREVIEW
)

imu_trials = pd.read_csv(
    IMU_SEGMENTS
)

visual_segments = pd.read_csv(
    VISUAL_SEGMENTS
)

imu_time = pd.to_numeric(
    imu["SessionTime_s"],
    errors="coerce",
).to_numpy(dtype=float)

imu_energy = pd.to_numeric(
    imu["CombinedIMUEnergy"],
    errors="coerce",
).to_numpy(dtype=float)

results = []


for trial in TRIALS:

    print("")
    print("=" * 76)
    print("正在精确对齐：", trial)

    repetitions = (
        visual_segments[
            visual_segments["Trial"] == trial
        ]
        .sort_values("Repeat")
        .copy()
    )

    if len(repetitions) != 10:
        raise RuntimeError(
            f"{trial}视觉分段应有10次，"
            f"实际为{len(repetitions)}次。"
        )

    visual_start = float(
        pd.to_numeric(
            repetitions["StartTime_s"],
            errors="coerce",
        ).min()
    )

    visual_end = float(
        pd.to_numeric(
            repetitions["EndTime_s"],
            errors="coerce",
        ).max()
    )

    # 在正式动作前后各增加0.30秒，
    # 保留动作开始和结束过渡信息
    visual_start = max(
        0.0,
        visual_start - 0.30,
    )

    visual_end = (
        visual_end + 0.30
    )

    trc_files = sorted(
        (
            ROOT
            / trial
            / "pose-3d"
        ).rglob(
            "*_filt_butterworth.trc"
        )
    )

    if len(trc_files) != 1:
        raise RuntimeError(
            f"{trial}应找到1个滤波TRC，"
            f"实际找到{len(trc_files)}个。"
        )

    trc = read_trc(
        trc_files[0]
    )

    visual_time_full = pd.to_numeric(
        trc["Time"],
        errors="coerce",
    ).to_numpy(dtype=float)

    visual_energy_full = (
        build_motion_energy(trc)
    )

    visual_mask = (
        (visual_time_full >= visual_start)
        & (visual_time_full <= visual_end)
        & np.isfinite(
            visual_energy_full
        )
    )

    if visual_mask.sum() < 100:
        raise RuntimeError(
            f"{trial}正式视觉区间有效数据不足。"
        )

    visual_duration = (
        visual_end - visual_start
    )

    visual_relative_time = np.arange(
        0.0,
        visual_duration
        + TARGET_STEP / 2,
        TARGET_STEP,
    )

    visual_uniform = interpolate_finite(
        visual_time_full[
            visual_mask
        ],
        visual_energy_full[
            visual_mask
        ],
        visual_start
        + visual_relative_time,
    )

    visual_uniform = robust_normalize(
        visual_uniform
    )

    imu_trial_row = imu_trials[
        imu_trials["Trial"] == trial
    ]

    if len(imu_trial_row) != 1:
        raise RuntimeError(
            f"{trial}应找到1个IMU区段。"
        )

    imu_trial_start = float(
        imu_trial_row[
            "IMUStartTime_s"
        ].iloc[0]
    )

    imu_trial_end = float(
        imu_trial_row[
            "IMUEndTime_s"
        ].iloc[0]
    )

    candidates = []

    for time_scale in TIME_SCALES:

        scaled_duration = (
            visual_duration
            * time_scale
        )

        earliest_start = (
            imu_trial_start
        )

        latest_start = (
            imu_trial_end
            - scaled_duration
        )

        if latest_start < earliest_start:
            continue

        candidate_starts = np.arange(
            earliest_start,
            latest_start
            + SEARCH_STEP_S / 2,
            SEARCH_STEP_S,
        )

        for candidate_start in candidate_starts:

            sample_times = (
                candidate_start
                + visual_relative_time
                * time_scale
            )

            imu_candidate = interpolate_finite(
                imu_time,
                imu_energy,
                sample_times,
            )

            imu_candidate = robust_normalize(
                imu_candidate
            )

            correlation, valid_count = (
                pearson_correlation(
                    visual_uniform,
                    imu_candidate,
                )
            )

            if np.isfinite(correlation):
                candidates.append(
                    {
                        "Correlation": correlation,
                        "CandidateStart_s": (
                            float(
                                candidate_start
                            )
                        ),
                        "TimeScale": float(
                            time_scale
                        ),
                        "ValidSamples": (
                            valid_count
                        ),
                    }
                )

    if not candidates:
        raise RuntimeError(
            f"{trial}没有找到有效对齐候选。"
        )

    candidate_table = (
        pd.DataFrame(candidates)
        .sort_values(
            "Correlation",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    best = candidate_table.iloc[0]

    best_start = float(
        best["CandidateStart_s"]
    )

    best_scale = float(
        best["TimeScale"]
    )

    best_correlation = float(
        best["Correlation"]
    )

    # 第二候选必须与最佳起点相差至少0.5秒，
    # 避免把同一峰附近的相邻采样点视为独立候选
    distinct_candidates = candidate_table[
        np.abs(
            candidate_table[
                "CandidateStart_s"
            ]
            - best_start
        ) >= 0.50
    ]

    second_correlation = (
        float(
            distinct_candidates[
                "Correlation"
            ].iloc[0]
        )
        if not distinct_candidates.empty
        else np.nan
    )

    correlation_margin = (
        best_correlation
        - second_correlation
        if np.isfinite(
            second_correlation
        )
        else np.nan
    )

    aligned_imu_time = (
        best_start
        + visual_relative_time
        * best_scale
    )

    aligned_imu_energy = (
        interpolate_finite(
            imu_time,
            imu_energy,
            aligned_imu_time,
        )
    )

    aligned_imu_energy = (
        robust_normalize(
            aligned_imu_energy
        )
    )

    # 对任意视觉TRC时间t：
    # IMU绝对时间 = Offset + Scale × t
    mapping_offset = (
        best_start
        - best_scale
        * visual_start
    )

    drift_percent = (
        best_scale - 1.0
    ) * 100.0

    if (
        best_correlation >= 0.60
        and (
            not np.isfinite(
                correlation_margin
            )
            or correlation_margin >= 0.03
        )
    ):
        status = "OK"

    elif best_correlation >= 0.40:
        status = "REVIEW"

    else:
        status = "CHECK"

    results.append(
        {
            "Participant": "P01",
            "Trial": trial,
            "VisualWindowStart_s": (
                round(
                    visual_start,
                    4,
                )
            ),
            "VisualWindowEnd_s": (
                round(
                    visual_end,
                    4,
                )
            ),
            "IMUAlignedStart_s": (
                round(
                    best_start,
                    4,
                )
            ),
            "IMUAlignedEnd_s": (
                round(
                    float(
                        aligned_imu_time[-1]
                    ),
                    4,
                )
            ),
            "TimeScale_IMU_per_Visual": (
                round(
                    best_scale,
                    6,
                )
            ),
            "ClockDrift_percent": (
                round(
                    drift_percent,
                    4,
                )
            ),
            "MappingOffset_s": (
                round(
                    mapping_offset,
                    6,
                )
            ),
            "MaxCorrelation": (
                round(
                    best_correlation,
                    4,
                )
            ),
            "SecondDistinctCorrelation": (
                round(
                    second_correlation,
                    4,
                )
                if np.isfinite(
                    second_correlation
                )
                else np.nan
            ),
            "CorrelationMargin": (
                round(
                    correlation_margin,
                    4,
                )
                if np.isfinite(
                    correlation_margin
                )
                else np.nan
            ),
            "ValidAlignmentSamples": int(
                best["ValidSamples"]
            ),
            "AlignmentStatus": status,
        }
    )

    figure, axis = plt.subplots(
        figsize=(16, 7)
    )

    axis.plot(
        visual_relative_time,
        visual_uniform,
        linewidth=1.1,
        label="Visual 3D motion energy",
    )

    axis.plot(
        visual_relative_time,
        aligned_imu_energy,
        linewidth=1.1,
        label="Aligned IMU energy",
    )

    for _, repetition in repetitions.iterrows():

        repeat_start = (
            float(
                repetition[
                    "StartTime_s"
                ]
            )
            - visual_start
        )

        repeat_end = (
            float(
                repetition[
                    "EndTime_s"
                ]
            )
            - visual_start
        )

        axis.axvline(
            repeat_start,
            linestyle="--",
            linewidth=0.6,
            alpha=0.45,
        )

        axis.axvline(
            repeat_end,
            linestyle=":",
            linewidth=0.6,
            alpha=0.35,
        )

    axis.set_xlabel(
        "Time relative to selected visual window (s)"
    )

    axis.set_ylabel(
        "Normalized movement energy"
    )

    axis.set_title(
        f"P01 {trial} Visual–IMU Alignment\n"
        f"r={best_correlation:.3f}, "
        f"scale={best_scale:.4f}, "
        f"status={status}"
    )

    axis.legend()
    axis.grid(alpha=0.25)

    figure.tight_layout()

    figure_path = (
        OUTPUT_DIR
        / f"P01_{trial}_visual_IMU_alignment.png"
    )

    figure.savefig(
        figure_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(figure)

    print(
        f"{trial}: "
        f"r={best_correlation:.4f}, "
        f"scale={best_scale:.4f}, "
        f"IMU start={best_start:.3f}s, "
        f"status={status}"
    )


summary = pd.DataFrame(
    results
)

summary.to_csv(
    OUTPUT_TABLE,
    index=False,
    encoding="utf-8-sig",
)

print("")
print("=" * 76)
print("P01视觉—IMU精确对齐完成")
print("=" * 76)

print(OUTPUT_TABLE)

print("")
print(
    summary[
        [
            "Trial",
            "IMUAlignedStart_s",
            "TimeScale_IMU_per_Visual",
            "ClockDrift_percent",
            "MaxCorrelation",
            "CorrelationMargin",
            "AlignmentStatus",
        ]
    ].to_string(index=False)
)
