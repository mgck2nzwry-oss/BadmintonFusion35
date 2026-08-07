from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


COLORS = {
    "WTRhand": "#0072B2",
    "WTLhand": "#D55E00",
    "WTRknee": "#009E73",
    "WTLknee": "#CC79A7",
}


def build_figure(data_dir: Path, output: Path) -> None:
    points = pd.read_csv(data_dir / "visual" / "keypoints_3d_filtered.csv")
    imu = pd.read_csv(data_dir / "imu" / "imu_50hz_filtered.csv")
    metrics = pd.read_csv(data_dir / "imu" / "repetition_metrics.csv")

    figure = plt.figure(figsize=(11.5, 7.2), constrained_layout=True)
    grid = figure.add_gridspec(2, 2)
    trajectory = figure.add_subplot(grid[0, 0], projection="3d")
    gyro = figure.add_subplot(grid[0, 1])
    acceleration = figure.add_subplot(grid[1, 0])
    quality = figure.add_subplot(grid[1, 1])

    for marker, color in (("RWrist", "#0072B2"), ("LWrist", "#D55E00"), ("Hip", "#333333")):
        selected = points.loc[points["keypoint"] == marker]
        trajectory.plot(selected["x_m"], selected["y_m"], selected["z_m"], color=color, label=marker)
        trajectory.scatter(
            selected.iloc[0]["x_m"], selected.iloc[0]["y_m"], selected.iloc[0]["z_m"],
            color=color, marker="o", s=25,
        )
    trajectory.set(xlabel="X (m)", ylabel="Y (m)", zlabel="Z (m)", title="a  Filtered 3D trajectories")
    trajectory.legend(frameon=False, fontsize=8)

    for device, group in imu.groupby("device", sort=False):
        gyro.plot(group["relative_time_s"], group["gyro_magnitude_deg_s"],
                  color=COLORS[device], linewidth=1.2, label=device)
        acceleration.plot(group["relative_time_s"], group["dynamic_acceleration_proxy_g"],
                           color=COLORS[device], linewidth=1.2, label=device)
    gyro.set(xlabel="Relative time (s)", ylabel="Angular speed (°/s)",
             title="b  Four-IMU angular-speed magnitude")
    acceleration.set(xlabel="Relative time (s)", ylabel="Dynamic acceleration proxy (g)",
                     title="c  Four-IMU dynamic-acceleration proxy")
    gyro.legend(frameon=False, fontsize=7, ncol=2)
    for axis in (gyro, acceleration):
        axis.grid(axis="y", color="#dddddd", linewidth=0.6)
        axis.spines[["top", "right"]].set_visible(False)

    ordered = metrics.set_index("Device").loc[list(COLORS)]
    bars = quality.bar(
        np.arange(len(ordered)), ordered["ValidPercent"],
        color=[COLORS[item] for item in ordered.index], width=0.65,
    )
    quality.set_ylim(90, 101)
    quality.set_xticks(np.arange(len(ordered)), ordered.index, rotation=20, ha="right")
    quality.set(ylabel="Valid samples (%)", title="d  IMU completeness for A10-R10")
    quality.axhline(95, color="#555555", linestyle="--", linewidth=0.8)
    quality.text(-0.42, 95.15, "95% main-analysis gate", color="#555555", fontsize=8)
    quality.bar_label(bars, fmt="%.1f%%", fontsize=8, padding=2)
    quality.spines[["top", "right"]].set_visible(False)

    figure.suptitle("A10-R10: synchronized visual–inertial evidence", fontsize=14, fontweight="bold")
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=300, bbox_inches="tight")
    figure.savefig(output.with_suffix(".svg"), bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("examples/a10_r10"))
    parser.add_argument("--output", type=Path, default=Path("examples/a10_r10/a10_r10_overview.png"))
    args = parser.parse_args()
    build_figure(args.data_dir, args.output)


if __name__ == "__main__":
    main()
