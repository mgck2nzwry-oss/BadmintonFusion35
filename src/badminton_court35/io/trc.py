from __future__ import annotations

from pathlib import Path
import csv
import re

import numpy as np
import pandas as pd


def read_trc(path: str | Path) -> pd.DataFrame:
    """Read a Pose2Sim/OpenSim TRC without crossing missing-data gaps."""
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        rows = list(csv.reader(handle, delimiter="\t"))

    frame_row = next(
        (index for index, row in enumerate(rows) if row and row[0].strip().lower() == "frame#"),
        None,
    )
    if frame_row is None or frame_row + 1 >= len(rows):
        raise ValueError(f"TRC header not found: {path}")

    marker_header = rows[frame_row]
    axis_header = rows[frame_row + 1]
    column_count = max(len(marker_header), len(axis_header))
    columns = ["Frame", "Time"]
    current_marker = ""
    seen: dict[str, int] = {}

    for index in range(2, column_count):
        marker = marker_header[index].strip() if index < len(marker_header) else ""
        axis = axis_header[index].strip() if index < len(axis_header) else ""
        if marker:
            current_marker = marker
        axis = re.sub(r"\d+$", "", axis).upper()
        if axis not in {"X", "Y", "Z"}:
            axis = ("X", "Y", "Z")[(index - 2) % 3]
        base = f"{current_marker}_{axis}"
        seen[base] = seen.get(base, 0) + 1
        columns.append(base if seen[base] == 1 else f"{base}__dup{seen[base]}")

    data: list[list[float]] = []
    for row in rows[frame_row + 2 :]:
        if not row or not row[0].strip():
            continue
        padded = row + [""] * (len(columns) - len(row))
        values: list[float] = []
        for value in padded[: len(columns)]:
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                values.append(np.nan)
        data.append(values)
    frame = pd.DataFrame(data, columns=columns)
    if frame.empty:
        raise ValueError(f"TRC contains no data rows: {path}")
    return frame


def build_motion_energy(
    frame: pd.DataFrame,
    markers: tuple[str, ...] = ("Hip", "RWrist", "LWrist", "RKnee", "LKnee", "RAnkle", "LAnkle"),
    interpolation_limit: int = 10,
    rolling_window: int = 15,
) -> np.ndarray:
    time = pd.to_numeric(frame["Time"], errors="coerce").to_numpy(dtype=float)
    dt = float(np.nanmedian(np.diff(time)))
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError("TRC time is not strictly usable")
    normalized: list[np.ndarray] = []
    for marker in markers:
        columns = [f"{marker}_{axis}" for axis in "XYZ"]
        if not all(column in frame for column in columns):
            continue
        coordinates = frame[columns].apply(pd.to_numeric, errors="coerce")
        coordinates = coordinates.interpolate(
            limit=interpolation_limit, limit_direction="both", limit_area="inside"
        )
        velocity = np.gradient(coordinates.to_numpy(dtype=float), dt, axis=0)
        speed = np.linalg.norm(velocity, axis=1)
        scale = float(np.nanpercentile(speed, 95))
        if np.isfinite(scale) and scale > 0:
            normalized.append(speed / scale)
    if not normalized:
        raise ValueError("No preferred marker triplets were found in the TRC")
    energy = np.nanmedian(np.vstack(normalized), axis=0)
    return (
        pd.Series(energy)
        .rolling(window=rolling_window, center=True, min_periods=1)
        .mean()
        .to_numpy(dtype=float)
    )
