"""Extract gap-aware marker/angle descriptors from one explicitly selected TRC segment."""
from pathlib import Path
import argparse
import json
import numpy as np
from badminton_court35.io.trc import read_trc
from badminton_court35.analysis.kinematics import calculate_marker_metrics, calculate_angle_series, calculate_angle_metrics


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trc',type=Path,required=True,help='Coordinates in metres; Time in seconds')
    p.add_argument('--start',type=float,required=True)
    p.add_argument('--end',type=float,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists() or args.end <= args.start:
        p.error('Output must not exist; end must be greater than start')
    frame=read_trc(args.trc)
    if not np.isfinite(frame.Time).all() or np.any(np.diff(frame.Time)<=0):
        raise ValueError('TRC times must be finite and strictly increasing')
    segment=frame.loc[(frame.Time>=args.start)&(frame.Time<=args.end)].copy()
    if len(segment)<3:
        raise ValueError('Fewer than three frames in selected segment')
    markers=['Hip','RHip','LHip','RKnee','LKnee','RAnkle','LAnkle','RShoulder','LShoulder','RElbow','LElbow','RWrist','LWrist']
    triplets={'RKneeAngle':('RHip','RKnee','RAnkle'),'LKneeAngle':('LHip','LKnee','LAnkle'),
              'RElbowAngle':('RShoulder','RElbow','RWrist'),'LElbowAngle':('LShoulder','LElbow','LWrist')}
    result={'start_s':args.start,'end_s':args.end,'frames':len(segment),
            'markers':{m:calculate_marker_metrics(segment,m) for m in markers},
            'angles':{name:calculate_angle_metrics(*calculate_angle_series(segment,*points)) for name,points in triplets.items()},
            'scope':'Geometric descriptors only. This command does not apply manual occlusion/inclusion annotations or certify anatomical validity.'}
    def clean(value):
        if isinstance(value,dict): return {k:clean(v) for k,v in value.items()}
        if isinstance(value,(float,np.floating)) and not np.isfinite(value): return None
        return value
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(clean(result),indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(f'Wrote feature descriptors for {len(segment)} frames')


if __name__=='__main__':
    main()
