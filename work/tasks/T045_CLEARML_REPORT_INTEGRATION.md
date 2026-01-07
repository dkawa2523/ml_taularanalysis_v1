# T045 ClearML Report 統合（結論を1ページに集約）

## Objective
- pipeline 実行の結論を “1ページ” にまとめ、ClearML UI で非DSが迷わず判断できるようにする
- ClearML が無い環境では `report.md` を artifact として出力し、同じ情報が得られるようにする

---

## Scope
### 1) pipeline_report 生成
- `src/tabular_analysis/reporting/pipeline_report.py`（例）を追加
  - 入力：pipeline_run.json / leaderboard.csv / recommendation.json / decision_summary.md 等
  - 出力：
    - `report.md`（必須）
    - `report.json`（機械可読、必須）
    - 可能なら `report_links.json`（各 task の run_dir/clearml_url）
- 内容（最低限）：
  - 実験ID（grid_run_id）
  - データセット/スキーマ概要
  - 比較条件（comparability）
  - 上位モデル表（トップN）
  - 推奨モデルの根拠
  - 注意点（不均衡/校正/不確かさの有効化状況）

### 2) ClearML Report への反映（optional）
- ClearML が有効で、Report API が使える場合のみ
  - report.md の内容を ClearML 側に “Report” として保存
- 使えない場合は no-op（artifact 出力のみ）

### 3) docs
- `docs/24_REPORTING.md` を追加/更新し、report の読み方を明記

---

## Acceptance Criteria
- ローカル pipeline 実行で report.md が生成される
- report.md に推奨モデルID・主要指標・比較条件が含まれる
- ClearML 無効でも verify が通る
- docs が整備されている

---

## Verification
```bash
python -m compileall -q src
python tools/tests/test_pipeline_report.py
```
