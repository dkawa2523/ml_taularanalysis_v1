# ClearML HyperParameters 分類（セクション） 契約 v2

## ゴール
ClearML UI の Configuration > Hyperparameters が **GENERAL一択**にならないよう、セクションを分ける。

## 方針
- `Task.connect(params_dict, name="<Section>")` を使用してセクションを作る。
- 全設定を入れない（ノイズ回避）。再実行・比較に必要な最小キーのみ。
- セクションと dotpath は `conf/clearml/hyperparams_sections.yaml`（`run.clearml.hyperparams.sections`）で定義する。
- `a.b` は scalar を拾い、`a.*` は a 配下の dict を拾う（無ければ skip）。
- 具体的な抽出は `src/tabular_analysis/clearml/hparams.py` に集約し、接続は `platform_adapter.init_task_context` で行う。
- 値が空のセクションは表示しない（キーがある時のみ connect）。

## セクション（使用名・既定）
- `inputs`
- `dataset`
- `preprocess`
- `model`
- `eval`
- `pipeline`
- `clearml`

## 既定の抽出例（conf/clearml/hyperparams_sections.yaml）
- inputs: `run.usecase_id`, `run.output_dir`, `data.dataset_path`, `infer.mode` など
- dataset: `data.raw_dataset_id`, `data.processed_dataset_id`
- preprocess: `preprocess.*`, `data.split.*`, `ops.processed_dataset.*`
- model: `train.model`, `train.params`, `model_variant.*`
- eval: `eval.*`, `leaderboard.*`
- pipeline: `pipeline.*`
- clearml: `run.clearml.enabled`, `run.clearml.execution`, `run.clearml.code_ref.*` など

## 運用
- 表示対象の調整は `conf/clearml/hyperparams_sections.yaml` の編集のみで行う。
- 新しい設定項目を追加する場合も同様に dotpath を追記する。
