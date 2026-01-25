# Infer Summary

- mode: batch
- schema_validation_mode: warn
- schema_validation_ok: True
- warnings_count: 0
- errors_count: 0

## Drift Summary
- rows: 60
- metrics: psi, ks
- psi_max: 7.886527236245777
- psi_mean: 1.9621526444752626
- ks_max: 0.6
- ks_mean: 0.19
- warn_count: 2
- fail_count: 0
- drift_alert: True

### Top Drift Features
- num__num1 (numeric): psi=7.8865 [warn]
- num__num2 (numeric): psi=1.9242 [warn]
- cat__cat_a (numeric): psi=0.0000 [ok]
- cat__cat_b (numeric): psi=0.0000 [ok]
- cat__cat_c (numeric): psi=0.0000 [ok]
