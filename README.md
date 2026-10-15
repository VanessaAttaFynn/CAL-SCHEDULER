# CAL-SCHEDULER

Energy–delay analysis of GPU placement for neural-network training jobs, using the measured four-GPU
EC-NAS hardware records (Quadro RTX 6000, RTX 3060, RTX 3090, Titan Xp).

This project is separate from CAL-ENERGY and CAL-TRANSFER. It uses the same EC-NAS four-GPU benchmark,
but asks a different question: for each architecture, how much training energy could be saved by placing
the job on the lowest-energy GPU that still meets a completion-time deadline, compared with a fixed
RTX 3060-first policy?

## Repository layout

```
data/
  raw/ec_nas/hardware_tfrecords/   Original EC-NAS hardware measurement files (one .tfrecord per GPU)
  processed/ec_nas/                Processed four-GPU table used for reconciliation
src/nasbench_proto/                Protobuf decoder for the EC-NAS records
scripts/
  extract_hardware_tfrecords.py    Decode measured 4-epoch runtime and energy from the raw files
  reconcile_hardware.py            Check raw energy against the processed table; build 88-architecture matrices
  e3_energy_delay.py               E3: deadline-constrained energy-oracle vs RTX 3060-first placement
  decision_study.py                Unconstrained placement study with bootstrap intervals
  frozen_prediction_audit.py       Audit of exported out-of-sample predictions (for later prediction-based work)
  run_original_measurements.py     Alternative runner that downloads the source files from GitHub
tests/                             Unit tests for the E3 analysis
docs/                              Anomaly register and earlier environment notes
paper/                             Manuscript files
```

## Data

The raw files contain records at 4, 12, 36 and 108 epochs. Only the 4-epoch records are direct
measurements; the 12-, 36- and 108-epoch records are exact multiples (×3, ×9, ×27) of the 4-epoch values
and are skipped by the extractor. The retained data cover 91 / 88 / 91 / 91 architectures per GPU, with
88 architectures measured on all four GPUs.

Energy in the raw records is `total_energy` in kWh, converted to joules (× 3,600,000). Runtime is
`total_time` in seconds.

EC-NAS: P. Bakhtiarifard, C. Igel, R. Selvan, EC-NAS: Energy Consumption Aware Tabular Benchmarks for
Neural Architecture Search, ICASSP 2024, 5660–5664. https://doi.org/10.1109/ICASSP48485.2024.10448303

## Setup

```bash
python -m pip install -r requirements.txt
```

## Running E3 from the local data

```bash
python scripts/extract_hardware_tfrecords.py --hardware-dir data/raw/ec_nas/hardware_tfrecords --proto-dir src/nasbench_proto --out outputs/hardware_source.csv
python scripts/reconcile_hardware.py --hardware-csv outputs/hardware_source.csv --processed-csv data/processed/ec_nas/ec_nas_4v_hardware_features.csv --out outputs/reconciliation
python scripts/e3_energy_delay.py --source outputs/reconciliation/measured_energy_runtime_long_RAW_SCOPE.csv --out outputs/e3_results
python -m pytest -q tests
```

Outputs are written to `outputs/`, which is not tracked by git.

## Scope

Results are offline, per-job placement comparisons on measured benchmark data. They do not model queueing,
concurrency, idle power or shared-cluster interference. Deadline factors are scenario assumptions
(multiples of each architecture's measured RTX 3060 runtime), not observed job deadlines.

## License

MIT License. See `LICENSE`.
