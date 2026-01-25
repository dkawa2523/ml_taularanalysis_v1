# Data Quality Summary

- quality_status: warn
- quality_issue_count: 9
- rows_total: 120
- rows_scanned: 120
- columns: 5
- sampled: False
- missing_columns: 0
- missing_rate_total: 0.000000
- duplicates_count: 0
- missing_top: n/a
- constant_columns: n/a
- mixed_type_columns: n/a
- high_cardinality_columns: record_id, cat_high
- id_like_columns: record_id(100.0%), cat_high(100.0%), feature(100.0%), leak_feature(100.0%)
- name_suspects: record_id:id_suspect(id)
- quality_issues: high_cardinality(warn,2), id_like(warn,4), name_suspect(warn,1), leak(warn,2)
- leak_suspects: leak_feature:high_correlation(warning,1.000), feature:high_correlation(warning,0.994)
