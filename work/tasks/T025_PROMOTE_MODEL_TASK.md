# T025 運用導線: promote_model タスク（推薦モデルを "昇格" する）

## Objective
- leaderboard の推薦モデル（recommended_model_id）を、運用上の "ステージ"（staging/prod 等）へ昇格させる作業をタスク化する
- ClearML を有効にしている場合は **Model Registry への登録/タグ付け**まで行えるようにする
- ClearML 無効の場合でもローカルで `promotion.json` を出して追跡できるようにする

---

## Scope
1) 新規プロセス `promote_model` を追加
- `conf/task/promote_model/base.yaml`
- `src/tabular_analysis/processes/promote_model.py`
- `cli` の task ルーティングに追加

2) 入力と動作
- 入力（最低限）
  - `promotion.source_leaderboard_dir`（local の leaderboard 出力ディレクトリ）または `promotion.recommended_model_id` を直接
  - `promotion.stage: staging | production | archived`（文字列）
  - `promotion.note`（任意）
- 出力
  - `promotion.json`（必須: model_id, stage, timestamp, source, metric など）
  - `summary.md`（推奨: 人が読める）
  - `out.json` / `manifest.json` は通常規約通り

3) ClearML 有効時
- `platform_adapter` もしくは ClearML SDK で、モデル（Artifact or Model）に以下を付与
  - tags: `stage:staging` のような形（既存方針に合わせる）
  - properties: usecase_id, task_type, metric, score, split_hash, recipe_hash 等
- 失敗した場合は "昇格できなかった" を明確に out.json に記録し、非ゼロで落とす

4) テスト追加
- `tools/tests/smoke_promote_model.py`
  - local で `pipeline`（または leaderboard まで）を実行
  - `promote_model` を local mode で実行
  - `promotion.json` が存在し、`stage` と `model_id` を含むこと

5) docs
- `docs/16_OPERATIONS_RUNBOOK.md`（新規）を追加し、
  - 推薦モデル選定→promote_model→推論運用 の流れを簡潔に書く

---

## Acceptance Criteria
- `python -m tabular_analysis.cli task=promote_model ...` が local mode で完走し、promotion.json を出す
- smoke_promote_model.py が通る

---

## Verification（runner 側で実行）
- `python tools/tests/smoke_promote_model.py`
