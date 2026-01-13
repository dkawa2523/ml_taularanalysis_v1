# T096 Python rehearsal runner: Local/Agent の再現検証を 1コマンド化し、自動チェックで固定する（jq不要）

## 背景
- これまで bash + jq 依存で検証が詰まりやすかった。
- また Local/Agent の “見え方一致” を人手で確認すると漏れやすい。
- そこで Python runner を正とし、**試験段階でのリハーサル手順を再現可能に固定**する。

## ゴール
1. `tools/rehearsal/run_pipeline_v2.py`（など）の Python runner を追加し、以下を1コマンドで実行できる：
   - toyデータ生成（既存があれば利用）
   - dataset_register（※pipelineには含めない方針）
   - pipeline 実行（LocalDriver / AgentDriver を選択可能）
   - 実行後の ClearML 内容確認（タグ検索→タスク一覧→基本検証）
2. runner は jq を使わない（Pythonだけ）。
3. 自動チェック項目（最低限）：
   - usecase タグで pipeline / preprocess / train / ensemble / leaderboard が存在する
   - project 階層が規約に沿う（完全一致でなくても prefix/含有でOK）
   - Hyperparameters がカテゴリ分割されている（General一括ではない）
   - Scalars / Plots が最低限存在（空ではない）
   - processed dataset が存在し、復元情報が含まれる（存在チェック＋keyの検査）
   - run_summary.json が pipeline に紐づいて存在する
4. 失敗時は “何が足りないか” を分かりやすく出力する。

## 非ゴール
- 全モデル・全前処理のフルスイート（まずは最小のスモーク）。
- ClearML サーバのセットアップ自動化（環境は既存前提）。

## 作業手順
### 1) 既存の rehearsal/smoke スクリプトの有無を確認
- `tools/tests` や `tools/rehearsal` があるなら、そこへ統合する（新規乱立を避ける）。
- 既存が bash の場合は python へ寄せる（bashは残してもよいが、正はpythonに）。

### 2) runner の CLI 設計（最小）
例：
- `--execution local|agent`
- `--task-type regression|classification`
- `--models ridge,random_forest`（省略時は小さめdefault）
- `--preprocess stdscaler_ohe,robust_ohe`（省略時は小さめdefault）
- `--usecase-id <auto>`（省略時は test_<dataset>_<timestamp>）
- `--project-root LOCAL` など
  - runner が `pipeline.preprocess_variants` / `pipeline.model_variants` を上書きする場合、conf 側で null 定義し Hydra strict を回避（grid.* にフォールバック）

### 3) ClearML API での検証
- `Task.get_tasks(tags=[f"usecase:{usecase}"])` で取得し、
  - 必須プロセスが存在するか
  - 期待するタグが付いているか（process:* / schema:*）
  を確認する。
- Hyperparameters のカテゴリは、ClearML SDK の取得方法に合わせる（SDKバージョン差に注意）。

### 4) 出力の利便性
- runner は最後に
  - usecase_id
  - pipeline_task_id
  - dataset_id
  - UIでの検索方法（タグ）
  を必ず表示する。

### 5) docs 追記
- “試験段階のリハーサル手順（Local→社内サーバへ移行）”
- runner の実行例（copy&paste可能）
- 失敗した時に見るべき箇所（run_summary, skip_reason, template_set）

## 受け入れ基準
- runner を実行すると、dataset_register + pipeline 実行 + 自動検証が一通り動く。
- jq が無くても結果確認できる（out.json 参照もPythonで完結）。
- 失敗した場合に原因が推測できるメッセージが出る。

## テスト
- `python -m compileall -q src tools`
- runner の `--help` が表示できる
- local 実行で最小ケース（1 preprocess + 2 models）を完走できる（ClearML on/off どちらでも）
