# データ品質・検証

## データ品質ゲート（Data Quality Gate）
- 設定: `conf/data/quality/base.yaml`
- モード: `warn` / `fail` / `off`
- しきい値例:
  - 欠損率 / 重複率 / 定数列 / 型混在 / 高カーディナリティ / ID類推 / リーク類似
- 入口:
  - dataset_register / preprocess 実行時

## 検証コマンド（ローカル）
- `docs/15_VERIFICATION.md` の quick / full を参照
- 代表例: `python tools/tests/verify_all.py --quick`

## 運用メモ
- warn はログ/レポートへ記録、fail はジョブ停止
- しきい値は `conf/data/quality/base.yaml` で調整
