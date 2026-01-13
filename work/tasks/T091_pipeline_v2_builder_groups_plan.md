# T091 Pipeline v2: groups.mode + custom(base/include/exclude) を解釈し、Preprocess×Model を同一階層で展開する Plan Builder を実装

## 背景
- T089 で pipeline v2 スキーマを追加し、T090 で registry を導入した。
- 本タスクでは pipeline を “v2 解釈” で計画（plan）生成できるようにする。
- 特に重要：
  - preprocess は **複数variant** を開発者が設定しやすい（include/exclude）形で扱う
  - pipeline 上では preprocess variant たちは同じ階層（兄弟ステップ）として実行される
  - 各 preprocess の成果（processed dataset）を参照して複数モデル学習タスクを展開する

## ゴール
1. `pipeline.profile=custom` の時、`pipeline.groups.<group>.mode` を v2 として解釈し、実行計画（plan）を生成できる。
2. preprocess/train/ensemble/leaderboard を “処理グループ” として plan に並べる（同一階層のステップとして展開）。
3. preprocess は複数variantに対応し、各 variant から processed dataset を生成し、train がそれぞれを参照する依存関係を plan に持つ。
4. 後方互換：`pipeline.profile=default`（または v2 未指定）の場合は、現行の grid 動作（`pipeline.grid.*`）を維持するか、**defaultに限り v2=default 解釈に寄せてもよい**（ただし互換を壊さないこと）。

## 非ゴール
- ClearML 上での skip 表現統一（T092）。
- fail_policy の確定（T093）。
- Local/Agent driver 統一（T095）。

## 実装方針（ファイル増を抑える）
- 既存の pipeline 実装ファイル（例: `src/tabular_analysis/pipeline/*` や `src/tabular_analysis/cli.py` の pipeline 部）をまず確認し、そこへ最小限の構造追加で実装する。
- 新規で “plan” を表す dataclass を作る場合も、ファイルは増やしすぎない（既存 pipeline モジュール内に同居させる）。

## 作業手順
### 1) 現行 pipeline の “展開ロジック” を確認
- どこで `pipeline.grid.preprocess_variants` と `pipeline.grid.model_variants` を読んでいるか特定。
- どこで ClearML PipelineController を呼んでいるか（または local 実行しているか）確認。
- 可能なら「計画生成」と「実行（driver）」が混在している箇所を把握し、T095 で分離できる形を意識する。

### 2) v2 の解釈（profile + group mode）
- `pipeline.profile` が `custom` の場合のみ v2 解釈を有効にする（既存挙動を壊しにくい）。
- group mode の解釈：
  - `none`：そのグループは plan に入れない
  - `default`：registry の default_enabled 候補を採用
  - `custom`：`custom.base` を起点に `include/exclude` で差分適用
    - base=default → default候補から差分
    - base=none → 空から include で追加

### 3) preprocess × model の plan 展開
- preprocess variants の決定：
  - v2: `pipeline.groups.preprocess.*`
  - 互換: `pipeline.grid.preprocess_variants`（default profile の時）
- 各 preprocess variant につき、plan 上に `preprocess/<variant_id>` を 1つ作る
- train variants の決定：
  - v2: `pipeline.groups.train.*` + registry default
  - 互換: `pipeline.grid.model_variants`
- train の展開：
  - 各 preprocess variant で生成される processed_dataset_id を入力に、
  - 各 model_variant の train task を plan 上に作る（`train/<preprocess>/<model>`）
- 依存関係：
  - train は対応する preprocess を depends_on として持つ（processed dataset を参照するため）

### 4) ClearML project 階層の “計画上のルール” を固定
- 既存方針：`<root>/TabularAnalysis/<usecase_id>/<process_group>`
- 複数タスクがぶら下がる場合の自動階層化：
  - Train: `<root>/TabularAnalysis/<usecase_id>/Train_models/<preprocess_variant>`
  - Preprocess: `<root>/TabularAnalysis/<usecase_id>/Preprocess`
  - Ensemble: `<root>/TabularAnalysis/<usecase_id>/Ensemble`
  - Leaderboard: `<root>/TabularAnalysis/<usecase_id>/Leaderboard`
  - Pipeline controller: `<root>/TabularAnalysis/<usecase_id>/Pipeline`
- ただし階層文字列は開発者が変更しやすいように、1箇所の関数/設定で生成する（散在させない）。

### 5) plan の出力（後続で使う）
- plan を python dict / json へシリアライズできるようにする（後続で dry-run と run_summary に使う）。
- 例: `plan.json` として artifact 化できる形。

### 6) docs/ に設計の要点を追記
- 「v2 は profile=custom で有効」「groups.mode」「custom.base/include/exclude」の動き
- 「preprocess は複数variantを同一階層で実行し、train が依存する」

## 受け入れ基準
- `pipeline.profile=custom` かつ `groups.preprocess.mode=custom` で、複数 preprocess variant を plan に載せられる。
- `groups.train.mode=default` で、複数モデルの train plan を生成できる。
- train plan が preprocess plan に依存し、processed dataset を参照する設計になっている（依存関係が表現できている）。

## テスト
- `python -m compileall -q src`
- 既存の pipeline 起動コマンドで、少なくとも plan 生成まで到達すること（実行はT095で安定化）。
- （あれば）`python -m tabular_analysis.ops.print_clearml_identity ...` などで pipeline identity が取れること
