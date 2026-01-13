# T078 pipeline 実行の Local/Agent 差を driver に閉じ込めて統一する（Local逐次 / Agentテンプレclone）

## 背景（症状 / 要求）
- Agent（PipelineController）では「テンプレ Task から clone → 子タスク生成」が必要（安定運用）
- 一方 Local 実行でも、ユーザーは 1コマンドで **前処理→複数モデル学習→leaderboard** を試せる必要がある
- ただし Local の場合は agent clone が不要なので、**テンプレは“参照（規約の源泉）”にしつつ処理はローカルで逐次実行**したい
  - ユーザー要望: 「Localの場合はテンプレを上げて、その内容の処理を同時に流す」＝テンプレ規約に沿って local でも同等の処理を流す

---

## 目的
- pipeline の実行方式を明確化し、実装重複や挙動差（Local/Agent）で破綻しない
- Local/Agent どちらでも ClearML 上の Project/Tags/Hyperparameters/Scalars/Plots/Artifacts ができるだけ一致
- pipeline は **raw_dataset_id 入力が前提**（dataset_register は pipeline に含めない）

---

## 実装方針（アーキテクチャ）
### 1) pipeline “driver” を2系統に分離
- `driver=local_sequential`（ローカル逐次実行）
- `driver=pipeline_controller`（ClearML PipelineController で子タスク生成 / agent実行）

実装としては例えば:
- `src/tabular_analysis/pipeline/driver_local.py`
- `src/tabular_analysis/pipeline/driver_controller.py`
- `src/tabular_analysis/pipeline/__init__.py` に共通I/F

> 重要: preprocess/train/leaderboard の「処理本体」は既存の process 実装（例 `processes/*.py`）を呼び、driver 側は orchestration のみに限定する。

### 2) driver の切替は Hydra 設定で
既存キー `run.clearml.execution` を活かすなら:
- `run.clearml.execution=local` → local_sequential
- `run.clearml.execution=pipeline_controller` → controller

または `pipeline.driver` を新設してもよいが、既存 CLI と整合させること。

---

## 変更内容（仕様）
### A) pipeline の入力は dataset_id（raw）を必須
- `data.raw_dataset_id` が空ならエラー（pipeline内で dataset_register しない）
- これに合わせて docs / rehearsal runner も更新する（dataset_register は pipeline の前に実行）

### B) Agent（pipeline_controller）ではテンプレ clone を必須
- controller driver は `base_task_id`（テンプレ）が解決できない場合は開始前に失敗させる（中途半端に実行しない）
- `base_task_id` 解決は `process:<name> + template:true + template_set:<id>`（T079で整備）で行う

### C) Local（local_sequential）はテンプレ規約に沿って逐次実行
- Local pipeline 実行時:
  1. （任意/推奨）`ensure_templates()` を呼び、テンプレが無ければ作成（T079と連携）
  2. `pipeline.grid.preprocess_variants` をループして preprocess を逐次実行
  3. 各 preprocess 結果（processed_dataset_id）ごとに `pipeline.grid.model_variants` をループして train を逐次実行
  4. 最後に leaderboard を実行（同じ usecase/grid を対象に集計）
  5. （T083〜で）ensemble が有効なら preprocess単位で ensemble train も実行

> Localでも ClearML enabled の場合は、各工程が **別 Task として記録**されるようにする（pipeline task 1つに集約しない）。

### D) タスク名 / タグ / Project階層を統一
- train タスク名には **モデル名（略称）**を入れる
- preprocess タスク名には **preprocess_variant** を入れる
- tags に最低限を入れる:
  - `usecase:<usecase_id>`
  - `process:<process_name>`
  - `preprocess:<variant>`（該当タスク）
  - `model:<variant>`（train/ensemble）
  - `grid:<grid_id>`（pipeline全体識別）
- Project階層は T080 の `project_layout` を必ず利用（直書き禁止）

---

## 受け入れ基準（Acceptance Criteria）
- Local 実行:
  - `run.clearml.execution=local` で pipeline を起動すると、ClearML に **preprocess/train/leaderboard が別 Task として作成**される
- Agent 実行:
  - `run.clearml.execution=pipeline_controller` で pipeline を起動すると、ClearML 上で **pipeline controller + 子タスク**が生成される
- どちらも `usecase:<id>` タグで揃って検索でき、Project階層が同じ規約になる

---

## テスト（最小）
- `python -m compileall -q src`
- ローカルで実行できる環境では:
  - dataset_register → pipeline(local) → tasks が増える
  - dataset_register → pipeline(controller) → 子タスクが増える（agentが動いている前提）

---

## 実装ヒント（重要）
- driver_local は “関数呼び出し” で逐次実行し、task間連携は `out.json`（manifest）で明示
- driver_controller は “テンプレclone” なので、Hydra override の作り方を統一（T075で list 正規化済みのはず）
- Local/Agent の差分は driver に閉じ込め、process 本体に if 分岐を増やさない
- Local logging の CLI 子プロセスは `CLEARML_TASK_ID` 等を env から除去し、pipeline Task の再利用を防ぐ（親は `run.clearml.parent_task_id` で紐付け）
