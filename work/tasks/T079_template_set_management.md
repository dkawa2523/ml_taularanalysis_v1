# T079 テンプレTask運用を template_set で安定化（増殖抑止・置換・obsolete化）

## 背景（症状）
- `template:true` のみだと、テンプレ Task が増殖した際に「どれが現行テンプレか」判別が難しくなり運用が破綻します。
- また ClearML の制約で `status=failed` の Task は script を更新できず、テンプレ更新が詰まります。

---

## 目的
- テンプレ Task を **template_set**（世代）で識別し、増殖しても運用破綻しない
- 更新できないテンプレは **新規作成で置換**し、古いテンプレは obsolete 扱いにする
- pipeline_controller が必ず “現行 template_set” を使うようにする（安全）

---

## 実装方針
### 1) config に template_set を追加
例:
- `run.clearml.template_usecase_id`（既存）: `"TabularAnalysis"`（固定でも良い）
- `run.clearml.template_set_id`: `"ta_v1"`（新設）
- `conf/clearml/templates.yaml` の tags に `template_set:{template_set_id}` を追加

> template_usecase_id は “テンプレ置き場” を固定化するためのキーなので、試験段階では固定でOK。  
> template_set_id は “運用テストの世代” として切替可能にする。

### 2) manage_clearml_templates の挙動を整理
`src/tabular_analysis/ops/manage_clearml_templates.py` を中心に、次の仕様へ:

- `--apply`:
  - まず `usecase:{template_usecase_id} AND template:true AND template_set:{template_set_id}` を検索
  - 既存があれば “更新” を試みる（ただし script 更新できないステータスは除外）
  - 更新できない（例: failed）場合は **新規作成**して置換する
- `--list`（追加推奨）:
  - 現在のテンプレ候補を process ごとに一覧表示（id/status/repo/branch/entry_point）
- `--cleanup-obsolete`（追加推奨 / 任意）:
  - 同一 process で template_set が古いもの、または更新不能で置換されたものに `obsolete:true` タグを付ける（可能なら）

> 注意: ClearML SDK のバージョン差で Task.get_tasks の引数が限定されるので、検索は tags ベースで堅牢に。

### 3) pipeline_controller は template_set を必須条件にする
- base_task_id 解決時は必ず `template_set:{template_set_id}` を含める
- これにより古いテンプレ（update3-clearml 時代など）が残っていても誤利用されない

---

## 受け入れ基準（Acceptance Criteria）
- `--apply` を複数回実行しても、テンプレが無制限に増殖しない（同じ set のテンプレが優先される）
- pipeline_controller が template_set を使って base_task_id を解決している
- `python -m compileall -q src` が通る

---

## テスト（最小）
- `python -m compileall -q src`
- `python -m tabular_analysis.ops.manage_clearml_templates --help`
- （ClearML接続できる環境）`--list` で template_set ごとに一覧が出る

---

## 実装メモ（重要）
- ClearML の制約で failed task の script は更新できない。置換（create new）が基本戦略。
- 既存の `conf/clearml/templates.yaml` に既に `template:true` があるので、そこに `template_set:` を追加するだけで効果が出る。
