from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "Camera",
    "Point_ID",
    "Residual_px",
    "Camera_true_RMSE_px",
    "Robust_inlier_count",
    "Robust_inlier_RMSE_px",
}


def audit_residual_table(
    path: str | Path, *, robust_pixel_review_threshold: float = 2.0
) -> tuple[pd.DataFrame, dict[str, object]]:
    data = pd.read_csv(path)
    missing = sorted(REQUIRED_COLUMNS - set(data.columns))
    if missing:
        raise ValueError(f"Residual table is missing columns: {missing}")

    for column in REQUIRED_COLUMNS - {"Camera", "Point_ID"}:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    rows: list[dict[str, object]] = []
    for camera, group in data.groupby("Camera", sort=True):
        residual = group["Residual_px"].to_numpy(dtype=float)
        finite = residual[np.isfinite(residual)]
        robust_count = int(np.nanmax(group["Robust_inlier_count"]))
        visible = int(len(finite))
        rows.append(
            {
                "Camera": camera,
                "VisiblePoints": visible,
                "AllPointRMSE_px": float(np.sqrt(np.mean(finite**2))) if visible else np.nan,
                "AllPointMean_px": float(np.mean(finite)) if visible else np.nan,
                "AllPointP95_px": float(np.percentile(finite, 95)) if visible else np.nan,
                "AllPointMax_px": float(np.max(finite)) if visible else np.nan,
                "ReportedCameraRMSE_px": float(group["Camera_true_RMSE_px"].dropna().iloc[0]),
                "RobustInliers": robust_count,
                "RobustInlierRatio": robust_count / visible if visible else np.nan,
                "RobustInlierRMSE_px": float(group["Robust_inlier_RMSE_px"].dropna().iloc[0]),
            }
        )

    summary = pd.DataFrame(rows)
    issues: list[str] = []
    if summary.empty:
        issues.append("No camera residuals were found")
    if (summary["RobustInliers"] < 6).any():
        issues.append("At least one camera has fewer than six robust inliers")
    if (summary["RobustInlierRatio"] < 0.40).any():
        issues.append("At least one camera has a robust-inlier ratio below 0.40")
    if (summary["RobustInlierRMSE_px"] > robust_pixel_review_threshold).any():
        issues.append(
            "At least one camera exceeds the configured robust pixel-RMSE review threshold "
            f"({robust_pixel_review_threshold:g} px)"
        )
    # Pixel residuals are diagnostic only. They are not converted to spatial accuracy here.
    report = {
        "status": "REVIEW_REQUIRED",
        "camera_count": int(summary.shape[0]),
        "robust_pixel_review_threshold": robust_pixel_review_threshold,
        "issues": issues,
        "interpretation": (
            "Pixel residuals do not establish centimetre-level 3D accuracy. "
            "A known-distance or held-out 3D validation is still required."
        ),
    }
    return summary, report
