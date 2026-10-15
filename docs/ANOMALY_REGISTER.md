# Open anomalies and release gates

| ID | Risk | Mitigation/status |
|---|---|---|
| A1 | Binary TFRecords inaccessible in current tool connection | E3 execution blocked. Scripts and tests ready; original files required. |
| A2 | Processed target vs raw energy scope unclear | E3 consumes ONLY raw `total_energy` converted to J; reconciliation required. |
| A3 | Per-GPU runtime incomplete or mismatched to energy | Pair architecture AND GPU; require 88 complete 4-device rows and no duplicates. |
| A4 | Selection biased to strong fixed RTX 3060 | Include fixed-first and oracle; disclose small prior static oracle ceiling. |
| A5 | SLA deadlines chosen after outcomes | Prespecify factors, include infeasibility counts; label as sensitivity analysis. |
| A6 | Unavailable frozen transfer predictions | No prediction superiority claim in E3. |
| A7 | Temporal concurrency, idle power, interference missing | No true shared-cluster system savings claim. |
| A8 | Bootstrap/pseudoreplication | Architecture is inference unit; repeated GPU measurements do not generate new independent architectures. |
| A9 | Existing manuscript overlap | New question, experimental protocol, independently written text, clear link to predecessor. |
