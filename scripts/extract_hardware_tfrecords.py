#!/usr/bin/env python3
"""Extract measured EC-NAS total time and energy, without TensorFlow dependency.

TFRecord entries in the NASBench/EC-NAS convention are JSON five-tuples:
[architecture_hash, epochs, adjacency, operations, base64(ModelMetricsEnergy)].
If the format differs, raise instead of silently guessing.
"""
import argparse, base64, csv, json, struct, sys
from pathlib import Path

GPU_FILE={'Quadro RTX 6000':'quadrortx6000.tfrecord','RTX 3060':'rtx3060.tfrecord',
          'RTX 3090':'rtx3090.tfrecord','Titan Xp':'titanxp.tfrecord'}

def frames(path):
    with open(path,'rb') as fh:
        n=0
        while True:
            head=fh.read(12)
            if not head:break
            if len(head)!=12:raise ValueError(f'{path}: truncated TFRecord header')
            size=struct.unpack('<Q',head[:8])[0]
            if size>100_000_000:raise ValueError(f'{path}: implausibly large TFRecord frame')
            payload=fh.read(size); crc=fh.read(4)
            if len(payload)!=size or len(crc)!=4:raise ValueError(f'{path}: truncated TFRecord payload')
            n+=1
            yield n,payload

def decode(payload, proto):
    try:
        row=json.loads(payload.decode('utf-8'))
    except Exception as ex:raise ValueError('TFRecord entry is not NASBench JSON; inspect actual storage encoding') from ex
    if not isinstance(row,list) or len(row)!=5:raise ValueError('Expected NASBench JSON five-tuple')
    arch,epochs,_,_,encoded=row
    if not isinstance(encoded,str):raise ValueError('Expected base64 protobuf string')
    msg=proto.ModelMetricsEnergy()
    msg.ParseFromString(base64.b64decode("".join(encoded.split()),validate=True))
    time=float(msg.total_time); energy=float(msg.total_energy)
    if time<=0 or energy<=0:raise ValueError('Missing/non-positive measured time or energy')
    return {'architecture_hash':str(arch).strip().lower(),'epochs':int(epochs),
            'duration_seconds':time,'energy_kwh_raw':energy,
            'energy_joules_raw':energy*3_600_000}

def run(root,out,proto_dir):
    sys.path.insert(0,str(proto_dir.resolve()))
    try:import model_metrics_energy_pb2 as proto
    except ImportError as ex:raise RuntimeError('Supply --proto-dir containing model_metrics_energy_pb2.py from the project') from ex
    entries=[]; skipped={}
    for gpu,fn in GPU_FILE.items():
        path=root/fn
        if not path.is_file():raise FileNotFoundError(f'Missing original hardware TFRecord: {path}')
        for i,rec in frames(path):
            item=decode(rec,proto)
            item.update(gpu_type=gpu,source_file=str(path),source_record=i)
            if item['epochs']!=4:
                # Records for 12/36/108 epochs are linear extrapolations of the 4-epoch run; keep measured 4-epoch rows only.
                skipped[item['epochs']]=skipped.get(item['epochs'],0)+1
                continue
            entries.append(item)
    pair_set=set()
    for r in entries:
        k=(r['architecture_hash'],r['gpu_type'])
        if k in pair_set:raise ValueError(f'Duplicate architecture/GPU in hardware files: {k}')
        pair_set.add(k)
    out.parent.mkdir(parents=True,exist_ok=True)
    with open(out,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(entries[0])); w.writeheader(); w.writerows(entries)
    print(json.dumps({'records':len(entries),'unique_pairs':len(pair_set),'skipped_non_4_epoch_records':skipped,'output':str(out)},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--hardware-dir',type=Path,required=True)
    p.add_argument('--proto-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();run(a.hardware_dir,a.out,a.proto_dir)
