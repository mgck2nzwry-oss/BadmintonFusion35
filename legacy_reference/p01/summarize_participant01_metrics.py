# Legacy reference; NOT a universal participant pipeline. See ../README.md.
# Local path configuration replaced; recorded session windows are not published.
from legacy_config import LEGACY_ROOT, load_windows
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = LEGACY_ROOT

MARKER_FILE = ROOT / "Participant01_marker_metrics.csv"
ANGLE_FILE = ROOT / "Participant01_joint_angle_metrics.csv"
SEGMENT_FILE = ROOT / "Participant01_repetition_segments.csv"


MARKER_METRICS = [
    "StartEndDisplacement_m",
    "PathLength_m",
    "MeanSpeed_m_s",
    "PeakSpeed_m_s",
    "P95Speed_m_s",
    "XRange_m",
    "YRange_m",
    "ZRange_m",
]

ANGLE_METRICS = [
    "MeanAngle_deg",
    "MinAngle_deg",
    "MaxAngle_deg",
    "AngleROM_deg",
    "PeakAngularVelocity_deg_s",
    "P95AngularVelocity_deg_s",
]


def summarize_long(
    dataframe: pd.DataFrame,
    group_columns: list[str],
    metric_columns: list[str],
) -> pd.DataFrame:
    """
    对每个分组的有效重复进行描述性统计。
    每个指标输出有效样本量、均值、标准差、中位数、
    四分位距、最小值、最大值和变异系数。
    """
    rows = []

    for group_values, group in dataframe.groupby(
        group_columns,
        dropna=False,
        sort=True,
    ):
        if not isinstance(group_values, tuple):
            group_values = (group_values,)

        base = dict(zip(group_columns, group_values))

        valid_group = group[group["Status"] == "Valid"].copy()

        total_repeats = int(group["Repeat"].nunique())
        valid_repeats = int(valid_group["Repeat"].nunique())

        excluded_occlusion = int(
            group.loc[
                group["Status"] == "Excluded_Occlusion",
                "Repeat",
            ].nunique()
        )

        for metric in metric_columns:
            if metric not in group.columns:
                continue

            values = pd.to_numeric(
                valid_group[metric],
                errors="coerce",
            ).dropna()

            row = dict(base)

            row.update(
                {
                    "Metric": metric,
                    "TotalRepeats": total_repeats,
                    "ValidRepeats": valid_repeats,
                    "ExcludedOcclusionRepeats": excluded_occlusion,
                    "MissingMetricRepeats": (
                        total_repeats
                        - excluded_occlusion
                        - int(values.size)
                    ),
                }
            )

            if values.empty:
                row.update(
                    {
                        "Mean": np.nan,
                        "SD": np.nan,
                        "Median": np.nan,
                        "Q1": np.nan,
                        "Q3": np.nan,
                        "IQR": np.nan,
                        "Minimum": np.nan,
                        "Maximum": np.nan,
                        "CV_percent": np.nan,
                    }
                )
            else:
                mean = float(values.mean())
                sd = (
                    float(values.std(ddof=1))
                    if values.size >= 2
                    else np.nan
                )

                q1 = float(values.quantile(0.25))
                q3 = float(values.quantile(0.75))

                # 均值接近0时不报告CV，避免产生没有意义的巨大数值
                cv = (
                    float(abs(sd / mean) * 100)
                    if (
                        np.isfinite(sd)
                        and np.isfinite(mean)
                        and abs(mean) > 1e-12
                    )
                    else np.nan
                )

                row.update(
                    {
                        "Mean": mean,
                        "SD": sd,
                        "Median": float(values.median()),
                        "Q1": q1,
                        "Q3": q3,
                        "IQR": q3 - q1,
                        "Minimum": float(values.min()),
                        "Maximum": float(values.max()),
                        "CV_percent": cv,
                    }
                )

            rows.append(row)

    return pd.DataFrame(rows)


def summarize_duration(
    segments: pd.DataFrame,
) -> pd.DataFrame:
    segments = segments.copy()

    segments["Duration_s"] = pd.to_numeric(
        segments["Duration_s"],
        errors="coerce",
    )

    rows = []

    for trial, group in segments.groupby("Trial", sort=True):
        values = group["Duration_s"].dropna()

        mean = float(values.mean())
        sd = (
            float(values.std(ddof=1))
            if len(values) >= 2
            else np.nan
        )

        rows.append(
            {
                "Participant": "P01",
                "Trial": trial,
                "TotalRepeats": int(group["Repeat"].nunique()),
                "MeanDuration_s": mean,
                "SDDuration_s": sd,
                "MedianDuration_s": float(values.median()),
                "MinDuration_s": float(values.min()),
                "MaxDuration_s": float(values.max()),
                "CV_percent": (
                    abs(sd / mean) * 100
                    if np.isfinite(sd) and abs(mean) > 1e-12
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    marker = pd.read_csv(MARKER_FILE)
    angle = pd.read_csv(ANGLE_FILE)
    segments = pd.read_csv(SEGMENT_FILE)

    marker_summary = summarize_long(
        marker,
        ["Participant", "Trial", "Marker"],
        MARKER_METRICS,
    )

    angle_summary = summarize_long(
        angle,
        ["Participant", "Trial", "Angle"],
        ANGLE_METRICS,
    )

    duration_summary = summarize_duration(segments)

    marker_output = (
        ROOT / "Participant01_marker_summary_by_trial.csv"
    )

    angle_output = (
        ROOT / "Participant01_angle_summary_by_trial.csv"
    )

    duration_output = (
        ROOT / "Participant01_duration_summary_by_trial.csv"
    )

    marker_summary.to_csv(
        marker_output,
        index=False,
        encoding="utf-8-sig",
    )

    angle_summary.to_csv(
        angle_output,
        index=False,
        encoding="utf-8-sig",
    )

    duration_summary.to_csv(
        duration_output,
        index=False,
        encoding="utf-8-sig",
    )

    print("")
    print("=" * 72)
    print("P01动作指标汇总完成")
    print("=" * 72)

    print(marker_output)
    print(angle_output)
    print(duration_output)

    print("")
    print("===== 每组动作持续时间 =====")
    print(
        duration_summary[
            [
                "Trial",
                "TotalRepeats",
                "MeanDuration_s",
                "SDDuration_s",
                "CV_percent",
            ]
        ].round(4).to_string(index=False)
    )

    print("")
    print("===== 有遮挡排除的指标分组 =====")

    marker_excluded = marker_summary[
        marker_summary["ExcludedOcclusionRepeats"] > 0
    ][
        [
            "Trial",
            "Marker",
            "Metric",
            "ValidRepeats",
            "ExcludedOcclusionRepeats",
        ]
    ]

    angle_excluded = angle_summary[
        angle_summary["ExcludedOcclusionRepeats"] > 0
    ][
        [
            "Trial",
            "Angle",
            "Metric",
            "ValidRepeats",
            "ExcludedOcclusionRepeats",
        ]
    ]

    print("\n标记点：")
    print(
        marker_excluded.to_string(index=False)
        if not marker_excluded.empty
        else "None"
    )

    print("\n关节角：")
    print(
        angle_excluded.to_string(index=False)
        if not angle_excluded.empty
        else "None"
    )


if __name__ == "__main__":
    main()
