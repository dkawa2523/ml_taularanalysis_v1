## 2026-01-03T10:04:58Z
- mode: local
- dry_run: true
- usecase_id: test_toy_20260103_100458
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/local/test_toy_20260103_100458
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/local/test_toy_20260103_100458 run.usecase_id=test_toy_20260103_100458 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=false
```
- result: dry-run (not executed)
## 2026-01-03T10:07:25Z
- mode: local
- dry_run: true
- usecase_id: test_toy_20260103_100725
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/local/test_toy_20260103_100725
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/local/test_toy_20260103_100725 run.usecase_id=test_toy_20260103_100725 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=false
```
- result: dry-run (not executed)
## 2026-01-12T11:48:15Z
- mode: local
- dry_run: false
- usecase_id: test_toy_20260112_114815
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/local/test_toy_20260112_114815
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=dataset_register run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/local/test_toy_20260112_114815 run.usecase_id=test_toy_20260112_114815 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=false
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/local/test_toy_20260112_114815 run.usecase_id=test_toy_20260112_114815 data.raw_dataset_id=local:bcbef2dd65ddeef15c7461588644b7574a85f265ef0d5a8f07940b116941ee87 data.target_column=target data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv run.clearml.enabled=false
```
- result: failure
- error: Command failed (exit=1)
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/local/test_toy_20260112_114815 run.usecase_id=test_toy_20260112_114815 data.raw_dataset_id=local:bcbef2dd65ddeef15c7461588644b7574a85f265ef0d5a8f07940b116941ee87 data.target_column=target data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv run.clearml.enabled=false

Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/runpy.py", line 196, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/runpy.py", line 86, in _run_code
    exec(code, run_globals)
  File "/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/src/tabular_analysis/cli.py", line 137, in <module>
    main()
  File "/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/src/tabular_analysis/...
## 2026-01-12T11:50:06Z
- mode: local
- dry_run: false
- usecase_id: test_toy_20260112_115006
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/local/test_toy_20260112_115006
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=dataset_register run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/local/test_toy_20260112_115006 run.usecase_id=test_toy_20260112_115006 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=false
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/local/test_toy_20260112_115006 run.usecase_id=test_toy_20260112_115006 data.raw_dataset_id=local:bcbef2dd65ddeef15c7461588644b7574a85f265ef0d5a8f07940b116941ee87 data.target_column=target data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv run.clearml.enabled=false
```
- result: success
## 2026-01-12T12:27:45Z
- mode: logging
- dry_run: false
- usecase_id: test_toy_20260112_122745
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122745
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=dataset_register run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122745 run.usecase_id=test_toy_20260112_122745 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122745 run.usecase_id=test_toy_20260112_122745 data.raw_dataset_id= data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
```
- result: failure
- error: Command failed (exit=1)
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=dataset_register run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122745 run.usecase_id=test_toy_20260112_122745 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging

Traceback (most recent call last):
  File "/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/src/tabular_analysis/platform_adapter.py", line 1203, in init_task_context
    _ensure_clearml_parent(task, _normalize_str(parent_task_id))
NameError: name '_normalize_str' is not defined

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/runpy.py", line 196, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/...
## 2026-01-12T12:28:45Z
- mode: logging
- dry_run: false
- usecase_id: test_toy_20260112_122845
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122845
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=dataset_register run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122845 run.usecase_id=test_toy_20260112_122845 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122845 run.usecase_id=test_toy_20260112_122845 data.raw_dataset_id=2e482c5443e749ba81cbc04f4b07dee5 data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
```
- result: failure
- error: Command failed (exit=1)
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122845 run.usecase_id=test_toy_20260112_122845 data.raw_dataset_id=2e482c5443e749ba81cbc04f4b07dee5 data.target_column=target run.clearml.enabled=true run.clearml.execution=logging

Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/runpy.py", line 196, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/runpy.py", line 86, in _run_code
    exec(code, run_globals)
  File "/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/src/tabular_analysis/cli.py", line 137, in <module>
    main()
  File "/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/src/tabular_analysis/cli.py", line 133, in main
    runner(cfg)
  File "/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/s...
