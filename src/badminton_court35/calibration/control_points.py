from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import csv
import json

import numpy as np


GROUND_X_M = (-2.70, -1.35, 0.00, 1.35, 2.70)
GROUND_Y_M = (0.75, 2.15, 3.55, 4.95, 6.35)
ELEVATED_Z_M = (0.50, 1.00, 1.50, 2.00, 2.30)
POLE_A_XY_M = (-3.45, 1.60)
POLE_B_XY_M = (3.45, 5.10)


@dataclass(frozen=True, slots=True)
class ControlPoint:
    click_order: int
    point_id: str
    point_type: str
    x_m: float
    y_m: float
    z_m: float

    def canonical_row(self) -> str:
        return (
            f"{self.click_order},{self.point_id},{self.point_type},"
            f"{self.x_m:.6f},{self.y_m:.6f},{self.z_m:.6f}"
        )


def expected_control_points() -> list[ControlPoint]:
    """Return the locked 25-ground + 10-elevated formal layout."""
    points: list[ControlPoint] = []
    order = 1
    for y_m in GROUND_Y_M:
        for x_m in GROUND_X_M:
            points.append(ControlPoint(order, f"P{order:02d}", "Ground", x_m, y_m, 0.0))
            order += 1

    for point_type, (x_m, y_m) in (
        ("Pole_A", POLE_A_XY_M),
        ("Pole_B", POLE_B_XY_M),
    ):
        for z_m in ELEVATED_Z_M:
            points.append(ControlPoint(order, f"P{order:02d}", point_type, x_m, y_m, z_m))
            order += 1
    return points


def read_control_points(path: str | Path) -> list[ControlPoint]:
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"Click_Order", "Point_ID", "Type", "X_m", "Y_m", "Z_m"}
    if not rows or not required.issubset(rows[0]):
        missing = sorted(required - (set(rows[0]) if rows else set()))
        raise ValueError(f"Invalid control-point CSV; missing columns: {missing}")
    return [
        ControlPoint(
            int(row["Click_Order"]),
            row["Point_ID"].strip(),
            row["Type"].strip(),
            float(row["X_m"]),
            float(row["Y_m"]),
            float(row["Z_m"]),
        )
        for row in rows
    ]


def write_control_points(points: list[ControlPoint], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("Click_Order", "Point_ID", "Type", "X_m", "Y_m", "Z_m"))
        for point in points:
            writer.writerow(
                (
                    point.click_order,
                    point.point_id,
                    point.point_type,
                    f"{point.x_m:.6f}",
                    f"{point.y_m:.6f}",
                    f"{point.z_m:.6f}",
                )
            )
    return path


def control_point_digest(points: list[ControlPoint]) -> str:
    payload = "\n".join(point.canonical_row() for point in points).encode("utf-8")
    return sha256(payload).hexdigest().upper()


def validate_control_points(
    points: list[ControlPoint], *, compare_to_formal: bool = True, atol: float = 1e-6
) -> dict[str, object]:
    issues: list[str] = []
    orders = [point.click_order for point in points]
    ids = [point.point_id for point in points]
    coordinates = np.asarray([(p.x_m, p.y_m, p.z_m) for p in points], dtype=float)

    if len(points) != 35:
        issues.append(f"Expected 35 points, found {len(points)}")
    if orders != list(range(1, len(points) + 1)):
        issues.append("Click_Order is not a continuous 1-based sequence")
    if ids != [f"P{index:02d}" for index in range(1, len(points) + 1)]:
        issues.append("Point_ID order is not P01...P35")
    if len({(p.x_m, p.y_m, p.z_m) for p in points}) != len(points):
        issues.append("Duplicate 3D coordinates detected")

    ground = [point for point in points if point.point_type == "Ground"]
    elevated = [point for point in points if point.point_type in {"Pole_A", "Pole_B"}]
    if len(ground) != 25 or any(abs(point.z_m) > atol for point in ground):
        issues.append("Ground layer must contain 25 points at Z=0")
    if len(elevated) != 10:
        issues.append("Elevated layer must contain 10 points")
    for point_type in ("Pole_A", "Pole_B"):
        heights = sorted(point.z_m for point in points if point.point_type == point_type)
        if not np.allclose(heights, ELEVATED_Z_M, atol=atol, rtol=0):
            issues.append(f"{point_type} heights differ from the locked five-level design")

    rank = int(np.linalg.matrix_rank(coordinates - coordinates.mean(axis=0))) if len(points) else 0
    if rank != 3:
        issues.append(f"Control points are not fully non-coplanar (rank={rank})")

    if compare_to_formal:
        formal = expected_control_points()
        if len(points) == len(formal):
            for actual, expected in zip(points, formal, strict=True):
                if (
                    actual.click_order != expected.click_order
                    or actual.point_id != expected.point_id
                    or actual.point_type != expected.point_type
                    or not np.allclose(
                        (actual.x_m, actual.y_m, actual.z_m),
                        (expected.x_m, expected.y_m, expected.z_m),
                        atol=atol,
                        rtol=0,
                    )
                ):
                    issues.append(
                        f"{actual.point_id or actual.click_order} differs from the locked formal layout"
                    )

    return {
        "status": "PASS" if not issues else "FAIL",
        "point_count": len(points),
        "ground_count": len(ground),
        "elevated_count": len(elevated),
        "coordinate_rank": rank,
        "sha256_canonical": control_point_digest(points),
        "issues": issues,
    }


def trc_declared_marker_count(path: str | Path) -> int:
    lines = Path(path).read_text(encoding="utf-8-sig", errors="replace").splitlines()
    if len(lines) < 3:
        raise ValueError("TRC file has fewer than three header rows")
    header = lines[1].split("\t")
    values = lines[2].split("\t")
    mapping = dict(zip(header, values))
    try:
        return int(mapping["NumMarkers"])
    except (KeyError, ValueError) as exc:
        raise ValueError("TRC header does not contain a valid NumMarkers field") from exc


def report_json(report: dict[str, object]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)
