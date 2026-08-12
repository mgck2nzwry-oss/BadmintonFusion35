from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


RESIDUAL_COLUMNS = {
    "Camera",
    "Point_ID",
    "Residual_px",
    "Robust_inlier_count",
    "Robust_inlier_RMSE_px",
}


def assess_calibration_resilience(
    residuals: str | Path | pd.DataFrame,
    *,
    minimum_robust_inliers: int = 6,
    minimum_inlier_ratio: float = 0.40,
    review_rmse_px: float = 5.0,
    reclick_limit: int = 5,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Assess whether small point/camera problems can be reviewed safely.

    This is a diagnostic gate, not a calibration solver. It never changes measured
    3D coordinates, clicked pixels or camera parameters. Suggested point IDs are the
    highest-residual observations to inspect/re-click before re-running calibration.
    """
    data = residuals.copy() if isinstance(residuals, pd.DataFrame) else pd.read_csv(residuals)
    missing = sorted(RESIDUAL_COLUMNS - set(data.columns))
    if missing:
        raise ValueError(f"Residual table is missing columns: {missing}")
    for column in RESIDUAL_COLUMNS - {"Camera", "Point_ID"}:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    rows: list[dict[str, object]] = []
    for camera, group in data.groupby("Camera", sort=True):
        finite = group.loc[np.isfinite(group["Residual_px"])].copy()
        visible = int(len(finite))
        robust_inliers = int(finite["Robust_inlier_count"].max()) if visible else 0
        robust_rmse = float(finite["Robust_inlier_RMSE_px"].iloc[0]) if visible else np.nan
        ratio = robust_inliers / visible if visible else 0.0
        reserve = max(0, robust_inliers - minimum_robust_inliers)
        suggestions = (
            finite.sort_values("Residual_px", ascending=False)[["Point_ID", "Residual_px"]]
            .head(reclick_limit)
            .to_dict(orient="records")
        )
        if robust_inliers < minimum_robust_inliers or ratio < minimum_inlier_ratio:
            status = "BLOCKED"
            action = "Increase point coverage or restore camera visibility before calibration"
        elif not np.isfinite(robust_rmse) or robust_rmse > review_rmse_px:
            status = "RECALIBRATE"
            action = "Inspect suggested points, re-click if justified, then re-run calibration"
        else:
            status = "TOLERANT_WITH_REVIEW"
            action = "Small point losses are tolerable within the reported reserve; retain review"
        rows.append(
            {
                "Camera": str(camera),
                "Status": status,
                "VisiblePoints": visible,
                "RobustInliers": robust_inliers,
                "RobustInlierRatio": ratio,
                "RobustInlierRMSE_px": robust_rmse,
                "AdditionalRobustPointLossReserve": reserve,
                "SuggestedPointReview": suggestions,
                "RecommendedAction": action,
            }
        )

    summary = pd.DataFrame(rows)
    overall = "BLOCKED" if (summary["Status"] == "BLOCKED").any() else (
        "RECALIBRATE" if (summary["Status"] == "RECALIBRATE").any() else "TOLERANT_WITH_REVIEW"
    )
    report = {
        "status": overall,
        "camera_count": int(len(summary)),
        "minimum_robust_inliers": minimum_robust_inliers,
        "minimum_inlier_ratio": minimum_inlier_ratio,
        "review_rmse_px": review_rmse_px,
        "automatic_changes_applied": False,
        "safe_adaptation": (
            "Measured control-point coordinates may be versioned per venue. Pixel clicks and camera "
            "parameters are never silently moved; a flagged camera must be re-calibrated and audited."
        ),
        "accuracy_boundary": (
            "Pixel residual tolerance is not centimetre-level spatial validation. Use held-out known "
            "distances or an independent 3D validation for spatial accuracy claims."
        ),
    }
    return summary, report
