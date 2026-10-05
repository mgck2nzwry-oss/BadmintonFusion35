# Legacy reference; NOT a universal participant pipeline. See ../README.md.
# Local path configuration replaced; recorded session windows are not published.
from legacy_config import LEGACY_ROOT, load_windows
from pathlib import Path
import csv
import re
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = LEGACY_ROOT
PARTICIPANT = "P01"


def read_trc(path: Path) -> pd.DataFrame:
    """读取Pose2Sim输出的TRC文件。"""
    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as file:
        rows = list(csv.reader(file, delimiter="\t"))

    frame_row = None
    for index, row in enumerate(rows):
        if row and row[0].strip().lower() == "frame#":
            frame_row = index
            break

    if frame_row is None:
        raise RuntimeError(f"找不到TRC表头：{path}")

    marker_header = rows[frame_row]
    axis_header = rows[frame_row + 1]

    column_count = max(len(marker_header), len(axis_header))
    columns = ["Frame", "Time"]
    current_marker = ""

    for column_index in range(2, column_count):
        marker = (
            marker_header[column_index].strip()
            if column_index < len(marker_header)
            else ""
        )
        axis = (
            axis_header[column_index].strip()
            if column_index < len(axis_header)
            else ""
        )

        if marker:
            current_marker = marker

        axis = re.sub(r"\d+$", "", axis).upper()

        if axis not in {"X", "Y", "Z"}:
            axis = ("X", "Y", "Z")[(column_index - 2) % 3]

        columns.append(f"{current_marker}_{axis}")

    data = []

    for row in rows[frame_row + 2:]:
        if not row or not row[0].strip():
            continue

        padded = row + [""] * (len(columns) - len(row))
        values = []

        for value in padded[:len(columns)]:
            try:
                values.append(float(value))
            except (ValueError, TypeError):
                values.append(np.nan)

        data.append(values)

    dataframe = pd.DataFrame(data, columns=columns)

    if dataframe.empty:
        raise RuntimeError(f"TRC中没有数据：{path}")

    return dataframe


def build_motion_energy(dataframe: pd.DataFrame) -> np.ndarray:
    """使用多个关键点的三维速度构建动作分段参考曲线。"""
    preferred_markers = [
        "Hip",
        "RWrist",
        "LWrist",
        "RKnee",
        "LKnee",
        "RAnkle",
        "LAnkle",
    ]

    time = dataframe["Time"].to_numpy(dtype=float)
    time_step = np.nanmedian(np.diff(time))

    if not np.isfinite(time_step) or time_step <= 0:
        time_step = 1 / 60

    normalized_speeds = []

    for marker in preferred_markers:
        coordinate_columns = [
            f"{marker}_X",
            f"{marker}_Y",
            f"{marker}_Z",
        ]

        if not all(column in dataframe.columns for column in coordinate_columns):
            continue

        coordinates = dataframe[coordinate_columns].copy()

        # 仅用于绘制分段参考曲线，不会写回TRC
        coordinates = coordinates.interpolate(
            limit=10,
            limit_direction="both",
        )

        velocity = np.gradient(
            coordinates.to_numpy(dtype=float),
            time_step,
            axis=0,
        )

        speed = np.linalg.norm(velocity, axis=1)
        scale = np.nanpercentile(speed, 95)

        if np.isfinite(scale) and scale > 0:
            normalized_speeds.append(speed / scale)

    if not normalized_speeds:
        raise RuntimeError("无法从TRC生成运动强度曲线。")

    energy = np.nanmedian(
        np.vstack(normalized_speeds),
        axis=0,
    )

    energy = (
        pd.Series(energy)
        .rolling(window=15, center=True, min_periods=1)
        .mean()
        .to_numpy()
    )

    return energy


def main() -> None:
    if len(sys.argv) != 2:
        raise RuntimeError(
            "运行方式：python segment_repetitions.py A01"
        )

    trial = sys.argv[1].upper()
    pose3d_directory = ROOT / trial / "pose-3d"

    trc_files = sorted(
        pose3d_directory.rglob("*_filt_butterworth.trc")
    )

    if len(trc_files) != 1:
        raise RuntimeError(
            f"{trial}应有1个滤波TRC，实际找到{len(trc_files)}个。"
        )

    trc_path = trc_files[0]
    dataframe = read_trc(trc_path)

    frame = dataframe["Frame"].to_numpy(dtype=int)
    time = dataframe["Time"].to_numpy(dtype=float)
    energy = build_motion_energy(dataframe)

    figure, axis = plt.subplots(figsize=(15, 7))
    axis.plot(time, energy, linewidth=1.2)

    axis.set_title(
        f"{PARTICIPANT} - {trial}\n"
        "依次点击20次：每次动作的开始、结束，共10次正式动作"
    )
    axis.set_xlabel("Time (s)")
    axis.set_ylabel("Normalized motion energy")
    axis.grid(alpha=0.25)

    plt.tight_layout()

    print("")
    print("=" * 70)
    print(f"正在切分：{trial}")
    print("请依次点击20个点：")
    print("第1次开始、结束；第2次开始、结束……第10次开始、结束")
    print("不要选择准备动作和结束阶段。")
    print("=" * 70)

    clicked_points = plt.ginput(
        20,
        timeout=0,
        show_clicks=True,
    )
    plt.close(figure)

    if len(clicked_points) != 20:
        raise RuntimeError(
            f"应点击20个点，实际点击了{len(clicked_points)}个。"
        )

    clicked_times = [point[0] for point in clicked_points]
    records = []

    for repeat_index in range(10):
        start_time = clicked_times[repeat_index * 2]
        end_time = clicked_times[repeat_index * 2 + 1]

        if start_time > end_time:
            start_time, end_time = end_time, start_time

        start_index = int(np.argmin(np.abs(time - start_time)))
        end_index = int(np.argmin(np.abs(time - end_time)))

        records.append(
            {
                "Participant": PARTICIPANT,
                "Trial": trial,
                "Repeat": repeat_index + 1,
                "StartFrame": int(frame[start_index]),
                "EndFrame": int(frame[end_index]),
                "StartTime_s": round(float(time[start_index]), 4),
                "EndTime_s": round(float(time[end_index]), 4),
                "Duration_s": round(
                    float(time[end_index] - time[start_index]),
                    4,
                ),
                "OverallValid": "Yes",
                "InvalidJoint": "",
                "InvalidReason": "",
                "Notes": "",
            }
        )

    trial_output = (
        ROOT /
        trial /
        f"{trial}_repetition_segments.csv"
    )

    result = pd.DataFrame(records)
    result.to_csv(
        trial_output,
        index=False,
        encoding="utf-8-sig",
    )

    master_output = ROOT / "Participant01_repetition_segments.csv"

    if master_output.exists():
        existing = pd.read_csv(master_output)
        existing = existing[existing["Trial"] != trial]
        result = pd.concat(
            [existing, result],
            ignore_index=True,
        )

    result = result.sort_values(
        ["Trial", "Repeat"]
    )

    result.to_csv(
        master_output,
        index=False,
        encoding="utf-8-sig",
    )

    print("")
    print("动作分段已保存：")
    print(trial_output)
    print(master_output)
    print("")
    print(pd.DataFrame(records).to_string(index=False))


if __name__ == "__main__":
    main()
