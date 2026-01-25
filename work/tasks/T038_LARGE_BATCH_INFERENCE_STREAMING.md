# T038 スケール対応: chunked batch infer（大規模CSVでOOMしない）

## Objective
- 業務では推論対象が大きくなるため、CSV/Parquet の **バッチ推論を chunk で処理**できるようにする
- 既存の schema validation（T026）と両立させ、エラーがあっても “どこで落ちたか” が分かるようにする

---

## Scope
### 1) config
- `conf/task/infer/base.yaml` に追加
  - `infer.batch.chunk_size: 50000`（例、デフォルトは小さめでも可）
  - `infer.batch.output_format: csv | parquet`
  - `infer.batch.write_mode: overwrite | append`
  - `infer.batch.max_rows: null`（debug用）
- chunk_size が null の場合は既存互換（全量読み込み）

### 2) infer 実装
- 入力がファイルの場合:
  - pandas の `read_csv(..., chunksize=...)` 等で逐次処理
  - 予測結果を逐次書き込み（append）
- スキーマ検証:
  - strict/warn/coerce に従い、chunk 単位で検証
  - 失敗 chunk を errors.jsonl 等に記録（全体を落とさないオプションも可）
- 出力:
  - out.json に chunked 実行情報（chunk_size / rows / errors_count）

### 3) tests
- `tools/tests/smoke_batch_chunked.py`
  - そこそこ大きい（例: 20k 行程度）の合成データで chunk infer を実行
  - output が生成されること
  - out.json に chunked 情報があること

---

## Acceptance Criteria
- chunk_size を指定したバッチ推論が完走する
- OOM を避ける設計になっている（全量読み込みしない）
- `smoke_batch_chunked.py` が通る

---

## Verification
- `python -m compileall -q src`
- `python tools/tests/smoke_batch_chunked.py`

---

## Notes / Risks
- parquet の append は実装が難しい場合があるので、最初は csv append でOK（parquetは後続で改善）
- errors の扱い（落とす/続行）は運用方針に合わせて config で切替できる形が望ましい

---

## RESULT（必ず記入）
- 変更点サマリ:
- 追加/変更した config キー:
- verify 結果:
