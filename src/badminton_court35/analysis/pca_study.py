"""Study-figure PCA: log1p, population-SD scaling, SVD, deterministic signs.

Adapted from rebuild_partp_pca.py. This is unsupervised description, not a
cross-validated classifier, and is never used to preprocess held-out CV data.
"""
import numpy as np
import pandas as pd


def study_pca(frame, features):
    if len(features) != len(set(features)) or len(features) < 2:
        raise ValueError('Supply at least two distinct features')
    if frame.duplicated(['Participant', 'Action']).any():
        raise ValueError('Expected one row per participant-action')
    if frame[['Participant', 'Action']].isna().any().any():
        raise ValueError('Participant and Action identifiers cannot be missing')
    values = frame[features].to_numpy(float)
    if len(values) < 3 or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('PCA requires at least three complete nonnegative rows; no silent exclusion or imputation')
    y = np.log1p(values)
    mean, scale = y.mean(axis=0), y.std(axis=0, ddof=0)
    if np.any(scale == 0):
        raise ValueError('Constant features cannot be standardized')
    z = (y-mean)/scale
    u, s, vt = np.linalg.svd(z, full_matrices=False)
    explained = s*s / np.sum(s*s)
    score, load = u[:, :2]*s[:2], vt[:2].T.copy()
    for j in range(2):
        sign = 1 if load[np.argmax(np.abs(load[:, j])), j] >= 0 else -1
        score[:, j] *= sign
        load[:, j] *= sign
    scores = frame[['Participant', 'Action']].reset_index(drop=True).copy()
    scores['PC1'], scores['PC2'] = score[:, 0], score[:, 1]
    coefficients = pd.DataFrame({'Feature':features, 'PC1_loading':load[:, 0], 'PC2_loading':load[:, 1]})
    return scores, coefficients, {'n':len(frame), 'features':list(features),
        'explained_percent':(100*explained).tolist(), 'first_two_percent':float(100*explained[:2].sum()),
        'transform':'ln(1+x), center, population SD (ddof=0), SVD; no imputation',
        'orientation':'largest-absolute coefficient positive for each of PC1 and PC2',
        'log1p_means':mean.tolist(), 'log1p_population_sd':scale.tolist()}
