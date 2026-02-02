# 運用・トラブルシュート

## 運用フロー（要点）
- pipeline 実行 → leaderboard で推薦 → 推論で利用
- テンプレ更新後は再 clone / 再 enqueue が前提

## トラブルシュートの入口
- ClearML Agent: `docs/68_CLEARML_AGENT_TROUBLESHOOTING.md`
- ClearML UI: `docs/69_CLEARML_TROUBLESHOOTING.md`
- 実行手順: `docs/16_OPERATIONS_RUNBOOK.md`

## よくある問題
- Queue 名不一致 / Agent 停止
- テンプレ不整合（古い clone）
- pipeline が UI に表示されない（project / system tag / hidden）