## 2026-01-12T12:29:14Z
- mode: logging
- dry_run: false
- usecase_id: test_toy_20260112_122914
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122914
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=dataset_register run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122914 run.usecase_id=test_toy_20260112_122914 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122914 run.usecase_id=test_toy_20260112_122914 data.raw_dataset_id=0faa456a53f541ad93a73895e5fdd202 data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
```
- result: failure
- error: Command failed (exit=1)
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122914 run.usecase_id=test_toy_20260112_122914 data.raw_dataset_id=0faa456a53f541ad93a73895e5fdd202 data.target_column=target run.clearml.enabled=true run.clearml.execution=logging

Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/runpy.py", line 196, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/runpy.py", line 86, in _run_code
    exec(code, run_globals)
  File "/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/src/tabular_analysis/cli.py", line 137, in <module>
    main()
  File "/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/src/tabular_analysis/cli.py", line 133, in main
    runner(cfg)
  File "/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/s...
## 2026-01-12T12:29:49Z
- mode: logging
- dry_run: false
- usecase_id: test_toy_20260112_122949
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122949
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=dataset_register run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122949 run.usecase_id=test_toy_20260112_122949 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260112_122949 run.usecase_id=test_toy_20260112_122949 data.raw_dataset_id=8e27c95d80c4442a98a38194980fa4ce data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
```
- result: success
## 2026-01-14T00:48:46Z
- execution: logging
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_004846
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260114_004846
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260114_004846 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260114_004846 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging

/Library/Frameworks/Python.framework/Versions/3.10/bin/python3: Error while finding module specification for 'tabular_analysis.cli' (ModuleNotFoundError: No module named 'tabular_analysis')
## 2026-01-14T01:25:35Z
- execution: logging
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_012535
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260114_012535
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260114_012535 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260114_012535 data.raw_dataset_id=354b227c4187442aac8e4249701a13c3 data.target_column=target run.clearml.enabled=true run.clearml.execution=logging pipeline.preprocess_variant=stdscaler_ohe 'pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260114_012535 data.raw_dataset_id=354b227c4187442aac8e4249701a13c3 data.target_column=target run.clearml.enabled=true run.clearml.execution=logging pipeline.preprocess_variant=stdscaler_ohe 'pipeline.model_variants=[ridge,elasticnet]'

Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/site-packages/hydra/_internal/config_loader_impl.py", line 390, in _apply_overrides_to_config
    OmegaConf.update(cfg, key, value, merge=True)
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/site-packages/omegaconf/omegaconf.py", line 741, in update
    root.__setattr__(last_key, value)
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/site-packages/omegaconf/dictconfig.py", line 337, in __setattr__
    raise e
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/site-packages/omegaconf/dictconfig.py", line 334, in __se...
## 2026-01-14T01:27:45Z
- execution: logging
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_012745
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260114_012745
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_012745 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260114_012745 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_012745 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260114_012745 data.raw_dataset_id=7e0e58e8a5ef4b6188228ba610e01545 data.target_column=target run.clearml.enabled=true run.clearml.execution=logging +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/tools/tests/rehearsal_verify_clearml_ui.py --usecase-id test_toy_20260114_012745

usecase_id: test_toy_20260114_012745
- dataset_register: 2
  - 7b4a35debaaa4798993978816c32496b completed dataset_register version_num=empty
  - 7e0e58e8a5ef4b6188228ba610e01545 completed test_toy_20260114_012745__raw__toy version_num=empty
- leaderboard: 1
  - ee72d3ef49a5435ab68b0edd51c22a6e completed pipeline version_num=empty
- preprocess: 1
  - 23e2877127834e098368027c304aad24 completed processed__test_toy_20260114_012745__stdscaler_ohe__d50f4fad9677a48e9305be7fdf75f238bce2b64130455ab898d66b0ad9c64b6f__vv1 version_num=empty
warnings:
- hyperparameters missing expected sections: preprocess 23e2877127834e098368027c304aad24
- hyperparameters missing expected sections: dataset_register 7e0e58e8a5ef4b6188228ba610e01545
errors:
- missing processes: pipeline, train_model
## 2026-01-14T02:02:16Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_020216
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_020216
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_020216 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_020216 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_020216 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_020216 data.raw_dataset_id=2c693d3782ba44c5a28f93350df6e3a0 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_020216 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_020216 data.raw_dataset_id=2c693d3782ba44c5a28f93350df6e3a0 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'

[warn] clearml-agent not found. Install it or disable remote execution (queue=default).
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/runpy.py", line 196, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/runpy.py", line 86, in _run_code
    exec(code, run_globals)
  File "/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/src/tabular_analysis/cli.py", line 126, in <module>
    main()
  File "/Users/kawahito/Desktop/ml_polyrepo_workspa...
