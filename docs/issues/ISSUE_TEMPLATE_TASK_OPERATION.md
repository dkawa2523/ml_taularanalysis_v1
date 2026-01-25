# [ISSUE] Template Task運用案

- Status: 未決
- Related decisions: docs/issues/DECISIONS.md

## 背景

試験段階ではUIでの手動clone運用を行っているが、
本番に向けて安定したテンプレ運用の形を検討したい。

## 現象 / 期待

- 現象: テンプレ運用の標準手順が未確定
- 期待: 事故率を下げつつ再現性を確保できる運用を選びたい

## 影響範囲

- テンプレTaskの配置と更新
- 実行オペレーション（UI/CLI/自動化）

## いまの暫定対応

- UIでCloneしてQueue投入

## 恒久対応案（候補）
- 案A: UIでの手動clone運用を継続
- 案B: 小さなCLIでclone+queueを補助（将来）
- 案C: pipeline cloneでパラメータを注入

## 判定に必要な検証

- 失敗率（間違ったQueue/Projectへの投入が起きないか）
- 再現性（テンプレ更新の影響範囲）
- 権限/制約（ClearMLサーバー設定に依存しないか）

## 決定ログ（いつ/誰が/なぜ）
