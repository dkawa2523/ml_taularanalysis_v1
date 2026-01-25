# T076 テンプレTask/Docsを整備（repository/entry_point/運用トラブルシュート）

## 背景
pipeline controller だけ直っても、子タスクが template から作られる場合、
template task の Script が platform repo / 旧entrypoint のままだと同様に失敗します。

また、試験段階では “あとから運用ルールを変えやすい” ことが重要なので、
トラブルシュートとチェック手順を docs に明記します。

---

## 目的
- template task も solution repo / clearml_entrypoint を指す
- ClearML 側で問題が起きたときの切り分けが docs で再現できる

---

## 変更内容
### 1) manage_clearml_templates の既定を更新
`src/tabular_analysis/ops/manage_clearml_templates.py` に以下を反映:

- `--repo/--branch` 未指定のとき:
  - T073 の git検出を使って solution repo/branch を使う
- template の entry_point は `tools/clearml_entrypoint.py` を使う
- validate の repository mismatch 判定も更新（platform で固定しない）

### 2) docs 追加
`docs/68_CLEARML_AGENT_TROUBLESHOOTING.md` を追加し、最低限以下を記載:

- “子タスクが作られない” ときに見るべき順序
  1) pipeline task の Script repository/branch/entry_point
  2) Queues/Agent
  3) Agent log の ModuleNotFoundError
- `Task.get_script()` の確認コマンド例
- list override が壊れるパターンと回避策（T075の内容）

### 3) rehearsal コマンド例を修正
既存の rehearsal docs（例: `docs/67_REHEARSAL_COMMANDS.md`）がある場合、
`pipeline.grid.model_variants` を JSON ではなく Hydra list 形式で書くように修正する。

---

## 受け入れ基準
- `manage_clearml_templates --validate` で repository/entry_point の mismatch が出ない（少なくとも新規作成したテンプレでは）
- docs が追加されている
- `python -m compileall -q src` が通る
