from __future__ import annotations

from pathlib import Path
from typing import Iterable


SUPPORTED_STAGES = (
    "calibration",
    "poseEstimation",
    "synchronization",
    "personAssociation",
    "triangulation",
    "filtering",
)


def run_pose2sim(
    config_path: str | Path,
    stages: Iterable[str],
    *,
    execute: bool = False,
) -> list[dict[str, str]]:
    """Plan or execute Pose2Sim stages with one explicit configuration file."""
    config = Path(config_path).resolve()
    if not config.is_file():
        raise FileNotFoundError(config)
    selected = list(stages)
    unknown = sorted(set(selected) - set(SUPPORTED_STAGES))
    if unknown:
        raise ValueError(f"Unsupported Pose2Sim stages: {unknown}")
    plan = [
        {"stage": stage, "config": str(config), "status": "PLANNED" if not execute else "PENDING"}
        for stage in selected
    ]
    if not execute:
        return plan

    from Pose2Sim import Pose2Sim  # imported only for a real run

    for row in plan:
        function = getattr(Pose2Sim, row["stage"])
        function(str(config))
        row["status"] = "COMPLETED"
    return plan
