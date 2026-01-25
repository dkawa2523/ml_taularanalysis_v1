# T063 ClearML PipelineController を「PIPELINESタブに表示される」実装に寄せる

## 目的
train pipeline を ClearML PipelineController で実行した際、ClearML UI 左タブの PIPELINES に表示され、子タスク（preprocess/train/leaderboard）の関係が追えるようにする。

## 背景 / なぜ必要か
現状 pipeline を実行しても pipeline controller として認識されず、タスク構造が理解しづらい。運用・比較・監査のために PIPELINES 表示が重要。

## スコープ（やること / やらないこと）
- やる: PipelineControllerの start 方法/TaskType/project 設定を見直す
- やる: docs/63 を実装と一致させる
- やらない: ClearMLサーバ設定の固定（試験段階なのでコード側は柔軟に）

## 実装手順（Codexはこの順で実施）
1. `src/tabular_analysis/processes/pipeline.py` の ClearML pipeline_controller 実装を確認し、以下を満たすよう調整:
   - controller task が ClearML 上で controller/pipeline として扱われる形で生成される
   - `run.clearml.execution=pipeline_controller` の場合、ステップタスクは queue に投入される
   - controller 自身は project を `.../99_pipeline` 系に統一（configで変更可能）
2. `start_locally` と `start` の使い分けを整理:
   - 試験段階の基本: agentありなら `start(queue=...)` を優先
   - ローカルデバッグ用: `start_locally` を別execution名（例: pipeline_controller_local）で提供
3. T058/T059 の template 探索仕様（tags）と整合させる（テンプレが見つからないときのエラーを明確化）。
4. docs/63 を更新。


## 受け入れ条件（Acceptance Criteria）
- pipeline_controller 実行で ClearML UI の PIPELINES に表示される。
- preprocess/train/leaderboard が子タスクとして生成され、依存関係がUIで追える。
- template未作成時は明確なエラーを出す（手順案内）。

## 検証コマンド（ローカル）
```bash
python -m compileall -q src
# 実環境では agent 起動が必要:
# clearml-agent daemon --foreground --queue default --create-queue
# python -m tabular_analysis.cli task=pipeline/train_regression run.clearml.enabled=true run.clearml.execution=pipeline_controller run.clearml.queue_name=default data.raw_dataset_id=<RAW_ID>

```

## 注意 / 設計ガードレール（冗長化・破綻防止）
- ClearML 連携のAPI呼び出しは可能な限り `src/tabular_analysis/clearml/` に集約する（process側に散らさない）。
- 可視化は `src/tabular_analysis/viz/` に集約し、各processは「何を可視化するか」だけ宣言する。
- HyperParameters は “全文” を入れない。**最小キー**をカテゴリ別に接続する（docs/61参照）。
- タスク名/タグ/Properties の付与ルールは docs/66 を単一の正とし、コード内にルールを散在させない。
- pipeline は「データ登録が前提」ではなく「dataset_id入力が前提」。dataset_register は独立運用（docs/60参照）。

