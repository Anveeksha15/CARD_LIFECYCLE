# Rules baseline

Dataset: `python -m ml.generate_data` (seed 42, 99,095 rows). Synthetic data only.
Test slice = last 30% of the timeline (same split the models use).

| slice | precision | recall | F1 | FPR (normal) | campaign recall |
|---|---|---|---|---|---|
| all | 0.869 | 0.715 | 0.784 | 0.0040 | 0.836 |
| test | 0.558 | 0.568 | 0.563 | 0.0129 | 0.714 |

| scenario | share flagged |
|---|---|
| attack_burst | 0.922 |
| attack_rotating_ip | 0.006 |
| attack_slow | 0.079 |
| flash_sale | 0.311 |
| normal | 0.000 |
| normal_retry | 0.003 |
| normal_shared_ip | 0.000 |
