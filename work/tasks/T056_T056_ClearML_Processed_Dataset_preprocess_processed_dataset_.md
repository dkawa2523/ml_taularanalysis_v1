# T056 ClearML Processed Dataset 管理を実装（preprocessでprocessed datasetを登録し、train/inferが復元して使う）

## Objective
前処理結果と前処理bundleを ClearML Dataset として登録し、学習・推論が `processed_dataset_id` で復元可能にする。split情報もdatasetに同梱して固定する。

## Risk / Redundancy check (read before coding)
- 変更は **ClearML統合の薄い層**（`src/tabular_analysis/clearml/`）へ集約し、process側に重複ロジックを散らさない。
- HyperParameters/Configuration は **最小**。全文connect禁止（UIがノイズで死ぬ）。
- local pipeline と pipeline_controller の仕様二重化を避ける（plan/step定義を共通化）。

## Context / Why
現状は前処理済みデータがDataset管理されず、再現・再利用・比較可能性が弱い。加えて、学習・推論で同じ前処理を担保できない。processed dataset を first-class にする。

## Instructions (do exactly)
1. `src/tabular_analysis/clearml/datasets.py` を新設（または既存 clearml adapter の下に追加）し、Dataset I/O を集約:
   - `create_processed_dataset(...) -> dataset_id`
   - `get_processed_dataset_local_copy(processed_dataset_id) -> local_dir`
   - 可能なら `create_raw_dataset` もここにまとめる（重複防止）
2. `preprocess` を改修:
   - `ops.processed_dataset.store_features`（default=true）を追加
   - `store_features=true` の場合は X/y を parquet 等で保存し、Dataset に同梱して登録
   - false の場合は bundle+recipe+splits+schema+meta のみ登録（大規模データ対策）
   - out.json に `processed_dataset_id` と hash群を必ず書く
3. `train_model` / `infer` を改修:
   - `data.processed_dataset_id` 指定時、Dataset.get_local_copy() で復元して学習/推論
   - train は `splits.json` を使って split を固定（再分割しない）
4. `tabular_analysis/clearml/hparams.py` を新設し、preprocess/train/infer の HyperParameters を最小で connect（docs/53に準拠）
5. docs:
   - docs/50, docs/53 を実装に合わせて更新（契約を満たすこと）
6. 例外/失敗:
   - `run.clearml.enabled=false` ならローカル保存にフォールバック可
   - enabled=true なのに Dataset 登録に失敗したら fail（doctorで検出可能に）


## Acceptance Criteria
- preprocess task 実行後、ClearML UI の Datasets に processed dataset が作成される。
- train_model / infer は `processed_dataset_id` だけで実行できる（同じ split を再利用）。
- preprocess/train/infer の HyperParameters に「必要最小の設定」が載る（docs/53準拠）。
- out.json / manifest.json の必須キーが docs/50 契約を満たす。


## Verification (run locally)
```bash
python -m compileall -q src
python tools/tests/smoke_local.py --until preprocess
# ローカルClearMLが起動している場合（loggingでdataset登録確認）
python -m tabular_analysis.cli task=preprocess run.clearml.enabled=true run.clearml.execution=logging data.dataset_path=/tmp/ta_rehearsal_data/toy_cls.csv data.target_column=target group/preprocess=stdscaler_ohe

```

## Result
- RESULT: TODO (nonce: <fill>)
