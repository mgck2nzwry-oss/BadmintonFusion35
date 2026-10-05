"""Aggregate valid repetitions by supplied grouping columns; no participant pooling.

Status must be Valid. SD uses ddof=1; near-zero means do not receive a CV.
Extracted unchanged from summarize_participant01_metrics.py.
"""
import numpy as np
import pandas as pd

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
