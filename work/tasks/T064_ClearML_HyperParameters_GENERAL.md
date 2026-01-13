# T064 ClearML HyperParameters をセクション分割して見やすくする（GENERAL一択を解消）

## 目的
dataset_register/preprocess/train/leaderboard/infer の HyperParameters を `Inputs/Dataset/Preprocess/Model/Eval/Optimize/Execution/Links` に分けて表示できるようにする。

## 背景 / なぜ必要か
GENERAL に全て集約されるとユーザーが設定を理解できず、再実行/比較も困難。情報量を増やしすぎず、最小キーをカテゴリ別に出す必要がある。

## スコープ（やること / やらないこと）
- やる: `src/tabular_analysis/clearml/hparams.py` を新設/改善し、カテゴリ別connectを提供
- やる: 各processが `hparams.connect_*` を呼ぶ
- やらない: 全configをHyperParametersに流し込む（禁止）

## 実装手順（Codexはこの順で実施）
1. `src/tabular_analysis/clearml/hparams.py` を作成/改善:
   - `connect_dataset_register(task, cfg, extra={})`
   - `connect_preprocess(...)`
   - `connect_train_model(...)`
   - `connect_leaderboard(...)`
   - `connect_infer(...)`
   それぞれが `Task.connect(dict, name="Inputs")` 等でセクションを作る。
2. 既存のclearml init/task context 生成箇所を調査し、task作成直後にカテゴリ別connectを呼ぶ（二重connect回避）。
3. docs/61 を更新し、必須キーとセクションを確定する。


## 受け入れ条件（Acceptance Criteria）
- ClearML UIで HyperParameters に複数セクションが表示される（Inputs, Modelなど）。
- GENERALのみに全情報が集中しない。
- 主要パラメータが欠落せず、かつノイズが増えない（最小キー）。

## 検証コマンド（ローカル）
```bash
python -m compileall -q src
python -m tabular_analysis.cli task=train_model run.clearml.enabled=false --help 2>/dev/null || true

```

## 注意 / 設計ガードレール（冗長化・破綻防止）
- ClearML 連携のAPI呼び出しは可能な限り `src/tabular_analysis/clearml/` に集約する（process側に散らさない）。
- 可視化は `src/tabular_analysis/viz/` に集約し、各processは「何を可視化するか」だけ宣言する。
- HyperParameters は “全文” を入れない。**最小キー**をカテゴリ別に接続する（docs/61参照）。
- タスク名/タグ/Properties の付与ルールは docs/66 を単一の正とし、コード内にルールを散在させない。
- pipeline は「データ登録が前提」ではなく「dataset_id入力が前提」。dataset_register は独立運用（docs/60参照）。

