# T077 ClearML Agent/Pipeline 失敗の主因（commit pin / version_num）を根治する

## 背景（症状）
- `run.clearml.execution=pipeline_controller` で pipeline を起動すると、ClearML Task Script に **version_num（commit）が pin** されます。
- ClearML Agent は `version_num` を checkout しようとしますが、ローカル未push / shallow clone / 参照不能等で
  `fatal: unable to read tree <commit>` になり pipeline が **子タスクを作る前に failed** になります。

このタスクでは、**Agent/Pipeline のデフォルトを「branch pin（commit pin しない）」**にして、環境差・Gitアカウント差・push漏れ差があっても試験段階の実行を止めないようにします。

---

## 目的
- Agent 実行で `version_num` pin に起因する clone failure を防ぐ（最優先）
- Local/Agent の挙動差を最小化（script生成規約を統一）
- 将来、厳密再現が必要になったら `commit` pin に切替できる（試験段階では branch pin を既定）

---

## 実装方針
### 1) Hydra 設定を追加（既定は branch）
`conf/run/base.yaml` または `conf/run/clearml.yaml` 等の適切な場所へ追加:

- `run.clearml.code_ref.mode`: `"branch"` | `"commit"` | `"none"`
  - `"branch"`: repository/branch は設定するが **version_num を空**にする（既定）
  - `"commit"`: repository/branch + commit pin（version_num）を設定（厳密再現用）
  - `"none"`: repository/branch/version_num を設定しない（Localのみ用途。Agentは禁止）
- `run.clearml.code_ref.repository`: `"auto"` または URL
- `run.clearml.code_ref.branch`: `"auto"` または ブランチ名
- `run.clearml.code_ref.commit`: `"auto"` または commit hash（commit mode 時）

> 注: 既存に `run.clearml.code_repository` / `run.clearml.code_branch` がある場合は統合し、古いキーは後方互換の alias にしてください。

---

## 変更内容（実装）
### A) Script dict 生成を 1箇所に集約する
`src/tabular_analysis/platform_adapter.py`（または既存の clearml script 生成関数）に、以下を満たす **純粋関数**を追加:

- `build_clearml_code_ref(cfg, repo_root: Path) -> dict`
  - `{"repository": ..., "branch": ..., "version_num": ...}` を返す
  - `mode=branch` の場合、**version_num は必ず空文字**（または None）で pin しない
  - `mode=commit` の場合、commit hash を version_num に入れる（"auto" の場合は git から検出）
  - `mode=none` の場合、空dict（agentは禁止）

> 重要: ClearML SDK のバージョン差があるので、Task.set_script の signature に合わせて `version_num` / `commit` / `version` のどれを渡すかは既存実装に追従しつつ、「branch mode は pin を消す」ことを最優先で実現する。

### B) Task.set_script を呼ぶ全箇所でこの関数を使う
以下を必ず統一:
- pipeline task
- template task 作成（`ops/manage_clearml_templates.py`）
- train/preprocess など単体タスクの ClearML 初期化

実装例（概念）:
- `script_kwargs = build_clearml_code_ref(cfg, repo_root)`
- `task.set_script(repository=..., branch=..., version_num="")`（branch mode）
- ClearML SDK の制約で `""` が無理なら `None` にし、**pin が残らない**方を採用。

### C) Doctor（または検証コマンド）に事前チェックを追加（任意だが推奨）
- `run.clearml.execution=pipeline_controller` なのに `mode=none` の場合は即エラー
- `mode=commit` の場合は「その commit が remote で取れる」ことを **警告** or **強制チェック**（試験段階は警告でよい）

---

## 受け入れ基準（Acceptance Criteria）
- `mode=branch` のとき、pipeline task / template task の script に **commit pin が残らない**
  - `Task.get_script()` の `version_num` が空/None になっている、または Agent が checkout を試みない
- `python -m compileall -q src` が通る
- （可能なら）ローカルで ClearML 接続して `clearml-agent execute --id <pipeline_task>` が clone failure しない

---

## テスト（ClearML無しでもOK）
- `python -m compileall -q src`
- 単体テスト（推奨）:
  - `build_clearml_code_ref(mode=branch)` が `version_num` を空にすることを検証する（pytest が無ければ簡易スクリプトでも可）

---

## 補足（調査ヒント）
- 既に `platform_adapter.py` に `set_script` 周りの処理がある（grep で確認済み）
- `manage_clearml_templates.py` も repository/branch を扱っているので、テンプレ側も必ず同じ規約に統一する
- `docs/70_CHATGPT_HANDOFF.md` に追加改良がある前提なので、既存の fix を壊さない（最小差分）
