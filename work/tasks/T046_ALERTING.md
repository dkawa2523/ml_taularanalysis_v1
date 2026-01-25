# T046 Alerting（品質/ドリフト/失敗を運用へ通知）

## Objective
- 運用で最も重要な「気づける」導線を作る
  - データ品質 NG
  - ドリフト閾値超え
  - champion-challenger で劣化
  - promote/rollback など重要イベント
- ClearML が有効なら Task の tags/properties を更新し、UI上で状態が分かるようにする
- 依存を増やしすぎない：通知は **file logger（デフォルト）** + optional webhook のみに留める

---

## Scope
### 1) アラート統一インターフェース
- `src/tabular_analysis/ops/alerting.py` を追加
  - `emit_alert(kind, severity, title, message, context_dict)`
  - sinks：
    - `file`（JSONL、デフォルト）
    - `stdout`
    - `webhook`（URL が設定されている場合のみ）
  - ClearML 有効時：
    - `task.add_tags(["alert:<kind>", "severity:<...>"])`
    - properties に `last_alert_kind` など最小セットのみ

### 2) フックの追加
- data_quality gate / drift_report / infer などから呼び出す
- opt-in：`conf/run/alerts/base.yaml` で enabled を制御（デフォルト false）

### 3) docs
- `docs/25_ALERTING.md` に運用ルール（severity/通知先/ログ場所）を記載

---

## Acceptance Criteria
- alerts.enabled=false では何も起きない（ノイズを増やさない）
- enabled=true + file sink で JSONL が出力される
- ClearML 無効でも動作する
- テストで file sink の出力が確認できる

---

## Verification
```bash
python -m compileall -q src
python tools/tests/test_alerting_logfile.py
```
