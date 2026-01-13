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
