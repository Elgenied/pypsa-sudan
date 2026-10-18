"""Resume checked coupling caches with a longer MIP resource limit.

The time allowance and optional LP backend change; inputs, objective, constraints
and gap tolerances are identical. Completed cases remain reusable. This is useful
on busy machines where the builder's default 1,200-second allowance is insufficient.
The optional HiPO backend requires highspy[extras]>=1.15 in the execution runtime.
"""
import argparse
import json
import pypsa
import highspy
import coupled_model as c

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=float,default=3600)
    parser.add_argument('--mip-lp-solver',choices=['ipm','hipo'],default='ipm')
    args=parser.parse_args()
    if args.seconds<1200:parser.error('Extended allowance must be at least 1200 seconds')
    if args.mip_lp_solver=='hipo' and tuple(map(int,highspy.Highs().version().split('.')[:2]))<(1,15):parser.error('HiPO requires highspy[extras]>=1.15')
    accessor=type(pypsa.Network().optimize)
    original=accessor.__call__
    def extended(self,*a,**kw):
        options=kw.get('solver_options',{})
        if 'mip_rel_gap' in options:kw['solver_options']={**options,'time_limit':args.seconds,'mip_lp_solver':args.mip_lp_solver}
        return original(self,*a,**kw)
    c.OUT.mkdir(parents=True,exist_ok=True)
    (c.OUT/'solver_resource_override.json').write_text(json.dumps(dict(mip_time_limit_seconds=args.seconds,default_seconds=1200,mip_lp_solver=args.mip_lp_solver,highs_version=highspy.Highs().version(),model_and_gap_tolerances_unchanged=True),indent=2)+'\n')
    accessor.__call__=extended
    try:c.run()
    finally:accessor.__call__=original

if __name__=='__main__':main()
