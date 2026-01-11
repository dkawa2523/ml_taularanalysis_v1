# T022 doctor 強化: env check + contract lint を「失敗で落ちる」形にする

## Objective
- `python -m tabular_analysis.doctor` を **運用前検査として実用レベル**に引き上げる
- run_dir（outputs）に対して、UI契約・I/O契約が破れていれば **必ず非ゼロで落ちる** lint を提供する
- CI / verify_all で再利用できる入口にする

---

## Scope
1) `src/tabular_analysis/doctor.py` を実装（弱い場合は作り直し）
   - `--lint-dir <path>`: 1つの stage 出力ディレクトリを lint
   - `--lint-run <path>`: `run.output_dir`（例: `work/_smoke/out`）配下の全 stage を lint
   - `--strict`（任意）: warning ではなく error 扱いにする

2) env check
- `import ml_platform` が通ること（platform_adapter 経由でも OK）
- `conf/` が存在すること

3) contract lint（最低限）
- `config_resolved.yaml` / `out.json` / `manifest.json` の存在
- `manifest.json` の必須キー（例）
  - `process.name`
  - `created_at`
  - `config_hash`（または同等の追跡キー）
  - `schema_version` / `task_type`（存在する場合）
- `out.json` の必須キー（process 別の最小セット）
  - dataset_register: `raw_dataset_id`
  - preprocess: `processed_dataset_id`, `split_hash`, `recipe_hash`
  - train_model: `model_id`, `primary_metric`, `best_score`, `task_type`
  - leaderboard: `leaderboard_csv`, `recommended_model_id`
  - infer: `predictions_path`
  - pipeline: `pipeline_run`

4) テスト追加
- `tools/tests/smoke_doctor_lint.py`
  - `python tools/tests/smoke_local.py --until pipeline` を内部呼び出し
  - 生成された `work/_smoke/out` に対して `python -m tabular_analysis.doctor --lint-run work/_smoke/out` を実行
  - exit=0 を期待

5) `tools/tests/verify_all.py` に doctor lint を組み込む（T021 実装済み前提）

---

## Implementation Notes
- 外部依存（jsonschema 等）は追加しない（まずは自前の必須キー検査で十分）
- lint は「例外握りつぶし禁止」。検出したら `SystemExit(2)` などで落とす
- ただし strict でない場合は、"推奨" 項目（例: summary.md）が無い程度は warning 扱いでもよい

---

## Acceptance Criteria
- `python -m tabular_analysis.doctor --help` が表示される
- `python -m tabular_analysis.doctor --lint-dir <dir>` が機能する
- `python -m tabular_analysis.doctor --lint-run <out_root>` が機能する
- `tools/tests/smoke_doctor_lint.py` が通る

---

## Verification（runner 側で実行）
- `python tools/tests/smoke_doctor_lint.py`
