# Reproduction access record

- The public project repository enumerates four files: quadrortx6000.tfrecord, rtx3060.tfrecord, rtx3090.tfrecord, titanxp.tfrecord under data/raw/ec_nas/hardware_tfrecords/.
- A GitHub blob-read attempt for the RTX 3060 file returned a binary/UTF-8 decoding error rather than data.
- Direct HTTPS retrieval from this execution container failed with DNS resolution error for raw.githubusercontent.com.
- Therefore source-measured E3 numerical results are NOT available in this session.
- The source-provided protobuf schema describes total_energy in kWh and total_time as total runtime.
