# Legacy reference; NOT a universal participant pipeline. See ../README.md.
# Local path configuration replaced; recorded session windows are not published.
from legacy_config import LEGACY_ROOT, load_windows
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = LEGACY_ROOT

INPUT_FILE = (
    ROOT
    / "P01_IMU_Alignment"
    / "P01_IMU_50Hz_alignment_preview.csv"
)

OUTPUT_FILE = (
    ROOT
    / "P01_IMU_Alignment"
    / "P01_IMU_trial_segments.csv"
)

QC_FIGURE = (
    ROOT
    / "P01_IMU_Alignment"
    / "P01_IMU_03_trial_segments_QC.png"
)

TRIALS = [
    "A01", "A02", "A03", "A04", "A05",
    "A06", "A07", "A08", "A09", "A10",
]

# 宽松显示窗口。
# 最终边界由鼠标点击决定。
WINDOWS = load_windows('imu_trial_windows')


def nearest_index(values, target):
    return int(
        np.nanargmin(
            np.abs(values - target)
        )
    )


data = pd.read_csv(INPUT_FILE)

time = pd.to_numeric(
    data["SessionTime_s"],
    errors="coerce",
).to_numpy(dtype=float)

energy = pd.to_numeric(
    data["CombinedIMUEnergy"],
    errors="coerce",
).to_numpy(dtype=float)

records = []


for trial, (left, right) in zip(TRIALS, WINDOWS):

    mask = (
        (time >= left)
        & (time <= right)
        & np.isfinite(energy)
    )

    if mask.sum() < 10:
        raise RuntimeError(
            f"{trial}窗口内有效数据不足。"
        )

    figure, axis = plt.subplots(
        figsize=(16, 7)
    )

    axis.plot(
        time[mask],
        energy[mask],
        linewidth=1.1,
    )

    axis.set_xlim(left, right)

    axis.set_title(
        f"P01 IMU — {trial}\n"
        "Click START first, then END"
    )

    axis.set_xlabel("Session time (s)")
    axis.set_ylabel(
        "Normalized IMU movement energy"
    )

    axis.grid(alpha=0.3)

    plt.tight_layout()

    print("")
    print("=" * 65)
    print(f"{trial}：请点击两次")
    print("第1次：整组10次动作开始前的低谷")
    print("第2次：整组10次动作结束后的低谷")
    print("=" * 65)

    points = plt.ginput(
        2,
        timeout=0,
        show_clicks=True,
    )

    plt.close(figure)

    if len(points) != 2:
        raise RuntimeError(
            f"{trial}应点击2个点，"
            f"实际点击{len(points)}个。"
        )

    start_time = float(points[0][0])
    end_time = float(points[1][0])

    if start_time > end_time:
        start_time, end_time = (
            end_time,
            start_time,
        )

    start_index = nearest_index(
        time,
        start_time,
    )

    end_index = nearest_index(
        time,
        end_time,
    )

    records.append(
        {
            "Participant": "P01",
            "Trial": trial,
            "IMUStartIndex": start_index,
            "IMUEndIndex": end_index,
            "IMUStartTime_s": round(
                float(time[start_index]),
                4,
            ),
            "IMUEndTime_s": round(
                float(time[end_index]),
                4,
            ),
            "IMUDuration_s": round(
                float(
                    time[end_index]
                    - time[start_index]
                ),
                4,
            ),
            "Status": "Selected",
            "Notes": "",
        }
    )


segments = pd.DataFrame(records)

# 检查区段顺序和重叠
segments["OverlapPrevious"] = False

for index in range(1, len(segments)):
    previous_end = float(
        segments.loc[
            index - 1,
            "IMUEndTime_s",
        ]
    )

    current_start = float(
        segments.loc[
            index,
            "IMUStartTime_s",
        ]
    )

    if current_start <= previous_end:
        segments.loc[
            index,
            "OverlapPrevious",
        ] = True


segments.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig",
)


# 生成整体边界检查图
figure, axis = plt.subplots(
    figsize=(18, 8)
)

axis.plot(
    time,
    energy,
    linewidth=0.8,
)

for _, row in segments.iterrows():

    start = float(row["IMUStartTime_s"])
    end = float(row["IMUEndTime_s"])
    trial = row["Trial"]

    axis.axvspan(
        start,
        end,
        alpha=0.16,
    )

    local_mask = (
        (time >= start)
        & (time <= end)
    )

    local_energy = energy[local_mask]

    label_height = (
        np.nanmax(local_energy)
        if np.isfinite(local_energy).any()
        else 0.5
    )

    axis.text(
        (start + end) / 2,
        label_height + 0.03,
        trial,
        ha="center",
        va="bottom",
        fontsize=9,
    )

axis.set_xlabel("Session time (s)")
axis.set_ylabel(
    "Normalized IMU movement energy"
)

axis.set_title(
    "P01 IMU Trial Segmentation QC"
)

axis.grid(alpha=0.25)

figure.tight_layout()

figure.savefig(
    QC_FIGURE,
    dpi=300,
    bbox_inches="tight",
)

plt.close(figure)


print("")
print("=" * 72)
print("P01 IMU十组实验区段已保存")
print("=" * 72)

print(OUTPUT_FILE)
print(QC_FIGURE)

print("")
print(
    segments[
        [
            "Trial",
            "IMUStartTime_s",
            "IMUEndTime_s",
            "IMUDuration_s",
            "OverlapPrevious",
        ]
    ].to_string(index=False)
)
