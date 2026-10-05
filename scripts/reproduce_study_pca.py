"""Recalculate study PCA and optionally draw score/coefficient panels from local inputs."""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
from badminton_court35.analysis.pca_study import study_pca
from badminton_court35.analysis.study import FEATURE_NAMES, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--input', type=Path, help='Wide CSV/XLSX or S2_observation_level_diagnostics.csv')
    source.add_argument('--synthetic-demo', action='store_true')
    parser.add_argument('--sheet', default='质量门控数据')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plot', action='store_true')
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Output must be new or empty')
    features = [f for f in FEATURE_NAMES if 'gyro' in f or 'dynamic_acc' in f]
    if args.synthetic_demo:
        from run_study_analysis import synthetic_frame
        data = synthetic_frame()
        identity = {'kind':'SYNTHETIC_SOFTWARE_TEST_NOT_PAPER_DATA'}
    else:
        data = pd.read_excel(args.input, sheet_name=args.sheet) if args.input.suffix.lower() == '.xlsx' else pd.read_csv(args.input)
        identity = {'filename':args.input.name, 'sha256':sha256(args.input)}
        if 'Feature' in data.columns:
            # Preserve the documented feature order. Duplicate IDs fail, not silently averaged.
            series = []
            for feature in features:
                subset = data.loc[data.Feature == feature, ['Participant','Action',feature]]
                if subset.duplicated(['Participant','Action']).any():
                    raise ValueError(f'Duplicate participant-action rows for {feature}')
                series.append(subset.set_index(['Participant','Action']))
            data = pd.concat(series, axis=1).reset_index()
    scores, coefficients, manifest = study_pca(data, features)
    args.output.mkdir(parents=True, exist_ok=True)
    scores.to_csv(args.output/'scores.csv', index=False)
    coefficients.to_csv(args.output/'coefficients.csv', index=False)
    manifest['input'] = identity
    manifest['scope'] = 'Descriptive PCA; no generalization or anatomical accuracy claim'
    if args.plot:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, (a,b) = plt.subplots(2,1,figsize=(10,10),layout='constrained')
        for action, group in scores.groupby('Action', sort=True):
            a.scatter(group.PC1,group.PC2,label=action,s=25)
        a.set_xlabel(f"PC1 ({manifest['explained_percent'][0]:.2f}%)")
        a.set_ylabel(f"PC2 ({manifest['explained_percent'][1]:.2f}%)")
        a.legend(ncol=5)
        a.set_title('Participant-action scores (synthetic)' if args.synthetic_demo else 'Participant-action scores')
        loc=np.arange(len(features))
        b.barh(loc-.18,coefficients.PC1_loading,height=.35,label='PC1')
        b.barh(loc+.18,coefficients.PC2_loading,height=.35,label='PC2',hatch='///')
        b.set_yticks(loc,features,fontsize=7); b.invert_yaxis()
        b.set_xlabel('Principal component coefficient'); b.legend()
        fig.savefig(args.output/'pca.png',dpi=180)
        fig.savefig(args.output/'pca.pdf')
        plt.close(fig)
        manifest['plot_note'] = 'Portable layout, not a pixel-identical reproduction of the manually laid-out manuscript figure'
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'n':manifest['n'],'explained_percent':manifest['explained_percent'][:2]}))


if __name__ == '__main__':
    main()
