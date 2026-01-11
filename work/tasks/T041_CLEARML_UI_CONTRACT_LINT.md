# T041 ClearML UI契約 lint 強化（doctor/CIで逸脱を検知）

## Objective
- ClearML UI契約（Project/Task命名、Properties/Artifactsの最小セット）を **自動検知**できるようにし、運用時に UI が崩壊しない状態を作る
- ローカル実行（ClearML無効）でも **同じ契約**を満たしているか検証できるようにする
- 既存の `tabular_analysis.doctor` と `tools/tests/verify_all.py` に統合し、開発者が迷わず検証できる導線にする

---

## Background / Constraints
- ml-platform は変更しない（Solution 側で完結）。platform 依存は `platform_adapter` に閉じ込める
- ClearML が使えない環境でも verify が通る必要がある（ClearML API を必須にしない）
- 「解析種が増えすぎて ClearML がノイズだらけ」にならないよう、Properties は検索用の短いキーに限定し、詳細は Artifact（JSON/MD）へ寄せる

---

## Scope
### 1) UI契約 lint の実装
- 新規モジュール例：`src/tabular_analysis/ops/ui_contract_lint.py`
  - 入力：run_dir（`outputs/...` など）を指定して lint
  - ルール：
    - 全タスク共通：`config_resolved.yaml`, `out.json`, `manifest.json` が存在
    - `manifest.json` に `schema_version`, `code_version`, `inputs`, `outputs` などがある（既存契約に合わせる）
    - `out.json` は task種別ごとの必須キーを満たす（例：train は `primary_metric`, `score`, `model_ref` など）
    - `decision_summary.md` / `report.md` など「任意 artifact」は存在すれば整形チェックのみ（必須化しない）
  - 失敗モード：
    - `--mode warn|fail` をサポート（デフォルト warn）
    - fail の場合は exit code != 0

### 2) doctor への統合
- `python -m tabular_analysis.doctor --lint-run <run_dir> --mode fail` のように実行できること
- 既存の `--lint-dir` がある場合は互換を壊さずに拡張

### 3) verify_all への統合
- `tools/tests/verify_all.py --quick` に UI契約 lint を含める
- ClearML が無効でも通るようにする（run_dir は local smoke の出力を使う）

---

## Acceptance Criteria
- UI契約 lint がローカル run_dir を対象に動作する
- ルール違反（例：manifest.json削除）で fail になることをテストで確認できる
- `verify_all --quick` が UI契約 lint を含んで成功する（ClearML無効でOK）
- docs（`docs/03_CLEARML_UI_CONTRACT.md`）に lint ルール（必須キー/必須artifact）が追記されている

---

## Implementation Notes
- 既存の `process_catalog` / `contract` 定義があるなら再利用し、二重定義しない
- ルールは「厳しすぎない」：運用上検索したいキーだけを Properties に要求し、詳細は artifact に寄せる方針を維持

---

## Verification
```bash
python -m compileall -q src
python tools/tests/test_ui_contract_lint.py
python tools/tests/verify_all.py --quick
```
