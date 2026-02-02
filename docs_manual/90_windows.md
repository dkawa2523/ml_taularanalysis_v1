# Windows 実行ガイド

## 前提
- Python 3.10+（公式インストーラ）
- PowerShell 7 推奨
- Docker Desktop（ClearML を使う場合）

## 重要な差分
- `/tmp/...` は Windows では存在しません。`$env:TEMP` を使ってください。
  - 例: `$env:TEMP\ta_rehearsal_data\toy_reg.csv`
- PowerShell では `\` がパス区切り、`$env:VAR` が環境変数です。
- bash 前提のスクリプトは WSL または Git Bash を使用してください。

## 典型コマンド例（PowerShell）

### Local 実行（ClearML なし）
```powershell
python -m tabular_analysis.cli task=dataset_register \
  run.clearml.enabled=false \
  data.dataset_path="$env:TEMP\\ta_rehearsal_data\\toy_reg.csv" data.target_column=target
```

### Local 実行 + ClearML 登録
```powershell
python -m tabular_analysis.cli task=infer infer.mode=single \
  run.clearml.enabled=true run.clearml.execution=logging \
  infer.model_id=<MODEL_ID> infer.input_path="$env:TEMP\\infer.csv"
```

## ClearML 関連の注意
- `clearml.conf` は `%USERPROFILE%\.clearml.conf` を推奨
- `files_server` が `localhost:8081` の場合、Windows ローカルからも問題なく参照可能
- Docker コンテナ内では `host.docker.internal` が解決されます（Windows の Docker Desktop では既定で有効）

## 開発系スクリプト
- `tools/codex_loop/*.sh` 等は **WSL/Git Bash 前提**
- PowerShell で実行する場合は `python tools/...` に置き換えるか、WSL を使ってください

