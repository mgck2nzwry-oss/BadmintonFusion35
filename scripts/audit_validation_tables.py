"""Read authorized event/scene CSV files, validate arithmetic and emit a JSON audit."""
import argparse
import json
from pathlib import Path
import pandas as pd
from badminton_court35.analysis.validation import scene_point_errors, event_timing_errors

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene',type=Path)
    parser.add_argument('--events',type=Path)
    parser.add_argument('--fixed-offset-ms',type=float)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.scene and not args.events: parser.error('Supply --scene and/or --events')
    if args.fixed_offset_ms is not None and not args.events: parser.error('--fixed-offset-ms requires --events')
    if args.output.exists(): parser.error('Output exists; choose a new filename')
    result={}
    if args.scene: result['scene']=scene_point_errors(pd.read_csv(args.scene))
    if args.events: result['events']=event_timing_errors(pd.read_csv(args.events),args.fixed_offset_ms)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(result,allow_nan=False))

if __name__=='__main__': main()
