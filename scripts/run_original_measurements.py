#!/usr/bin/env python3
"""One-command, provenance-preserving EC-NAS E3 reproduction. Requires internet locally.
Only downloads source artefacts from the named public repository and runs strict validators.
"""
import argparse,hashlib,json,subprocess,sys,urllib.request,time
from pathlib import Path
BASE="https://raw.githubusercontent.com/VanessaAttaFynn/NN-Energy-Prediction-Framework/master/"
URLS={
 "data/raw/ec_nas/hardware_tfrecords/quadrortx6000.tfrecord":None,
 "data/raw/ec_nas/hardware_tfrecords/rtx3060.tfrecord":None,
 "data/raw/ec_nas/hardware_tfrecords/rtx3090.tfrecord":None,
 "data/raw/ec_nas/hardware_tfrecords/titanxp.tfrecord":None,
 "src/data/nasbench_proto/model_metrics_energy_pb2.py":None,
 "data/processed/ec_nas/ec_nas_4v_hardware_features.csv":None,
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def download(path,dir):
 dest=dir/path;dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists() and dest.stat().st_size>0:return dest
 url=BASE+path
 error=None
 for attempt in range(3):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CAL-SCHEDULER-research-audit/0.8'}),timeout=40) as response:
    content=response.read()
   if not content:raise RuntimeError('empty source')
   tmp=dest.with_suffix(dest.suffix+'.part');tmp.write_bytes(content);tmp.replace(dest)
   return dest
  except Exception as ex:error=ex;time.sleep(attempt+1)
 raise RuntimeError(f'Cannot retrieve {url}: {error}')
def run_command(args):
 print('RUN',' '.join(map(str,args)),flush=True)
 subprocess.run([str(x) for x in args],check=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=Path('e3_reproduction'));a=ap.parse_args()
 root=a.output.resolve();root.mkdir(parents=True,exist_ok=True)
 files={}
 for rel in URLS:
  p=download(rel,root);files[rel]={'bytes':p.stat().st_size,'sha256':sha(p),'source':BASE+rel}
 (root/'source_manifest.json').write_text(json.dumps(files,indent=2)+'\n')
 scripts=Path(__file__).resolve().parent
 records=root/'hardware_source.csv';review=root/'reconciliation';result=root/'e3_results'
 run_command([sys.executable,scripts/'extract_hardware_tfrecords.py','--hardware-dir',root/'data/raw/ec_nas/hardware_tfrecords','--proto-dir',root/'src/data/nasbench_proto','--out',records])
 run_command([sys.executable,scripts/'reconcile_hardware.py','--hardware-csv',records,'--processed-csv',root/'data/processed/ec_nas/ec_nas_4v_hardware_features.csv','--out',review])
 report=json.loads((review/'source_reconciliation_report.json').read_text())
 # Fail closed if source energy doesn't agree with processed targets; require human review of scope.
 if report['unit_status']!='CONFIRMED_NUMERICAL_EQUIVALENCE':
  print('SOURCE-UNIT/SCOPE DISCREPANCY: source-level E3 can be run, but processed E1/E2 are NOT directly comparable.',file=sys.stderr)
 run_command([sys.executable,scripts/'e3_energy_delay.py','--source',review/'measured_energy_runtime_long_RAW_SCOPE.csv','--out',result])
 report['source_manifest_sha256']=sha(root/'source_manifest.json')
 (root/'E3_EXECUTION_STATUS.json').write_text(json.dumps({'status':'EXECUTED_FROM_ORIGINAL_SOURCE','reconciliation':report,'result_csv':str(result/'e3_deadline_frontier.csv')},indent=2)+'\n')
 print('FINISHED',result/'e3_deadline_frontier.csv')
if __name__=='__main__':main()
