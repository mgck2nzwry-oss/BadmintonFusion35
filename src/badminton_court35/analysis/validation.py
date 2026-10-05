"""Audit provided validation tables; do not create or infer validation observations."""
import numpy as np
import pandas as pd


def scene_point_errors(frame: pd.DataFrame):
    truth=frame[[f'True_{axis}_m' for axis in 'XYZ']].to_numpy(float)
    estimate=frame[[f'Estimated_{axis}_m' for axis in 'XYZ']].to_numpy(float)
    if not len(frame) or not np.isfinite(truth).all() or not np.isfinite(estimate).all():
        raise ValueError('Scene coordinates must be nonempty and finite, in metres')
    errors=np.linalg.norm(estimate-truth,axis=1)*100
    if 'Euclidean_error_cm' in frame and not np.allclose(errors,frame.Euclidean_error_cm.to_numpy(float),atol=1e-7,rtol=1e-7):
        raise ValueError('Reported scene errors disagree with coordinate-derived errors')
    return {'n':len(frame),'mean_cm':float(errors.mean()),'median_cm':float(np.median(errors)),
            'max_cm':float(errors.max()),'errors_cm':errors.tolist(),
            'scope':'Scene-coordinate reconstruction only; not anatomical landmark, angle or velocity validation.'}


def event_timing_errors(frame: pd.DataFrame, fixed_offset_ms: float | None = None):
    raw=(frame['cam3_audio_event_s'].to_numpy(float)-frame['imu_time_s'].to_numpy(float))*1000
    if not len(raw) or not np.isfinite(raw).all():
        raise ValueError('Event times must be nonempty and finite, in seconds')
    if 'raw_video_minus_imu_ms' in frame and not np.allclose(raw,frame.raw_video_minus_imu_ms,atol=1e-6,rtol=0):
        raise ValueError('Raw difference column disagrees with paired timestamps')
    offset=float(raw.mean()) if fixed_offset_ms is None else float(fixed_offset_ms)
    if not np.isfinite(offset):
        raise ValueError('Offset must be finite')
    residual=raw-offset; absolute=np.abs(residual)
    if fixed_offset_ms is None and 'residual_after_constant_offset_ms' in frame:
        if not np.allclose(residual,frame.residual_after_constant_offset_ms,atol=1e-6,rtol=0):
            raise ValueError('Residual column disagrees with mean-offset calculation')
    return {'n':len(raw),'offset_ms':offset,'mean_absolute_ms':float(absolute.mean()),
            'median_absolute_ms':float(np.median(absolute)),'max_absolute_ms':float(absolute.max()),
            'residuals_ms':residual.tolist(),
            'offset_estimation':'same supplied events' if fixed_offset_ms is None else 'user-supplied fixed offset; provenance must be documented',
            'scope':'Timestamp-pair residual audit; independence, event identity and rapid-action adequacy are not established by this calculation.'}
