#!/usr/bin/env python3
"""Measured energy/delay constrained offline placement, no fictitious runtimes.

Input must have 88 complete architectures x 4 devices with verified TOTAL measured
energy and duration from the same hardware run. Never use processed 'target' here.
For each architecture, compare a feasible energy oracle with an RTX3060-first
policy, where RTX3060 is used if it meets the deadline and the least-runtime
feasible GPU is used otherwise. Infeasible jobs are counted separately.
Thresholds are ratios to RTX3060 measured duration per architecture; these
are stated operational assumptions, not measured deadlines.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
GPUS=['Quadro RTX 6000','RTX 3060','RTX 3090','Titan Xp']
REQ=['architecture_hash','gpu_type','duration_seconds','energy_joules_raw']

def validate(path):
 d=pd.read_csv(path)
 missing=set(REQ)-set(d)
 if missing: raise ValueError(f'Missing columns: {missing}')
 d=d[REQ].copy()
 d.architecture_hash=d.architecture_hash.astype(str).str.strip().str.lower()
 d.gpu_type=d.gpu_type.astype(str).str.strip()
 if d.duplicated(['architecture_hash','gpu_type']).any(): raise ValueError('Repeated GPU/architecture keys: do not silently average')
 if not d.gpu_type.isin(GPUS).all():raise ValueError('Unknown GPU')
 for c in ['duration_seconds','energy_joules_raw']:
  d[c]=pd.to_numeric(d[c],errors='raise')
  if not np.isfinite(d[c]).all() or (d[c]<=0).any():raise ValueError('Bad duration/energy')
 en=d.pivot(index='architecture_hash',columns='gpu_type',values='energy_joules_raw').reindex(columns=GPUS)
 tm=d.pivot(index='architecture_hash',columns='gpu_type',values='duration_seconds').reindex(columns=GPUS)
 if en.isna().any().any() or tm.isna().any().any():raise ValueError('Incomplete GPU coverage: restrict explicitly before processing')
 if len(en)!=88:raise ValueError(f'Expected 88 matched architectures; received {len(en)}')
 return en.sort_index(),tm.sort_index()

def run(energy, runtime, factors=(0.75,1,1.25,1.5,2.0,3.0)):
 if not energy.index.equals(runtime.index) or list(energy.columns)!=list(runtime.columns):raise ValueError('Misaligned arrays')
 E=energy.to_numpy(float);T=runtime.to_numpy(float);n=len(E)
 if np.any(T<=0) or np.any(E<=0):raise ValueError('Nonpositive values')
 out=[]; details=[]
 for factor in factors:
  deadlines=T[:,1]*factor
  oracle_sum=0; default_sum=0; oracle_time=0; default_time=0; total_regret=0; feasible_count=0; changes=0
  for i in range(n):
   choices=np.where(T[i]<=deadlines[i]+1e-9)[0]
   if not len(choices):
    details.append({'architecture_hash':energy.index[i],'factor':factor,'feasible':False})
    continue
   feasible_count+=1
   oracle_idx=choices[np.argmin(E[i,choices])]
   if 1 in choices: baseline_idx=1
   else: baseline_idx=choices[np.argmin(T[i,choices])]
   oa=float(E[i,oracle_idx]);ba=float(E[i,baseline_idx]);oracle_sum+=oa;default_sum+=ba
   oracle_time+=float(T[i,oracle_idx]);default_time+=float(T[i,baseline_idx]);total_regret+=ba-oa
   changes+=int(oracle_idx!=baseline_idx)
   details.append({'architecture_hash':energy.index[i],'factor':factor,'feasible':True,'deadline_seconds':deadlines[i],'oracle_gpu':GPUS[oracle_idx],'baseline_gpu':GPUS[baseline_idx],'oracle_energy_joules':oa,'baseline_energy_joules':ba,'oracle_runtime_seconds':T[i,oracle_idx],'baseline_runtime_seconds':T[i,baseline_idx]})
  out.append({'deadline_factor':factor,'feasible_architectures':feasible_count,'infeasible_architectures':n-feasible_count,'oracle_energy_joules_feasible_only':oracle_sum,'fixed_first_energy_joules_feasible_only':default_sum,'oracle_saving_vs_fixed_first_pct':100*(default_sum-oracle_sum)/default_sum if default_sum else None,'oracle_mean_runtime_seconds_feasible_only':oracle_time/feasible_count if feasible_count else None,'fixed_first_mean_runtime_seconds_feasible_only':default_time/feasible_count if feasible_count else None,'different_device_decisions':changes,'comparison_scope':'Only jobs feasible for BOTH policies; no queueing or idle power'})
 return pd.DataFrame(out),pd.DataFrame(details)

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 en,tm=validate(a.source);summary,detail=run(en,tm)
 a.out.mkdir(parents=True,exist_ok=True)
 en.to_csv(a.out/'verified_energy_joules_matrix.csv');tm.to_csv(a.out/'verified_runtime_seconds_matrix.csv')
 summary.to_csv(a.out/'e3_deadline_frontier.csv',index=False);detail.to_csv(a.out/'e3_pairwise_decisions.csv',index=False)
 (a.out/'provenance.json').write_text(json.dumps({'input_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'source':str(a.source),'scope':'Per-job noncontended offline hardware placement; no claimed multi-GPU runtime energy savings','deadline_definition':'factor x RTX3060 measured duration; scenario assumption, not empirical job deadlines','energy':'Original protobuf total_energy in kWh converted to joules by audited extractor','status':'measured source must pass source reconciliation, output separate from predictions'},indent=2)+'\n')
 print(summary.to_string(index=False))
if __name__=='__main__':main()