## 2026-01-14T02:14:18Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_021418
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_021418
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_021418 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_021418 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_021418 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_021418 data.raw_dataset_id=dfbd217bd20443ab8ba298254744b7f0 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_021418 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_021418 data.raw_dataset_id=dfbd217bd20443ab8ba298254744b7f0 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'

[warn] clearml-agent not found. Install it or disable remote execution (queue=default).
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/runpy.py", line 196, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/runpy.py", line 86, in _run_code
    exec(code, run_globals)
  File "/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/src/tabular_analysis/cli.py", line 126, in <module>
    main()
  File "/Users/kawahito/Desktop/ml_polyrepo_workspa...
## 2026-01-14T02:15:39Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_021539
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_021539
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_021539 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_021539 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_021539 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_021539 data.raw_dataset_id=05e377c4520a4cdbb2410c9b535a5790 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_021539 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_021539 data.raw_dataset_id=05e377c4520a4cdbb2410c9b535a5790 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'

Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/runpy.py", line 196, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/runpy.py", line 86, in _run_code
    exec(code, run_globals)
  File "/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/src/tabular_analysis/cli.py", line 126, in <module>
    main()
  File "/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/src/tabular_analysis/cli.py", line 122, in main
    r...
## 2026-01-14T03:15:03Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_031503
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_031503
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_031503 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_031503 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_031503 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_031503 data.raw_dataset_id=a6dc24cbe9004cd0a285c14bf9d53b20 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/tools/tests/rehearsal_verify_clearml_ui.py --usecase-id test_toy_20260114_031503

usecase_id: test_toy_20260114_031503
- dataset_register: 2
  - a321c1380fe544c19d623378f9c6dc14 completed dataset_register version_num=empty
  - a6dc24cbe9004cd0a285c14bf9d53b20 completed test_toy_20260114_031503__raw__toy version_num=empty
- pipeline: 1
  - 7f2598d1438740739fb5916c1ffc24cd queued pipeline version_num=empty
warnings:
- hyperparameters missing expected sections: dataset_register a6dc24cbe9004cd0a285c14bf9d53b20
errors:
- missing processes: leaderboard, preprocess, train_model
## 2026-01-14T03:29:58Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_032958
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_032958
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_032958 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_032958 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_032958 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_032958 data.raw_dataset_id=0525586c6f17447ab820ede032abd9a9 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-14T03:42:24Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_034224
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_034224
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_034224 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_034224 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_034224 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_034224 data.raw_dataset_id=0ad212e4dc9c48f3b0f96e6db38de90e data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-14T06:32:53Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_063253
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_063253
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_063253 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_063253 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_063253 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_063253 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging

Parameters must be of builtin type (eval/eval.thresholding.grid[ListConfig], eval/eval.metrics.regression[ListConfig], eval/eval.metrics.classification_multiclass[ListConfig], eval/eval.metrics.classification_imbalance[ListConfig])
InsecureRequestWarning: Certificate verification is disabled! Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings
InsecureRequestWarning: Certificate verification is disabled! Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings
Traceback (most recent call last):
  File "/Users/kawahit...
## 2026-01-14T07:48:28Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_074828
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_074828
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_074828 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_074828 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_074828 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_074828 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging

Parameters must be of builtin type (eval/eval.thresholding.grid[ListConfig], eval/eval.metrics.regression[ListConfig], eval/eval.metrics.classification_multiclass[ListConfig], eval/eval.metrics.classification_imbalance[ListConfig])
InsecureRequestWarning: Certificate verification is disabled! Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings
InsecureRequestWarning: Certificate verification is disabled! Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings
Traceback (most recent call last):
  File "/Users/kawahit...
## 2026-01-14T07:48:49Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_074849
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_074849
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_074849 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_074849 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_074849 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_074849 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging

Parameters must be of builtin type (eval/eval.thresholding.grid[ListConfig], eval/eval.metrics.regression[ListConfig], eval/eval.metrics.classification_multiclass[ListConfig], eval/eval.metrics.classification_imbalance[ListConfig])
InsecureRequestWarning: Certificate verification is disabled! Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings
InsecureRequestWarning: Certificate verification is disabled! Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings
Traceback (most recent call last):
  File "/Users/kawahit...
