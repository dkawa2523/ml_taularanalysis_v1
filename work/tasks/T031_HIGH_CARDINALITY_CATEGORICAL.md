# T031 特徴量拡張: 高カーディナリティカテゴリ（frequency/hash/OOF mean encoding）

## Objective
- カテゴリ列の水準数が多い（高カーディナリティ）場合に one-hot が破綻するため、**選択可能なエンコーディング**を追加する
- データリークを避ける（特に target encoding は事故りやすいので **安全設計**）
- ClearML のノイズを増やさずに “何をしたか” が追える（summary/recipe/manifest を更新）

---

## Scope
### 1) config（デフォルトは既存互換）
- `conf/task/preprocess/base.yaml` もしくは `conf/preprocess/*.yaml` に追加（配置は既存設計に合わせる）
  - `preprocess.categorical.encoding: onehot | frequency | hashing | target_mean_oof | auto`
  - `preprocess.categorical.auto_onehot_max_categories: 50`（例）
  - `preprocess.categorical.hashing.n_features: 128`（例）
  - `preprocess.categorical.target_mean_oof.folds: 5`
  - `preprocess.categorical.target_mean_oof.smoothing: 10.0`（任意）
- `auto` の場合:
  - カラムごとに unique 数を見て onehot / hashing を切替（頻度は明示指定）

### 2) preprocess 実装
- `frequency`:
  - train でカテゴリ→頻度（count/total）の mapping を作り、未知カテゴリは 0
- `hashing`:
  - sklearn の `FeatureHasher` または自前実装で OK（依存追加なし）
- `target_mean_oof`:
  - **OOF（Out-of-Fold）** で学習データをエンコードし、validation には train fold の統計で適用
  - 推論用 mapping は学習データ全体で再計算して保存
  - 初期は `regression` と `binary classification` のみ対応（multiclass は明示的にエラー/非対応）
- 出力:
  - `categorical_encoding_report.json`（カラムごとの encoding / unique 数 / 次元数）
  - `recipe.json` に encoding 設定を含める（recipe_hash に反映）
  - `summary.md` に「high-card対応を行った」ことを簡潔に記載

### 3) tests
- `tools/tests/smoke_high_card_cat.py`
  - 高カーディナリティ（例: 500 unique）のカテゴリ列を含む合成データで preprocess を実行
  - onehot だと爆発する条件でも hashing/frequency で完走し、出力次元が抑えられていることを検証
  - `categorical_encoding_report.json` が生成されること

---

## Acceptance Criteria
- encoding を yaml で切替可能（デフォルトは既存互換の onehot）
- 高カーディナリティでも preprocess が完走し、追跡性が保持される（recipe_hash/split_hash）
- `smoke_high_card_cat.py` が通る

---

## Verification
- `python -m compileall -q src`
- `python tools/tests/smoke_high_card_cat.py`

---

## Notes / Risks
- target encoding はリーク事故が起きやすい。OOF 実装とテストで “リークしない” を最優先
- ClearML 上のArtifactsは report.json + summary.md 程度に留める（大量ファイルは避ける）

---

## RESULT（必ず記入）
- 変更点サマリ:
- 追加/変更した config キー:
- verify 結果:
