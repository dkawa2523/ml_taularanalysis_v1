# T088 docs 整備（試験段階の運用・テンプレ・命名則・Local/Agent実行・アンサンブル方針）

## 目的
試験段階では “命名や運用ルールを固定しない” 方針だが、将来の運用解析がしやすいように:
- 現在の推奨規約
- 変更ポイント（どこを変えれば良いか）
- リハーサル手順
を docs/ に明記する。

---

## 追加/更新する docs（例）
- `docs/80_CLEARML_EXECUTION_MODES.md`
  - local_sequential / pipeline_controller の違い
  - どの yaml をどう切替えるか
  - 典型コマンド例（Python runner含む）

- `docs/81_CLEARML_TEMPLATE_POLICY.md`
  - template_usecase_id / template_set_id の意味
  - `manage_clearml_templates --apply/--list` の使い方
  - テンプレ増殖を避ける運用（template_set の切替）

- `docs/82_CLEARML_PROJECT_LAYOUT.md`
  - `<root>/TabularAnalysis/<usecase_id>/<process_group>` 規約
  - `conf/clearml/project_layout.yaml` の編集方法

- `docs/83_ENSEMBLE_POLICY.md`
  - mean_topk / weighted / stacking の違い（長所短所）
  - 推論で常用しない前提でも leaderboard に載せる意義
  - “比較評価は cv_score を優先” 等の注意

- `docs/84_REHEARSAL_GUIDE.md`
  - `tools/rehearsal/` の使い方
  - local server → 社内 server の切替時に見るポイント

---

## 受け入れ基準（Acceptance Criteria）
- 開発者が docs を見れば「どの設定/どのコードを触れば良いか」が分かる
- “固定しないが、後で変えやすい” という試験段階方針が明文化されている
