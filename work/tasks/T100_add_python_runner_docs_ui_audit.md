# T100 tools+docs: rehearsal後にClearML UI構造を自動検証する Python runner 追加（jq不要）

## 背景
- docs の整合性は人間レビューだけだと崩れやすい。
- 試験段階で “Local/Agent 見え方一致” や “pipeline の子タスク生成” を固定したい。
- jq が使えない環境があるため、**Python runner を正**として検証できるようにする。

## ゴール
1. `tools/tests/` 配下に、ClearML 上のタスク構造を検証する Python runner を追加する。
2. 55 checklist（T099）から **そのままコピペ**できる形で実行例を docs に追記する。

## 要件
- jq 不要
- usecase_id を指定して、以下を最低限チェックできる：
  - pipeline controller タスクの存在（`process:pipeline` / `usecase:<id>`）
  - pipeline の child task が生成されている（preprocess/train/ensemble/leaderboard）
  - 各 task の repository/branch が期待通りで、**commit pin（version_num）が空**である（pinされていたら警告）
  - hyperparameters が “General一括” ではなく、推奨のカテゴリ（inputs/dataset/...）に分かれている（少なくともキー名から判定）

> Plots/Scalars の “中身の正しさ” まで完全自動化するのは難しいため、
> runner では **構造・存在・ピン留め・セクション分割** に絞る。
> 内容（グラフの形など）は 55 checklist の目視で担保する。

## 仕様（runner）
- ファイル名：`tools/tests/rehearsal_verify_clearml_ui.py`（変更してもよいが docs と合わせる）
- 引数：
  - `--usecase-id`（必須）
  - `--project-root`（任意：絞り込みの補助）
  - `--require-pipeline`（既定 True）
  - `--json`（任意：機械可読出力）
- 出力：
  - 見つかった task を process ごとに列挙（status/id/project/name）
  - repository/branch/version_num を表示
  - warnings を最後にまとめる
- 終了コード：
  - OK: 0
  - NG（重大）：pipeline 不在 / train不在 など → 1

## 実装手順
1. `clearml` SDK を使い、`Task.get_tasks(tags=[...])` で usecase を絞り込む。
2. tags から `process:*` を抽出し、工程別にグルーピングする。
3. `Task.get_script()` / `task.data.script.version_num` を参照して pin を検出する。
   - `version_num` が None か空文字なら OK
   - 値があれば WARNING
4. hyperparameters のセクション判定：
   - `task.get_parameters()` のキー（例：`inputs.xxx`）を見てカテゴリが含まれるかを確認。
5. docs 追記：
   - `docs/55_CLEARML_UI_CHECKLIST.md` の末尾に runner 実行例（コピペ）を入れる。
   - もし rehearsal guide がある場合（`docs/67_...` / `docs/84_...`）、そちらにも短く導線を入れる。

## 受け入れ基準
- `python tools/tests/rehearsal_verify_clearml_ui.py --usecase-id <id>` がローカル環境で実行でき、
  タスク構造の一覧と警告が出る。
- docs に実行コマンドが追記されている。

## テスト
- `python -m compileall -q tools`（最低限）
