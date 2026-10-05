# Legacy reference; NOT a universal participant pipeline. See ../README.md.
# Local path configuration replaced; recorded session windows are not published.
from legacy_config import LEGACY_ROOT, load_windows
from pathlib import Path
import pandas as pd


ROOT = LEGACY_ROOT

INPUT_FILE = (
    ROOT
    / "P01_IMU_Alignment"
    / "P01_IMU_repetition_metrics.csv"
)

OUTPUT_FILE = (
    ROOT
    / "P01_IMU_Alignment"
    / "P01_visual_IMU_joint_inclusion_table.csv"
)

AUDIT_FILE = (
    ROOT
    / "P01_IMU_Alignment"
    / "P01_visual_IMU_joint_inclusion_audit.csv"
)


data = pd.read_csv(INPUT_FILE)

data["ValidPercent"] = pd.to_numeric(
    data["ValidPercent"],
    errors="coerce",
)

data["OpticalComparisonEligible"] = (
    data["OpticalComparisonEligible"]
    .astype(str)
    .str.strip()
    .str.lower()
    .map(
        {
            "true": True,
            "false": False,
        }
    )
)


def determine_status(row):

    optical_valid = bool(
        row["OpticalComparisonEligible"]
    )

    imu_valid_percent = float(
        row["ValidPercent"]
    )

    if not optical_valid:
        return "Excluded_Optical"

    if imu_valid_percent < 90:
        return "Excluded_IMU"

    if imu_valid_percent < 95:
        return "Sensitivity_Only"

    return "Main_Analysis"


def determine_reason(row):

    reasons = []

    if not bool(
        row["OpticalComparisonEligible"]
    ):
        joints = str(
            row.get(
                "OpticalComparisonExclusion",
                "",
            )
        ).strip()

        reasons.append(
            "Optical occlusion"
            + (
                f": {joints}"
                if joints
                and joints.lower() != "nan"
                else ""
            )
        )

    valid_percent = float(
        row["ValidPercent"]
    )

    if valid_percent < 90:
        reasons.append(
            f"IMU valid data {valid_percent:.2f}% (<90%)"
        )

    elif valid_percent < 95:
        reasons.append(
            f"IMU valid data {valid_percent:.2f}% (90–95%)"
        )

    if not reasons:
        return "Meets optical and IMU quality criteria"

    return "; ".join(reasons)


data["JointAnalysisStatus"] = data.apply(
    determine_status,
    axis=1,
)

data["JointExclusionReason"] = data.apply(
    determine_reason,
    axis=1,
)

data["IncludeMainAnalysis"] = (
    data["JointAnalysisStatus"]
    == "Main_Analysis"
)

data["IncludeSensitivityAnalysis"] = (
    data["JointAnalysisStatus"].isin(
        [
            "Main_Analysis",
            "Sensitivity_Only",
        ]
    )
)

data.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig",
)


audit = (
    data.groupby(
        [
            "Trial",
            "Device",
            "JointAnalysisStatus",
        ],
        dropna=False,
    )
    .size()
    .reset_index(name="Repetitions")
)

audit.to_csv(
    AUDIT_FILE,
    index=False,
    encoding="utf-8-sig",
)


print("")
print("=" * 76)
print("P01视觉—IMU联合纳入表生成完成")
print("=" * 76)

print(OUTPUT_FILE)
print(AUDIT_FILE)

print("")
print("===== 总体纳入结果 =====")

print(
    data[
        "JointAnalysisStatus"
    ]
    .value_counts()
    .reindex(
        [
            "Main_Analysis",
            "Sensitivity_Only",
            "Excluded_Optical",
            "Excluded_IMU",
        ],
        fill_value=0,
    )
    .to_string()
)

print("")
print("===== 非主分析记录 =====")

attention = data[
    data["JointAnalysisStatus"]
    != "Main_Analysis"
][
    [
        "Trial",
        "Repeat",
        "Device",
        "ValidPercent",
        "OpticalComparisonEligible",
        "JointAnalysisStatus",
        "JointExclusionReason",
    ]
]

print(
    attention
    .sort_values(
        [
            "Trial",
            "Repeat",
            "Device",
        ]
    )
    .to_string(index=False)
)
