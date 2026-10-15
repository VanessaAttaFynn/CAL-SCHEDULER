#!/usr/bin/env python3
"""Audit externally exported CAL-TRANSFER predictions; no model retraining or relabelling.
Required columns: architecture_hash,gpu_type,predicted_energy_joules,outer_fold,
train_architecture_hashes,calibration_architecture_hashes. Split sets semicolon-delimited.
"""
import argparse,json,hashlib
from pathlib import Path
import pandas as pd
import numpy as np

def parse_hashes(v):return {s.strip().lower() for s in str(v).split(';') if s.strip() and s!='nan'}

def run(pred_file,measured_file,out):
    p=pd.read_csv(pred_file); m=pd.read_csv(measured_file)
    required={'architecture_hash','gpu_type','predicted_energy_joules','outer_fold','train_architecture_hashes','calibration_architecture_hashes'}
    if required-set(p):raise ValueError('Missing prediction/provenance fields: '+str(required-set(p)))
    p['architecture_hash']=p.architecture_hash.astype(str).str.strip().str.lower()
    m['architecture_hash']=m.architecture_hash.astype(str).str.strip().str.lower()
    p['predicted_energy_joules']=pd.to_numeric(p.predicted_energy_joules,errors='raise')
    if (~np.isfinite(p.predicted_energy_joules)| (p.predicted_energy_joules<=0)).any():raise ValueError('Invalid predictions')
    if p.duplicated(['architecture_hash','gpu_type']).any():raise ValueError('Duplicated OOF predictions')
    for r in p.itertuples():
        if r.architecture_hash in parse_hashes(r.train_architecture_hashes):raise ValueError('Test architecture found in training manifest')
        if r.architecture_hash in parse_hashes(r.calibration_architecture_hashes):raise ValueError('Test architecture found in calibration manifest')
    q=p.merge(m[['architecture_hash','gpu_type','energy_joules_raw']],on=['architecture_hash','gpu_type'],how='inner',validate='one_to_one')
    if len(q)!=len(m):raise ValueError(f'Prediction coverage incomplete: {len(q)} vs {len(m)} measured pairs')
    out.mkdir(parents=True,exist_ok=True); q.to_csv(out/'audited_oof_predictions.csv',index=False)
    report={'matched_pairs':len(q),'architectures':q.architecture_hash.nunique(),
            'folds':q.outer_fold.nunique(),'manifest_note':'Checks explicit declared sets, not the unseen training implementation. Independent code/provenance audit still required.',
            'predictions_sha256':hashlib.sha256(pred_file.read_bytes()).hexdigest()}
    (out/'prediction_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--predictions',type=Path,required=True)
    p.add_argument('--measured',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();run(a.predictions,a.measured,a.out)
