# T090 Pipeline v2: Variant/Step Registry を導入（default_enabled / requires / applicability）し、拡張点を固定する

## 背景
- 将来、前処理・次元削減・特徴量化・モデル・アンサンブル等が増えると、`conf` 側の “セット管理” が運用コストになりやすい。
- そこで「default の中身はコード側で決める（registry）」を正にし、
  - 開発者は variant/step を追加するとき **registryに1エントリ追加**すればよい
  - pipeline 設定は `mode=default/custom` と `base=default + include/exclude` の差分指定だけで済む
  という構造にする。

## ゴール
1. preprocess/model/ensemble の **variant registry** を導入する（最小の新規コード/ファイルで）。
2. 各 variant が以下のメタ情報を持つようにする：
   - `id`
   - `group`（preprocess/train/ensemble など）
   - `default_enabled`（defaultに含めるか）
   - `supports`（regression/classification/multiclass など）
   - `requires`（optional deps。例: ["xgboost"]）
   - `applicability_check(schema) -> ok/skip(reason)`（前処理向け。モデルは基本okで良い）
3. registry を利用して「default候補一覧」が取得できる関数APIを提供する（後続の pipeline v2 builder が使う）。

## 非ゴール
- pipeline の v2 解釈（T091で実施）。
- skip の ClearML 表現統一（T092で実施）。

## 実装方針（ファイル増を抑える）
- まず既存コードで「モデル一覧」「前処理variant一覧」「ensemble method一覧」がどこに定義されているかを探す。
  - 例: `src/tabular_analysis/models/*`, `conf/model/*`, `conf/preprocess/*`, `src/tabular_analysis/ensemble/*` など
- 既存のまとまりがあるなら、そこに registry を同居させる（新規ディレクトリを増やさない）。
- どうしても置き場がない場合だけ、`src/tabular_analysis/registry.py` の単一ファイルで開始する（増殖を避ける）。

## 作業手順
### 1) 現状把握（必須）
- 現行で利用されている model_variant / preprocess_variant / ensemble method の “ID文字列” のソースを特定する。
- 可能なら「現在 pipeline.grid に入れているID一覧」と一致させる（後方互換のため）。

### 2) Registry データ構造を定義
- dataclass などでよい。最低限：
  - `VariantSpec(id, kind, default_enabled, supports, requires, applicability_checker)`
- supports は過剰に複雑にしない。まずは `task_type in {"regression","classification"}` のレベルで十分。

### 3) optional deps の判定関数（後続でskipに使う）
- `requires=["xgboost"]` のような指定を受け取り、
  - import 可能かどうかを判定する関数を用意する（例: `importlib.util.find_spec`）。
- “importできない=skip候補” を返せるようにする。

### 4) preprocess applicability_check の最小実装
- preprocess はデータ依存で「意味がない/適用不能」があり得るため、最低限のチェックを入れる：
  - 例: OHE が必要なカテゴリ列が存在しない → skip
  - 例: 数値列が存在しないのに scaler を指定 → skip
- 現行の「データスキーマ表現」がどこにあるか確認し、それに合わせる。
  - 既に `schema` や `data_profile` のようなものがあるならそれを利用。
  - 無い場合は、最小の schema 要約（数値列/カテゴリ列の有無など）を作る関数を 1つ用意して、registry判定に渡す。

### 5) Registry API を用意（後続で使う）
例：
- `list_preprocess_variants(task_type, schema) -> List[VariantSpec]`
- `list_model_variants(task_type) -> List[VariantSpec]`
- `list_ensemble_methods(task_type) -> List[VariantSpec]`
- `get_default_*` も同様

※後続の T091 で `mode=default` の時にこの API を使う。

### 6) docs 追記（開発者向け拡張点）
- 「新しい前処理/モデルを追加する時は registry のこの場所を編集する」を明記。
- ここは運用影響が大きいので、レビューしやすいように **ID命名規約**や `default_enabled` の判断基準も短く書く。

## 受け入れ基準
- `default_enabled` な preprocess/model/ensemble の候補が取得できる。
- `requires` が満たないモデルを識別できる（importチェック）。
- preprocess の最低限の applicability 判定が動く（数値列/カテゴリ列の存在などで skip できる）。

## テスト
- `python -m compileall -q src`
- registry の簡単な自己テストを1つ追加（pytestが無い場合は `python -m tabular_analysis.ops...` でもよい）
  - toy schema を作って preprocess applicability が期待通りになることを確認
