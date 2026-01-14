# T087 リハーサル用 Python runner を追加（jq不要・Local/Agentの再検証を1コマンド化）

## 背景（課題）
- bash + jq 前提の検証は環境差で壊れやすい（jq無し等）
- quoting エラー（zsh parse error）も発生しやすい
- 試験段階では “コマンド一式” を誰でも再現できることが重要

---

## 目的
- `tools/rehearsal/` 配下に Python runner を追加し、以下を 1コマンドで再現:
  - toy データ生成
  - dataset_register（ローカル）
  - pipeline（Local逐次 / Agent controller）実行
  - ClearML の Task 一覧・ステータス確認
  - 主要 Task id を out.json に保存
- jq 不要、macOS / Linux で動く

---

## 実装内容
### 1) runner スクリプト追加
例:
- `tools/rehearsal/run_train_pipeline.py`
  - 引数:
    - `--mode local|agent`（local=逐次、agent=pipeline_controller）
    - `--task-type regression|classification`
    - `--models all|small`（small は 2〜3モデル）
    - `--preprocess stdscaler_ohe` など（複数可）
    - `--usecase-id` 未指定なら自動生成
    - `--project-root` / `--queue-name`
    - `--out-root`（/tmp/ta_rehearsal_runs など）
  - 生成物:
    - `${out_root}/run_summary.json`（raw_ds_id、pipeline_task_id、train_task_ids 等）

- `tools/rehearsal/inspect_clearml_usecase.py`
  - `--usecase-id`
  - tags で tasks を列挙し、processごとに整列して表示
  - pipeline task が failed の場合は “script/repo/branch/version pin” を表示（原因究明の入口）

### 2) subprocess 呼び出しを安全に
- `python -m tabular_analysis.cli ...` を list argv で渡す（shell=True禁止）
- Hydra override は `key=value` をそのまま argv に積む
- JSON 引数（model_variants 等）は python 側で `json.dumps()` して渡す

### 3) ClearML SDK での確認（任意）
- clearml が import できる場合のみ Task.get_tasks を実行
- import できない場合でもローカル実行は可能（ログに注意喚起）

---

## 受け入れ基準（Acceptance Criteria）
- jq 無しで “一連の検証” が 1コマンドで実行できる
- runner が out_root に summary json を作り、次の工程で参照できる
- `python -m compileall -q src tools` が通る

---

## テスト
- `python -m compileall -q src tools`
- （ClearML接続あり）:
  - `python tools/rehearsal/run_train_pipeline.py --mode local --task-type regression --models small`
  - `python tools/rehearsal/run_train_pipeline.py --mode agent  --task-type regression --models small --queue-name default`

---

## Update (2026-01-13)
- `run_rehearsal.py` は `raw_dataset_id` 必須の pipeline 入力と不整合のため見直しが必要
- refactor plan の Phase 1 (T101) で runner を再設計する
- `tools/rehearsal/run_pipeline_v2.py` を追加し、dataset_register → pipeline を1コマンド化
- `tools/rehearsal/run_rehearsal.py` は run_pipeline_v2 のラッパに整理
