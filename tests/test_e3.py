import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from e3_energy_delay import run,validate,GPUS

def test_feasibility_and_savings():
 e=pd.DataFrame([[10.,8.,7.,15.]]*88,columns=GPUS,index=[f'id{i:03d}' for i in range(88)])
 t=pd.DataFrame([[6.,10.,9.,8.]]*88,columns=GPUS,index=e.index)
 r,d=run(e,t,factors=[.5,1,1.2])
 assert r.iloc[0]['feasible_architectures']==0
 assert r.iloc[1]['feasible_architectures']==88
 assert np.isclose(r.iloc[1]['oracle_saving_vs_fixed_first_pct'],12.5)
 assert (d[d.feasible==True].oracle_gpu=='RTX 3090').all()

def test_alignment():
 e=pd.DataFrame([[10.,8.,7.,15.]],columns=GPUS,index=['a'])
 t=e.rename(index={'a':'b'})
 with pytest.raises(ValueError,match='Misaligned'):run(e,t)

def test_reject_incomplete(tmp_path):
 f=tmp_path/'fake.csv'
 pd.DataFrame([dict(architecture_hash='abc',gpu_type='RTX 3060',duration_seconds=10,energy_joules_raw=15)]).to_csv(f,index=False)
 with pytest.raises(ValueError,match='Incomplete'):validate(f)
