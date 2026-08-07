from __future__ import annotations

import numpy as np
import pandas as pd


def _as_bool(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "yes", "1", "pass"}:
        return True
    if normalized in {"false", "no", "0", "fail", "nan", "none", ""}:
        return False
    raise ValueError(f"Cannot interpret as boolean: {value!r}")


def apply_inclusion_rules(
    data: pd.DataFrame,
    *,
    optical_column: str = "OpticalComparisonEligible",
    imu_valid_percent_column: str = "ValidPercent",
    main_threshold_percent: float = 95.0,
    exclusion_threshold_percent: float = 90.0,
) -> pd.DataFrame:
    """Apply the locked variable-specific optical/IMU inclusion policy."""
    if optical_column not in data or imu_valid_percent_column not in data:
        raise ValueError(f"Input must include {optical_column!r} and {imu_valid_percent_column!r}")
    output = data.copy()
    optical = output[optical_column].map(_as_bool)
    valid_percent = pd.to_numeric(output[imu_valid_percent_column], errors="coerce")

    status = np.select(
        [
            ~optical,
            valid_percent < exclusion_threshold_percent,
            valid_percent < main_threshold_percent,
        ],
        ["Excluded_Optical", "Excluded_IMU", "Sensitivity_Only"],
        default="Main_Analysis",
    )
    status = pd.Series(status, index=output.index, dtype="object")
    status[valid_percent.isna()] = "Excluded_IMU"
    output["JointAnalysisStatus"] = status
    output["IncludeMainAnalysis"] = status.eq("Main_Analysis")
    output["IncludeSensitivityAnalysis"] = status.isin(("Main_Analysis", "Sensitivity_Only"))

    reasons: list[str] = []
    for is_optical, percent, current in zip(optical, valid_percent, status, strict=True):
        if not is_optical:
            reasons.append("Optical quality criterion not met")
        elif not np.isfinite(percent):
            reasons.append("IMU valid percentage missing")
        elif current == "Excluded_IMU":
            reasons.append(f"IMU valid data {percent:.2f}% (<{exclusion_threshold_percent:.0f}%)")
        elif current == "Sensitivity_Only":
            reasons.append(
                f"IMU valid data {percent:.2f}% ({exclusion_threshold_percent:.0f}–{main_threshold_percent:.0f}%)"
            )
        else:
            reasons.append("Meets optical and IMU quality criteria")
    output["JointExclusionReason"] = reasons
    return output
