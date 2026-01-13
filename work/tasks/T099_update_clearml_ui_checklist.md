# T099 docs: 55_CLEARML_UI_CHECKLIST を T097仕様に合わせて実行確認しやすく刷新（pipeline構成チェック含む）

## 背景
- 現状の `docs/55_CLEARML_UI_CHECKLIST.md` が、T097 時点の実装（pipeline v2 / ensemble / hparamsセクション / Plots/Scalars設計）とズレている、または
  テスト実行後に **どこを見れば期待通りか判断できない** 可能性がある。

## ゴール
- `docs/55_CLEARML_UI_CHECKLIST.md` を、試験段階でそのまま使える **実行→UI確認のチェックリスト** に更新する。
- pipeline 構成（Pipelinesタブ）確認を checklist に組み込み、後でテスト実行時に確認できるようにする。

## 重要な前提（このチェックリストが依存する仕様）
- tags 命名：`usecase:<usecase_id>` / `process:<process>` / `solution:tabular-analysis` / `schema:v1` / `grid:<grid_id>` など
- project 階層：`<project_root>/TabularAnalysis/<usecase_id>/<process_group>`（推奨）
- hyperparameters セクション： `inputs/ dataset/ preprocess/ model/ eval/ pipeline/ clearml`
- Local/Agent の見え方一致：
  - Agent はテンプレ clone 前提
  - commit pin（version_num）で落ちない（テンプレで pin しない）

## 作業内容
### 1) checklist の構造を “工程順” にする
推奨の大見出し：
1. **事前準備（テンプレ Task の存在確認）**
2. **dataset_register（raw dataset）**
3. **preprocess（processed dataset + 復元性）**
4. **train_model（単体モデル）**
5. **ensemble（mean_topk / weighted / stacking）**
6. **leaderboard（比較評価 + 推奨/採用の分離）**
7. **pipeline（PipelineController / 子タスク生成 / 階層化）**
8. **infer（single/batch/optimize の UI 表示）**
9. **失敗時の見方（SKIP/partial failure/optional deps）**

### 2) 各工程で “UI のどこを見るか” を固定
各工程で必ず以下の表を入れる（同じ形式で統一）：
- **探し方**：tag で絞り込み / project 階層
- **Configuration**：hyperparameters セクションごとに「最低限見えるべきキー」
- **Scalars**：最低限の主要指標（R2/MSE/RMSE/MAE 等）
- **Plots**：最低限の可視化（Plotly優先）
- **Artifacts**：保存するが “検索キーではない” もの（詳細レポート、run_summary 等）
- **Tags / User Properties**：追跡性のキー（dataset_id / preprocess_id / model_id 等）

> 注意：推論の「入力vs出力の例」は Debug Samples ではなく **Plots のテーブル**を優先（ユーザー指示）。

### 3) pipeline（Pipelinesタブ）の構成チェックを checklist に入れる
最低限の観点：
- Pipelines タブに pipeline controller が表示される
- pipeline controller のノードとして preprocess/train/ensemble/leaderboard が見える
- child task に `usecase:<usecase_id>` が付与され、階層（project）にも反映される
- partial failure 時に pipeline 自体は失敗でなく “一部失敗” として扱われ、run_summary で確認できる

### 4) 既存 docs との参照関係を整理
- checklist 内では詳細説明を重複させず、契約 docs へリンクする：
  - processed dataset: `50_CLEARML_PROCESSED_DATASET_CONTRACT.md`
  - plots/scalars: `51_CLEARML_PLOTS_SCALARS_DEBUGSAMPLES_CONTRACT.md`
  - pipeline controller: `52_CLEARML_PIPELINE_CONTROLLER_CONTRACT.md`
  - hyperparameters: `53_CLEARML_HYPERPARAMETERS_CONTRACT.md`
  - pipeline train: `60_PIPELINE_TRAIN_CONTRACT.md`
  - ensemble: `83_ENSEMBLE_POLICY.md`

### 5) 実行確認のための “Python runner” への導線
- T100 で `tools/tests/...py` を追加するので、55 の末尾に
  - `python tools/tests/rehearsal_verify_clearml_ui.py --usecase-id <id>`
  のようなコマンドを **コピペできる形**で追記する（ファイル名はT100で確定）。

## 受け入れ基準
- checklist を読むだけで、テスト実行後に ClearML UI のどこを見れば良いか迷わない。
- ensemble（3方式）と leaderboard 比較が checklist に含まれている。
- pipeline（Pipelinesタブ）の確認が checklist に含まれている。

## テスト
- なし（T100の runner で検証可能にする）
