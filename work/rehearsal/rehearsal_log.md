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
