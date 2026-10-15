#!/usr/bin/env python3
"""Confirmatory-analysis-ready offline paired placement study.

Input: 4-GPU EC-NAS hardware CSV. Every statistic derived solely from input.
Prediction-based placement is deliberately not claimed here.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

GPUS = ('Quadro RTX 6000', 'RTX 3060', 'RTX 3090', 'Titan Xp')

def study(path: Path, out: Path, boot: int=10000, seed: int=47291):
    x=pd.read_csv(path)
    required={'architecture_hash','gpu_type','target'}
    if not required.issubset(x): raise ValueError(f'Missing columns: {required-set(x)}')
    if x.duplicated(['architecture_hash','gpu_type']).any():raise ValueError('Duplicate architecture-GPU records: resolve provenance instead of averaging')
    if x['architecture_hash'].isna().any():raise ValueError('Missing architecture ID')
    if not x['gpu_type'].isin(GPUS).all():raise ValueError('Unexpected GPU label')
    x['target']=pd.to_numeric(x['target'],errors='raise')
    if not np.isfinite(x['target']).all() or (x['target']<=0).any():raise ValueError('Nonfinite or nonpositive measured target')
    p=x.pivot(index='architecture_hash',columns='gpu_type',values='target').reindex(columns=GPUS)
    p=p.dropna(axis=0,how='any').sort_index()
    if p.empty:raise ValueError('No complete architecture pairs')
    oracle=p.min(axis=1)
    best=p.idxmin(axis=1)
    default=p['RTX 3060']
    gains=default-oracle
    # Ratio of energy sums for fixed workload; avoids inflated mean-of-percent saving.
    saving=100*gains.sum()/default.sum()
    rng=np.random.default_rng(seed)
    a=p.to_numpy(dtype=float); base=a[:,1]; low=a.min(axis=1)
    n=len(a); vals=np.empty(boot)
    for i in range(boot):
        ids=rng.integers(0,n,n)
        vals[i]=100*(base[ids]-low[ids]).sum()/base[ids].sum()
    ci=np.quantile(vals,[0.025,0.5,0.975])
    # Degeneracy diagnostic: leave-one-architecture-out learning best fixed GPU
    loog=[]
    for j in range(n):
        train=np.delete(a,j,axis=0)
        chosen=GPUS[int(np.argmin(train.sum(axis=0)))]
        actual=p.iloc[j][chosen]
        loog.append({'architecture_hash':p.index[j],'chosen_gpu':chosen,'actual_target':actual,'oracle_target':low[j]})
    loog=pd.DataFrame(loog)
    metrics={
      'n_complete_architectures':n,'n_complete_pairs':n*len(GPUS),
      'oracle_gpu_counts':{g:int((best==g).sum()) for g in GPUS},
      'oracle_target_sum':float(low.sum()),'fixed_rtx3060_target_sum':float(default.sum()),
      'oracle_saving_over_fixed_rtx3060_pct':float(saving),
      'bootstrap_95pct_interval_saving_pct':[float(ci[0]),float(ci[2])],
      'bootstrap_median_saving_pct':float(ci[1]),
      'nonzero_oracle_gains':int((gains>0).sum()),
      'max_job_saving_pct':float((100*gains/default).max()),
      'loao_fixed_gpu_choice_counts':loog['chosen_gpu'].value_counts().to_dict(),
      'loao_fixed_gpu_total_target':float(loog['actual_target'].sum()),
      'uniform_random_expected_target_sum':float(a.mean(axis=1).sum()),
      'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
      'target_unit':'UNVERIFIED: processed target field; do not assert absolute kWh/J',
      'scope':'Static independent-job placements; no queueing, runtime, idle power, calibration overhead or concurrency',
      'bootstrap_unit':'architecture (paired four-device observation); conditional on dataset sample',
      'prediction_based_results':'NOT RUN: requires frozen out-of-sample CAL-TRANSFER prediction exports'
    }
    out.mkdir(parents=True,exist_ok=True)
    p.to_csv(out/'energy_matrix_complete.csv',index_label='architecture_hash')
    pd.DataFrame({'architecture_hash':p.index,'oracle_gpu':best.values,'fixed_rtx3060_target':default.values,'oracle_target':low,'achievable_saving_target':gains}).to_csv(out/'oracle_per_architecture.csv',index=False)
    loog.to_csv(out/'leave_one_architecture_out_fixed_gpu.csv',index=False)
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    return metrics

if __name__=='__main__':
    pa=argparse.ArgumentParser();pa.add_argument('--source',type=Path,required=True);pa.add_argument('--out',type=Path,required=True);pa.add_argument('--boot',type=int,default=10000)
    a=pa.parse_args();print(json.dumps(study(a.source,a.out,a.boot),indent=2))