## 2026-01-14T08:02:49Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_080249
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_080249
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_080249 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_080249 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_080249 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_080249 data.raw_dataset_id=a09f15a8e49b44269e7563fff4637ea5 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-14T08:15:32Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_081532
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_081532
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_081532 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_081532 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_081532 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_081532 data.raw_dataset_id=5c7aec515e2a4fd6b94215394e4a7447 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-14T10:29:44Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_102944
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_102944
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_102944 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_102944 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_102944 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_102944 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging

/Library/Frameworks/Python.framework/Versions/3.10/bin/python3: Error while finding module specification for 'tabular_analysis.cli' (ModuleNotFoundError: No module named 'tabular_analysis')
## 2026-01-14T10:31:49Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_103149
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_103149
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_103149 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_103149 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_103149 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_103149 data.raw_dataset_id=1b45896bb7674d6daa47697050386b36 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default +pipeline.preprocess_variant=stdscaler_ohe +pipeline.model_set=regression_all
```
- result: success
## 2026-01-14T10:41:35Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_104135
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_104135
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_104135 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_104135 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_104135 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_104135 data.raw_dataset_id=99c90cd99f7742d5b45323af8a0e40dd data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default +pipeline.preprocess_variant=stdscaler_ohe +pipeline.model_set=regression_all
```
- result: success
## 2026-01-14T10:45:51Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_104551
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_104551
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_104551 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_104551 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_104551 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_104551 data.raw_dataset_id=c5ad7e75e02e48eaa921ce4812259b33 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default +pipeline.preprocess_variant=stdscaler_ohe +pipeline.model_set=regression_all
```
- result: success
## 2026-01-14T13:18:33Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_131833
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_131833
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_131833 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_131833 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging run.clearml.project_root=LOCAL
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_131833 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260114_131833 data.raw_dataset_id=f3b09256db134a7ab85d28c2f428aa88 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default run.clearml.project_root=LOCAL +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-14T13:30:23Z
- execution: logging
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260114_133023
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260114_133023
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260114_133023 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260114_133023 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging run.clearml.project_root=LOCAL
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260114_133023 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/logging/test_toy_20260114_133023 data.raw_dataset_id=8d82fef017654db4a86775e67d3b7f22 data.target_column=target run.clearml.enabled=true run.clearml.execution=logging run.clearml.project_root=LOCAL +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-16T02:34:55Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260116_023455
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260116_023455
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260116_023455 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260116_023455 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging run.clearml.project_root=LOCAL
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260116_023455 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260116_023455 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging run.clearml.project_root=LOCAL

/Library/Frameworks/Python.framework/Versions/3.10/bin/python3: Error while finding module specification for 'tabular_analysis.cli' (ModuleNotFoundError: No module named 'tabular_analysis')
## 2026-01-16T02:35:46Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260116_023546
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260116_023546
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260116_023546 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260116_023546 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging run.clearml.project_root=LOCAL
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260116_023546 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260116_023546 data.raw_dataset_id=3146a1dc54494ffea93ea1be84d3a767 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default run.clearml.project_root=LOCAL +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/tools/tests/rehearsal_verify_clearml_ui.py --usecase-id test_toy_20260116_023546 --project-root LOCAL

usecase_id: test_toy_20260116_023546
errors:
- missing processes: leaderboard, pipeline, preprocess, train_model
## 2026-01-16T02:55:21Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260116_025521
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260116_025521
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260116_025521 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260116_025521 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging run.clearml.project_root=LOCAL
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260116_025521 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260116_025521 data.raw_dataset_id=4701035b4d1a443fa24928a74f9594ba data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default run.clearml.project_root=LOCAL +pipeline.preprocess_variant=stdscaler_ohe +pipeline.model_set=regression_all
```
- result: success
## 2026-01-16T03:54:19Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260116_035419
- repo: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260116_035419
- python: 3.10.8 (/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260116_035419 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260116_035419 data.dataset_path=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv data.target_column=target run.clearml.enabled=true run.clearml.execution=logging run.clearml.project_root=LOCAL
$ /Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/.venv/bin/python -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260116_035419 run.output_dir=/Users/kawahito/Desktop/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260116_035419 data.raw_dataset_id=1c4ebb141c914edba6ca8e33f41d09d6 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default run.clearml.project_root=LOCAL +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[catboost,elasticnet,extra_trees,gaussian_process,gradient_boosting,knn,lasso,lgbm,linear_regression,mlp,random_forest,ridge,svc,svr,xgboost]'
```
- result: success
## 2026-01-25T02:52:34Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_025234
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_025234
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_025234 'run.output_dir='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_025234'"'"'' 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_025234 'run.output_dir='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_025234'"'"'' data.raw_dataset_id=ad779bb86e1844e3bbb19c3e4a958074 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 '/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/tools/tests/rehearsal_verify_clearml_ui.py' --usecase-id test_toy_20260125_025234

usecase_id: test_toy_20260125_025234
- dataset_register: 2
  - ea24d5c224c64593808ccebb122e41d9 completed dataset_register version_num=empty
  - ad779bb86e1844e3bbb19c3e4a958074 completed test_toy_20260125_025234__raw__toy version_num=empty
- pipeline: 1
  - 5ae063eb014f4c96a5c8f7624d6a6f5c queued pipeline version_num=empty
errors:
- missing processes: leaderboard, preprocess, train_model
## 2026-01-25T02:56:29Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_025629
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_025629
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_025629 'run.output_dir='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_025629'"'"'' 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_025629 'run.output_dir='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_025629'"'"'' data.raw_dataset_id=3d06ad46b4f94d69963455641b8e4faf data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=clearml-agent-services +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_025629 'run.output_dir='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_025629'"'"'' data.raw_dataset_id=3d06ad46b4f94d69963455641b8e4faf data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=clearml-agent-services +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'

[warn] clearml-agent not found. Install it or disable remote execution (queue=clearml-agent-services).
InsecureRequestWarning: Certificate verification is disabled! Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings
InsecureRequestWarning: Certificate verification is disabled! Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.10/lib/pyth...
## 2026-01-25T02:58:55Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_025855
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_025855
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_025855 'run.output_dir='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_025855'"'"'' 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_025855 'run.output_dir='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_025855'"'"'' data.raw_dataset_id=e9133106391b4d79a69f885848995825 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 '/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/tools/tests/rehearsal_verify_clearml_ui.py' --usecase-id test_toy_20260125_025855

usecase_id: test_toy_20260125_025855
- dataset_register: 2
  - cb8cfc22838c43a4bb16143a175216d2 completed dataset_register version_num=empty
  - e9133106391b4d79a69f885848995825 completed test_toy_20260125_025855__raw__toy version_num=empty
- pipeline: 1
  - bb50b8d0d7f14ada8cb23733de7f0354 in_progress pipeline version_num=empty
errors:
- missing processes: leaderboard, preprocess, train_model
## 2026-01-25T04:27:19Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_042719
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_042719
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_042719 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_042719 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_042719 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_042719 data.raw_dataset_id=90266f17229640438c24358ddec5f134 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-25T04:31:31Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_043131
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_043131
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_043131 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_043131 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_043131 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_043131 data.raw_dataset_id=2d153c798cab4c3f80d92338f6ef8833 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-25T06:28:30Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_062830
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_062830
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_062830 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_062830 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_062830 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_062830 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging

/Library/Frameworks/Python.framework/Versions/3.10/bin/python3: Error while finding module specification for 'tabular_analysis.cli' (ModuleNotFoundError: No module named 'tabular_analysis')
## 2026-01-25T06:29:36Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_062936
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_062936
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_062936 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_062936 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_062936 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_062936 data.raw_dataset_id=59166329ec6144709523367a341833a9 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-25T06:47:04Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_064704
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_064704
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_064704 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_064704 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_064704 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_064704 data.raw_dataset_id=40628dcaea1847db9f4ad48f8931f48d data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-25T07:15:30Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_071530
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_071530
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_071530 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_071530 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_071530 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_071530 data.raw_dataset_id=9dca2a3c6a16421eaf17367838f7a62e data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-25T08:03:50Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_080350
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_080350
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_080350 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_080350 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_080350 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_080350 data.raw_dataset_id=b10d8507af41426ab3521bf1edf0e419 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-25T08:07:24Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_080724
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_080724
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_080724 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_080724 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_080724 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_080724 data.raw_dataset_id=7d514e5dbd1648b8a9cebd39c244629a data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-25T08:48:41Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_084841
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_084841
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_084841 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_084841 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_084841 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_084841 data.raw_dataset_id=8d76cd39b01f422183331b47d66db639 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 '/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/tools/tests/rehearsal_verify_clearml_ui.py' --usecase-id test_toy_20260125_084841

usecase_id: test_toy_20260125_084841
- dataset_register: 2
  - c0b71f3366e84c6f8f7e73e7f3e58a72 completed dataset_register version_num=empty
  - 8d76cd39b01f422183331b47d66db639 completed test_toy_20260125_084841__raw__toy version_num=empty
- pipeline: 1
  - c2eed58077f64df192a7f03fb626d4b6 queued pipeline version_num=empty
errors:
- missing processes: leaderboard, preprocess, train_model
## 2026-01-25T08:49:42Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_084942
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_084942
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_084942 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_084942 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_084942 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_084942 data.raw_dataset_id=a36592b823824527ba1f18b2d3f55320 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 '/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/tools/tests/rehearsal_verify_clearml_ui.py' --usecase-id test_toy_20260125_084942

usecase_id: test_toy_20260125_084942
- dataset_register: 2
  - 1e75d3573e1e4ae9ae1b860d3831261b completed dataset_register version_num=empty
  - a36592b823824527ba1f18b2d3f55320 completed test_toy_20260125_084942__raw__toy version_num=empty
- pipeline: 1
  - f6e4feb816904be9814affa4c5c6001f queued pipeline version_num=empty
errors:
- missing processes: leaderboard, preprocess, train_model
## 2026-01-25T09:15:15Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_091515
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_091515
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_091515 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_091515 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_091515 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_091515 data.raw_dataset_id=384d04b5ce57472090af92fef79cca51 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 '/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/tools/tests/rehearsal_verify_clearml_ui.py' --usecase-id test_toy_20260125_091515

usecase_id: test_toy_20260125_091515
- dataset_register: 2
  - 61a4de00f6a1417aa2886704caad673f completed dataset_register version_num=empty
  - 384d04b5ce57472090af92fef79cca51 completed test_toy_20260125_091515__raw__toy version_num=empty
- pipeline: 1
  - e1e29d9b4f2a498eb6bfbaf148ec4761 queued pipeline version_num=empty
errors:
- missing processes: leaderboard, preprocess, train_model
## 2026-01-25T10:22:35Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_102235
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_102235
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_102235 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_102235 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_102235 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_102235 data.raw_dataset_id=323ee4d1e16a4a2784da12be208aa3d8 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 '/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/tools/tests/rehearsal_verify_clearml_ui.py' --usecase-id test_toy_20260125_102235

usecase_id: test_toy_20260125_102235
- dataset_register: 2
  - 80a9701a0680481b87cc7a7f6af54231 completed dataset_register version_num=empty
  - 323ee4d1e16a4a2784da12be208aa3d8 completed test_toy_20260125_102235__raw__toy version_num=empty
- pipeline: 1
  - db5a901e9ddc4843b0d107a383de0b53 in_progress pipeline version_num=empty
errors:
- missing processes: leaderboard, preprocess, train_model
## 2026-01-25T12:24:25Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_122425
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_122425
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_122425 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_122425 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_122425 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_122425 data.raw_dataset_id=9c57ff91c41144ce809c6731c294e84a data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 '/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/tools/tests/rehearsal_verify_clearml_ui.py' --usecase-id test_toy_20260125_122425

usecase_id: test_toy_20260125_122425
- dataset_register: 2
  - 10cbc0d92eff43c99275364e1f0f2667 completed dataset_register version_num=empty
  - 9c57ff91c41144ce809c6731c294e84a completed test_toy_20260125_122425__raw__toy version_num=empty
- pipeline: 1
  - 5ccab9052eea4168841452f91cc67e3e queued pipeline version_num=empty
errors:
- missing processes: leaderboard, preprocess, train_model
## 2026-01-25T12:39:18Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_123918
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_123918
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_123918 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_123918 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_123918 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_123918 data.raw_dataset_id=90373b617e534275b64857478a7eee8e data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 '/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/tools/tests/rehearsal_verify_clearml_ui.py' --usecase-id test_toy_20260125_123918

usecase_id: test_toy_20260125_123918
- dataset_register: 2
  - 236a06c377c846448787a6368939fb2b completed dataset_register version_num=empty
  - 90373b617e534275b64857478a7eee8e completed test_toy_20260125_123918__raw__toy version_num=empty
- pipeline: 1
  - 6e1aa18947ea4639aab5881b5d3847c2 in_progress pipeline version_num=empty
errors:
- missing processes: leaderboard, preprocess, train_model
## 2026-01-25T22:50:59Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260125_225059
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260125_225059
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260125_225059 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_225059 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260125_225059 run.output_dir=work/rehearsal/out/agent/test_toy_20260125_225059 data.raw_dataset_id=9d55e85b320f442b9d8ce7ca6c9f9974 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: failure
- error: Command failed (exit=1)
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 '/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/tools/tests/rehearsal_verify_clearml_ui.py' --usecase-id test_toy_20260125_225059

usecase_id: test_toy_20260125_225059
- dataset_register: 2
  - f3ea57e918f2424bbca25ee0168f55d7 completed dataset_register version_num=empty
  - 9d55e85b320f442b9d8ce7ca6c9f9974 completed test_toy_20260125_225059__raw__toy version_num=empty
- pipeline: 1
  - a524495ea4ee464a9ef061aa58b7ab21 in_progress pipeline version_num=empty
errors:
- missing processes: leaderboard, preprocess, train_model
## 2026-01-26T00:22:46Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260126_002246
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260126_002246
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260126_002246 run.output_dir=work/rehearsal/out/agent/test_toy_20260126_002246 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260126_002246 run.output_dir=work/rehearsal/out/agent/test_toy_20260126_002246 data.raw_dataset_id=f51e39600f0946c6ac1de99a58aa7b59 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-26T00:53:21Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260126_005321
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260126_005321
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260126_005321 run.output_dir=work/rehearsal/out/agent/test_toy_20260126_005321 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260126_005321 run.output_dir=work/rehearsal/out/agent/test_toy_20260126_005321 data.raw_dataset_id=4148e7596249412aa611b1789a269282 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-26T04:06:16Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260126_040616
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260126_040616
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260126_040616 run.output_dir=work/rehearsal/out/agent/test_toy_20260126_040616 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260126_040616 run.output_dir=work/rehearsal/out/agent/test_toy_20260126_040616 data.raw_dataset_id=7d09821e3c16406cbb51211babca8f00 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-26T04:07:48Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260126_040748
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260126_040748
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260126_040748 run.output_dir=work/rehearsal/out/agent/test_toy_20260126_040748 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260126_040748 run.output_dir=work/rehearsal/out/agent/test_toy_20260126_040748 data.raw_dataset_id=c848c480434643839f032828df53e289 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-26T04:15:26Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260126_041526
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260126_041526
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260126_041526 run.output_dir=work/rehearsal/out/agent/test_toy_20260126_041526 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260126_041526 run.output_dir=work/rehearsal/out/agent/test_toy_20260126_041526 data.raw_dataset_id=47a33c8d32994c8087cfb39d4c03ec5c data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-26T04:24:32Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260126_042432
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260126_042432
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260126_042432 run.output_dir=work/rehearsal/out/agent/test_toy_20260126_042432 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260126_042432 run.output_dir=work/rehearsal/out/agent/test_toy_20260126_042432 data.raw_dataset_id=3b6a00e9be06491490fbff16164847e5 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
## 2026-01-26T04:27:18Z
- execution: agent
- task_type: regression
- dry_run: false
- usecase_id: test_toy_20260126_042718
- repo: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis
- dataset_path: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv
- output_dir: /Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/out/agent/test_toy_20260126_042718
- python: 3.10.8 (/Library/Frameworks/Python.framework/Versions/3.10/bin/python3)
- platform: macOS-14.5-arm64-arm-64bit
- commands:
```bash
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=dataset_register run.usecase_id=test_toy_20260126_042718 run.output_dir=work/rehearsal/out/agent/test_toy_20260126_042718 'data.dataset_path='"'"'/Volumes/SP PX10/Main_code/ml_polyrepo_workspace_v1/ml-solution-tabular-analysis/work/rehearsal/tmp/toy.csv'"'"'' data.target_column=target run.clearml.enabled=true run.clearml.execution=logging
$ /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m tabular_analysis.cli task=pipeline run.usecase_id=test_toy_20260126_042718 run.output_dir=work/rehearsal/out/agent/test_toy_20260126_042718 data.raw_dataset_id=dfcb1715ee0b4e9290e9ebfe71940d76 data.target_column=target run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=services run.clearml.env.bootstrap=uv run.clearml.env.uv.all_extras=true run.clearml.env.uv.frozen=true +pipeline.preprocess_variant=stdscaler_ohe '+pipeline.model_variants=[ridge,elasticnet]'
```
- result: success
