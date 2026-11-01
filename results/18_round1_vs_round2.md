# Pilot coding: round 1 vs. round 2

Round 1: 30 items, LLM coder with codebook v0.13. Round 2: 20 new items, LLM coder with codebook v1.0. V4 on F3 items only. Small n: one item moves kappa a lot.

| Variable | R1 n | R1 kappa | R1 agree % | R2 n | R2 kappa | R2 agree % |
| --- | --- | --- | --- | --- | --- | --- |
| V1_retraction_flag | 30 | 0.79 | 93.3 | 20 | 1.00 | 100.0 |
| V2_stance | 30 | 0.69 | 76.7 | 20 | 0.66 | 75.0 |
| V3_cited | 30 | 0.61 | 80.0 | 20 | 0.73 | 90.0 |
| V3_source | 30 | 0.52 | 73.3 | 20 | 0.74 | 90.0 |
| V4_status_answer | 6 | 1.00 | 100.0 | 4 | 1.00 | 100.0 |
| V5_fabrication | 30 | 0.63 | 93.3 | 20 | 0.00 | 95.0 |

| V1 positive | R1 sensitivity | R1 precision | R2 sensitivity | R2 precision |
| --- | --- | --- | --- | --- |
| EXPLICIT | 1.0 (5/5) | 0.714 (5/7) | 1.0 (6/6) | 1.0 (6/6) |
| EXPLICIT or INTEGRITY_CONCERN | 1.0 (5/5) | 0.714 (5/7) | 1.0 (6/6) | 1.0 (6/6) |
