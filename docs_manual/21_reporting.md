# レポーティング

## 出力物
- `report.md`：人向けの要約
- `report.json`：機械可読の要約
- `report_links.json`：run_dir / ClearML URL の一覧

## ClearML 連携
- ClearML 有効時は report を artifact としてアップロード
- UI への掲載は可能な場合のみ（失敗時は無視）

詳細は `docs/24_REPORTING.md` を参照。
