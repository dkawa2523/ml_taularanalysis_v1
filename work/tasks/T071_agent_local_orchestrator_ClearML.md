# T071 ローカル一括実行（agent不要）: local_orchestrator を追加し、ClearMLタスクは個別に生成する

## 目的
ユーザー目線では1コマンドで一括実行したいが、ClearML上では dataset_register/preprocess/train×N/leaderboard が個別タスクとして残るように、ローカル orchestrator を追加する。

## 背景 / なぜ必要か
pipeline_controller は agent が必要で、ローカル試験時に手順が重い。試験段階では『ローカル資源で一括』が重要。

## スコープ（やること / やらないこと）
- やる: `src/tabular_analysis/ops/local_orchestrator.py` を追加
- やる: subprocessでCLIを叩き、各工程が独立taskとしてClearMLに残る
- やる: out.json を確実に取得し、次工程へ引き継ぐ（失敗を明確化）
- やらない: ml-platform の改修

## 実装手順（Codexはこの順で実施）
1. `src/tabular_analysis/ops/local_orchestrator.py` を追加:
   - サブコマンド: `train_regression`
   - 引数: dataset_path/target_column OR raw_dataset_id, preprocess_variant, model_set, clearml on/off, project_root, output_root
2. 実装は subprocess 呼び出しで CLI (`python -m tabular_analysis.cli ...`) を順に実行し、各工程の `out.json` を読み取ってIDを引き継ぐ。
   - dataset_register → raw_dataset_id
   - preprocess → processed_dataset_id
   - train_model×N → train_task_id 列挙
   - leaderboard → recommended_model_id
3. out.json の場所は「run.output_dir配下を探索」方式にして堅牢化（zsh貼り付け事故対策）。
4. docs/67 にコマンド例を追加。


## 受け入れ条件（Acceptance Criteria）
- `python -m tabular_analysis.ops.local_orchestrator train_regression ...` で一括実行できる。
- ClearMLに各工程が別taskとして作成される（logging実行でOK）。
- 失敗時にどの工程で落ちたか分かるログ/例外になる。

## 検証コマンド（ローカル）
```bash
python -m compileall -q src
python -m tabular_analysis.ops.local_orchestrator --help

```

## 注意 / 設計ガードレール（冗長化・破綻防止）
- ClearML 連携のAPI呼び出しは可能な限り `src/tabular_analysis/clearml/` に集約する（process側に散らさない）。
- 可視化は `src/tabular_analysis/viz/` に集約し、各processは「何を可視化するか」だけ宣言する。
- HyperParameters は “全文” を入れない。**最小キー**をカテゴリ別に接続する（docs/61参照）。
- タスク名/タグ/Properties の付与ルールは docs/66 を単一の正とし、コード内にルールを散在させない。
- pipeline は「データ登録が前提」ではなく「dataset_id入力が前提」。dataset_register は独立運用（docs/60参照）。

