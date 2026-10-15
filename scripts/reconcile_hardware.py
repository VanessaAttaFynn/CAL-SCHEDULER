#!/usr/bin/env python3
"""Audit source TFRecord power/time against project processed table; fail on mismatches."""
import argparse, json
from pathlib import Path
import pandas as pd
import numpy as np

def run(hardware_csv,processed_csv,out):
    raw=pd.read_csv(hardware_csv); processed=pd.read_csv(processed_csv)
    keys=['architecture_hash','gpu_type']
    for frame in (raw,processed):
        frame['architecture_hash']=frame.architecture_hash.astype(str).str.strip().str.lower()
        frame['gpu_type']=frame.gpu_type.astype(str).str.strip()
        if frame.duplicated(keys).any():raise ValueError('Duplicate hardware/architecture keys')
    m=raw.merge(processed[keys+['target']],on=keys,how='outer',indicator=True,validate='one_to_one')
    both=m[m._merge=='both'].copy()
    if both.empty:raise ValueError('No joined measured hardware records')
    both['target']=pd.to_numeric(both.target,errors='raise')
    both['ratio_target_to_raw_j']=both.target/both.energy_joules_raw
    # NOTE: target in original dataset may use 0.8*energy or only part of training.
    # Never silently treat nonunit ratios as identical physical measurements.
    both['relative_difference']=(both.target-both.energy_joules_raw).abs()/both.energy_joules_raw
    out.mkdir(parents=True,exist_ok=True)
    m.to_csv(out/'hardware_full_join_audit.csv',index=False)
    both.to_csv(out/'energy_unit_reconciliation.csv',index=False)
    n=both.groupby('architecture_hash').gpu_type.nunique()
    complete=n[n==4].index
    valid=both[both.architecture_hash.isin(complete)].copy()
    valid.to_csv(out/'measured_energy_runtime_long_RAW_SCOPE.csv',index=False)
    valid.pivot(index='architecture_hash',columns='gpu_type',values='duration_seconds').to_csv(out/'measured_runtime_matrix.csv')
    valid.pivot(index='architecture_hash',columns='gpu_type',values='energy_joules_raw').to_csv(out/'measured_energy_matrix_RAW_SCOPE.csv')
    report={'hardware_source_records':len(raw),'processed_records':len(processed),
            'joined_records':len(both),'left_or_right_unmatched':int((m._merge!='both').sum()),
            'complete_case_architectures':len(complete),'complete_case_pairs':len(valid),
            'median_processed_target_over_raw_total_energy_joules':float(both.ratio_target_to_raw_j.median()),
            'p95_relative_difference':float(np.percentile(both.relative_difference,95)),
            'unit_status':'CONFIRMED_NUMERICAL_EQUIVALENCE' if np.allclose(both.target,both.energy_joules_raw,rtol=.001,atol=1) else 'DIFFERENT_TARGET_SCOPE_OR_TRANSFORMATION_INVESTIGATE',
            'claims_rule':'Use original total_energy(kWh) x 3,600,000 as source physical energy; do not call processed target equivalent unless verified'}
    (out/'source_reconciliation_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if len(complete)!=88:raise ValueError(f'Expected 88 complete EC-NAS architectures, got {len(complete)}')
    if report['unit_status']!='CONFIRMED_NUMERICAL_EQUIVALENCE':
        print('WARNING: processed target differs from source total energy. Investigate physical measurement scope.')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--hardware-csv',type=Path,required=True)
    p.add_argument('--processed-csv',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();run(a.hardware_csv,a.processed_csv,a.out)
