# T023 データ品質: data_quality.json/md + ターゲットリーク検知（warn/fail を設定可能に）

## Objective
- 業務投入前提で最低限必要な「データ品質チェック」を自動で出力し、分析の手戻りを減らす
- ターゲットリーク（リーク疑い）を早期に検知し、誤った高スコアモデルの混入を減らす
- 出力は ClearML UI でも見える形（artifact / report へ組み込み）にする

---

## Scope
1) データ品質計算モジュールを追加
- `src/tabular_analysis/quality/data_quality.py` を追加
- 入力: `pandas.DataFrame`, `target_column`, `task_type`, `id_columns`（任意）
- 出力: `dict`（json化可能） + `markdown`（summary用）

2) dataset_register / preprocess に組み込み
- dataset_register 出力に以下を追加
  - `data_quality.json`（必須）
  - `data_quality.md`（必須）
  - `out.json` に `data_quality_summary`（軽量: row/col/missing/duplicates/leak flags）
- preprocess では、前処理後の品質（欠損率の変化、除外された列数 等）を `quality_after_preprocess.json` として出力（必須）

3) チェック項目（最小セット）
- 行数/列数、dtype 分布
- 欠損率（列ごと上位N）
- 重複行数（完全一致）
- 定数列（ユニーク数=1）
- 高カーディナリティ列（例: ユニーク率 > 0.8 など）
- ターゲットリーク（疑い）
  - target と完全一致する列があれば **error**
  - 回帰: 相関（Pearson）上位の列名/係数を記録（閾値超えは warning）
  - 分類: target と一致/ほぼ一致、または単一特徴で高精度を出しそうな列を簡易検知（例: target と 1-1 対応のカテゴリ）

4) 失敗/警告制御（config）
- `conf/data/base.yaml` に以下を追加
  - `data.quality.enabled: true`（推奨）
  - `data.quality.fail_on_duplicates: false`（デフォルトは warn）
  - `data.quality.fail_on_leak: true`（完全一致は必ず fail）
  - `data.quality.max_rows_scan: 50000`（大規模はサンプル）

5) report への反映
- `pipeline` の report.md に、品質サマリ（欠損上位、重複、リーク警告）を 1 セクションで出す

6) テスト追加
- `tools/tests/smoke_data_quality.py`
  - 小さな合成データを作る（欠損 + 重複 + leak列を含む）
  - dataset_register を実行
  - `01_dataset_register/data_quality.json` と `data_quality.md` が存在し、内容に `duplicates_count` と `leak_suspects` が含まれること

---

## Implementation Notes
- リーク検知は "正確" より "早期警告" を優先。重い統計はやらない
- 大規模データでは先頭N行のサンプルでOK（ただしサンプル数は記録）
- `data_quality.json` は将来的な監視（drift）にも使う前提で、キー名は安定させる

---

## Acceptance Criteria
- dataset_register が `data_quality.json` / `data_quality.md` を必ず出力する
- preprocess が `quality_after_preprocess.json` を出力する
- `smoke_data_quality.py` が通る

---

## Verification（runner 側で実行）
- `python tools/tests/smoke_data_quality.py`
