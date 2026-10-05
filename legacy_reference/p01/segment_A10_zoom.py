# Legacy reference; NOT a universal participant pipeline. See ../README.md.
# Local path configuration replaced; recorded session windows are not published.
from legacy_config import LEGACY_ROOT, load_windows
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from segment_repetitions import (
    ROOT,
    PARTICIPANT,
    read_trc,
    build_motion_energy,
)

trial = "A10"
pose3d_dir = ROOT / trial / "pose-3d"

trc_files = sorted(
    pose3d_dir.rglob("*_filt_butterworth.trc")
)

if len(trc_files) != 1:
    raise RuntimeError(
        f"A10 should contain exactly one filtered TRC, found {len(trc_files)}"
    )

df = read_trc(trc_files[0])

frames = df["Frame"].to_numpy(dtype=int)
times = df["Time"].to_numpy(dtype=float)
energy = build_motion_energy(df)

# 每次动作的大致时间范围，只用于放大显示
windows = load_windows('a10_zoom_windows')

records = []

for repeat_index, (left, right) in enumerate(windows, start=1):

    fig, ax = plt.subplots(figsize=(16, 8))

    mask = (times >= left) & (times <= right)

    ax.plot(
        times[mask],
        energy[mask],
        linewidth=1.5,
    )

    ax.set_xlim(left, right)
    ax.set_title(
        f"P01 - A10 - Repeat {repeat_index}\n"
        "Click START first, then END"
    )
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Normalized motion energy")
    ax.grid(alpha=0.3)

    plt.tight_layout()

    print("")
    print(
        f"Repeat {repeat_index}: "
        "click START, then END"
    )

    points = plt.ginput(
        2,
        timeout=0,
        show_clicks=True,
    )

    plt.close(fig)

    if len(points) != 2:
        raise RuntimeError(
            f"Repeat {repeat_index}: expected 2 clicks, got {len(points)}"
        )

    start_time = points[0][0]
    end_time = points[1][0]

    if start_time > end_time:
        start_time, end_time = end_time, start_time

    start_idx = int(
        np.argmin(np.abs(times - start_time))
    )
    end_idx = int(
        np.argmin(np.abs(times - end_time))
    )

    records.append(
        {
            "Participant": PARTICIPANT,
            "Trial": trial,
            "Repeat": repeat_index,
            "StartFrame": int(frames[start_idx]),
            "EndFrame": int(frames[end_idx]),
            "StartTime_s": round(
                float(times[start_idx]),
                4,
            ),
            "EndTime_s": round(
                float(times[end_idx]),
                4,
            ),
            "Duration_s": round(
                float(
                    times[end_idx] -
                    times[start_idx]
                ),
                4,
            ),
            "OverallValid": "Yes",
            "InvalidJoint": "",
            "InvalidReason": "",
            "Notes": "",
        }
    )

result = pd.DataFrame(records)

trial_output = (
    ROOT /
    trial /
    "A10_repetition_segments.csv"
)

result.to_csv(
    trial_output,
    index=False,
    encoding="utf-8-sig",
)

master_output = (
    ROOT /
    "Participant01_repetition_segments.csv"
)

if master_output.exists():
    existing = pd.read_csv(master_output)
    existing = existing[
        existing["Trial"] != trial
    ]

    result_master = pd.concat(
        [existing, result],
        ignore_index=True,
    )
else:
    result_master = result.copy()

result_master = result_master.sort_values(
    ["Trial", "Repeat"]
)

result_master.to_csv(
    master_output,
    index=False,
    encoding="utf-8-sig",
)

print("")
print("A10 segmentation saved:")
print(trial_output)
print(master_output)
print("")
print(result.to_string(index=False))
