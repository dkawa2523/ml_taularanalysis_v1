# T048 Data Quality Gate 強化（リーク疑い/ID列/高カーディナリティ）

## Objective
- 本番事故の主因である「データ起因の不具合」を早期検知する
  - 欠損・重複・定数列・型ブレ
  - ID列（ほぼユニーク）やリーク疑い（ターゲットと過度に一致、名前が怪しい等）
  - 高カーディナリティ（one-hot 破綻の予兆）
- 検知結果を ClearML と artifacts に残し、運用で追えるようにする
- デフォルトは warn（解析を止めない）にし、運用フェーズで fail を選べるようにする

---

## Scope
### 1) quality report 拡張
- `src/tabular_analysis/ops/data_quality.py`（例）を拡張/新規作成
  - report を `data_quality.json` と `data_quality.md` で出力
  - severity を `pass/warn/fail` で判定
  - ルールは `conf/data/quality/base.yaml` で制御（thresholds）

### 2) gate（warn/fail）
- preprocess / infer で quality を実行
- `mode: warn|fail|off` をサポート（default warn）
- fail の場合は明確な例外とメッセージ（何が原因か）を出す

### 3) ClearML への反映（最小）
- properties は最小：
  - `quality_status`
  - `quality_issue_count`
- 詳細は artifacts に寄せる

---

## Acceptance Criteria
- synthetic データで warn が出る・fail で落ちることがテストで確認できる
- artifacts（json/md）が出力される
- ClearML 無効でも動作する
- docs（`docs/27_DATA_QUALITY.md`）が追加/更新される

---

## Verification
```bash
python -m compileall -q src
python tools/tests/test_data_quality_gate.py
```
