# Legacy reference; NOT a universal participant pipeline. See ../README.md.
# Local path configuration replaced; recorded session windows are not published.
from legacy_config import LEGACY_ROOT, load_windows
from pathlib import Path
import numpy as np
import pandas as pd


ROOT = LEGACY_ROOT

VISUAL_SEGMENTS = (
    ROOT / "Participant01_repetition_segments.csv"
)

ALIGNMENT_FILE = (
    ROOT
    / "P01_IMU_Alignment"
    / "Visual_IMU_Alignment"
    / "P01_visual_IMU_alignment_summary.csv"
)

IMU_TRIAL_SEGMENTS = (
    ROOT
    / "P01_IMU_Alignment"
    / "P01_IMU_trial_segments.csv"
)

IMU_PREVIEW = (
    ROOT
    / "P01_IMU_Alignment"
    / "P01_IMU_50Hz_alignment_preview.csv"
)

OUTPUT_FILE = (
    ROOT
    / "P01_IMU_Alignment"
    / "P01_visual_IMU_repetition_mapping.csv"
)

AUDIT_FILE = (
    ROOT
    / "P01_IMU_Alignment"
    / "P01_visual_IMU_repetition_mapping_audit.csv"
)


def nearest_index(values, target):
    insertion = int(
        np.searchsorted(values, target)
    )

    if insertion <= 0:
        return 0

    if insertion >= len(values):
        return len(values) - 1

    before = insertion - 1
    after = insertion

    if (
        abs(values[after] - target)
        < abs(values[before] - target)
    ):
        return after

    return before


visual = pd.read_csv(VISUAL_SEGMENTS)
alignment = pd.read_csv(ALIGNMENT_FILE)
trial_bounds = pd.read_csv(IMU_TRIAL_SEGMENTS)

imu_preview = pd.read_csv(
    IMU_PREVIEW,
    usecols=["SessionTime_s"],
)

imu_time = pd.to_numeric(
    imu_preview["SessionTime_s"],
    errors="coerce",
).to_numpy(dtype=float)

if not np.isfinite(imu_time).all():
    raise RuntimeError(
        "IMU 50 Hz时间轴存在无效值。"
    )

if np.any(np.diff(imu_time) <= 0):
    raise RuntimeError(
        "IMU 50 Hz时间轴不是严格递增。"
    )


required_visual = [
    "Participant",
    "Trial",
    "Repeat",
    "StartFrame",
    "EndFrame",
    "StartTime_s",
    "EndTime_s",
    "Duration_s",
    "InvalidJoint",
    "InvalidReason",
    "Notes",
]

missing_visual = [
    column
    for column in required_visual
    if column not in visual.columns
]

if missing_visual:
    raise RuntimeError(
        f"视觉分段表缺少字段：{missing_visual}"
    )


alignment_columns = [
    "Trial",
    "TimeScale_IMU_per_Visual",
    "MappingOffset_s",
    "MaxCorrelation",
    "CorrelationMargin",
    "AlignmentStatus",
]

mapping = visual[required_visual].merge(
    alignment[alignment_columns],
    on="Trial",
    how="left",
    validate="many_to_one",
)

mapping = mapping.merge(
    trial_bounds[
        [
            "Trial",
            "IMUStartTime_s",
            "IMUEndTime_s",
        ]
    ].rename(
        columns={
            "IMUStartTime_s": "IMUTrialStart_s",
            "IMUEndTime_s": "IMUTrialEnd_s",
        }
    ),
    on="Trial",
    how="left",
    validate="many_to_one",
)


for column in [
    "StartTime_s",
    "EndTime_s",
    "Duration_s",
    "TimeScale_IMU_per_Visual",
    "MappingOffset_s",
    "IMUTrialStart_s",
    "IMUTrialEnd_s",
]:
    mapping[column] = pd.to_numeric(
        mapping[column],
        errors="coerce",
    )


# 对齐公式：
# IMU时间 = MappingOffset + TimeScale × 视觉TRC时间
mapping["MappedIMUStart_s"] = (
    mapping["MappingOffset_s"]
    + mapping["TimeScale_IMU_per_Visual"]
    * mapping["StartTime_s"]
)

mapping["MappedIMUEnd_s"] = (
    mapping["MappingOffset_s"]
    + mapping["TimeScale_IMU_per_Visual"]
    * mapping["EndTime_s"]
)

mapping["MappedIMUDuration_s"] = (
    mapping["MappedIMUEnd_s"]
    - mapping["MappedIMUStart_s"]
)

mapping["DurationRatio_IMU_to_Visual"] = (
    mapping["MappedIMUDuration_s"]
    / mapping["Duration_s"]
)


start_indices = []
end_indices = []
nearest_start_times = []
nearest_end_times = []

for _, row in mapping.iterrows():

    start_index = nearest_index(
        imu_time,
        float(row["MappedIMUStart_s"]),
    )

    end_index = nearest_index(
        imu_time,
        float(row["MappedIMUEnd_s"]),
    )

    start_indices.append(start_index)
    end_indices.append(end_index)

    nearest_start_times.append(
        float(imu_time[start_index])
    )

    nearest_end_times.append(
        float(imu_time[end_index])
    )


mapping["IMUStartIndex_50Hz"] = start_indices
mapping["IMUEndIndex_50Hz"] = end_indices

mapping["IMUStartTime_50Hz_s"] = (
    nearest_start_times
)

mapping["IMUEndTime_50Hz_s"] = (
    nearest_end_times
)

mapping["IMUSamples_50Hz"] = (
    mapping["IMUEndIndex_50Hz"]
    - mapping["IMUStartIndex_50Hz"]
    + 1
)

mapping["StartQuantizationError_ms"] = (
    (
        mapping["IMUStartTime_50Hz_s"]
        - mapping["MappedIMUStart_s"]
    )
    * 1000
)

mapping["EndQuantizationError_ms"] = (
    (
        mapping["IMUEndTime_50Hz_s"]
        - mapping["MappedIMUEnd_s"]
    )
    * 1000
)


# 允许最多两个50 Hz采样间隔的边界误差
tolerance_s = 0.04

mapping["InsideSelectedIMUTrial"] = (
    (
        mapping["MappedIMUStart_s"]
        >= mapping["IMUTrialStart_s"]
        - tolerance_s
    )
    & (
        mapping["MappedIMUEnd_s"]
        <= mapping["IMUTrialEnd_s"]
        + tolerance_s
    )
)

mapping["PositiveDuration"] = (
    mapping["MappedIMUDuration_s"] > 0
)

mapping["ValidIMUIndices"] = (
    (
        mapping["IMUStartIndex_50Hz"] >= 0
    )
    & (
        mapping["IMUEndIndex_50Hz"]
        < len(imu_time)
    )
    & (
        mapping["IMUEndIndex_50Hz"]
        >= mapping["IMUStartIndex_50Hz"]
    )
)


# 检查同一动作内相邻重复是否重叠
mapping["OverlapPreviousRepeat"] = False

mapping = mapping.sort_values(
    ["Trial", "Repeat"]
).reset_index(drop=True)

for trial, indices in mapping.groupby(
    "Trial"
).groups.items():

    ordered_indices = list(indices)

    for position in range(
        1,
        len(ordered_indices),
    ):
        previous_index = ordered_indices[
            position - 1
        ]

        current_index = ordered_indices[
            position
        ]

        previous_end = float(
            mapping.loc[
                previous_index,
                "MappedIMUEnd_s",
            ]
        )

        current_start = float(
            mapping.loc[
                current_index,
                "MappedIMUStart_s",
            ]
        )

        mapping.loc[
            current_index,
            "OverlapPreviousRepeat",
        ] = (
            current_start <= previous_end
        )


mapping["MappingStatus"] = np.where(
    mapping[
        [
            "InsideSelectedIMUTrial",
            "PositiveDuration",
            "ValidIMUIndices",
        ]
    ].all(axis=1)
    & ~mapping["OverlapPreviousRepeat"],
    "OK",
    "CHECK",
)


mapping.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig",
)


audit_rows = []

for trial, group in mapping.groupby(
    "Trial",
    sort=True,
):

    audit_rows.append(
        {
            "Participant": "P01",
            "Trial": trial,
            "Repetitions": int(
                group["Repeat"].nunique()
            ),
            "OKRepetitions": int(
                (group["MappingStatus"] == "OK").sum()
            ),
            "InsideTrialCount": int(
                group[
                    "InsideSelectedIMUTrial"
                ].sum()
            ),
            "OverlapCount": int(
                group[
                    "OverlapPreviousRepeat"
                ].sum()
            ),
            "MeanDurationRatio": float(
                group[
                    "DurationRatio_IMU_to_Visual"
                ].mean()
            ),
            "MaxAbsQuantizationError_ms": float(
                max(
                    group[
                        "StartQuantizationError_ms"
                    ].abs().max(),
                    group[
                        "EndQuantizationError_ms"
                    ].abs().max(),
                )
            ),
            "AlignmentCorrelation": float(
                group[
                    "MaxCorrelation"
                ].iloc[0]
            ),
            "Status": (
                "OK"
                if (
                    len(group) == 10
                    and (
                        group[
                            "MappingStatus"
                        ]
                        == "OK"
                    ).all()
                )
                else "CHECK"
            ),
        }
    )


audit = pd.DataFrame(audit_rows)

audit.to_csv(
    AUDIT_FILE,
    index=False,
    encoding="utf-8-sig",
)


print("")
print("=" * 76)
print("P01视觉重复已映射到IMU时间轴")
print("=" * 76)

print(OUTPUT_FILE)
print(AUDIT_FILE)

print("")
print(
    audit[
        [
            "Trial",
            "Repetitions",
            "OKRepetitions",
            "InsideTrialCount",
            "OverlapCount",
            "MeanDurationRatio",
            "MaxAbsQuantizationError_ms",
            "AlignmentCorrelation",
            "Status",
        ]
    ]
    .round(4)
    .to_string(index=False)
)

print("")
print(
    "总映射数：",
    len(mapping),
)

print(
    "OK映射数：",
    int(
        (
            mapping["MappingStatus"]
            == "OK"
        ).sum()
    ),
)
