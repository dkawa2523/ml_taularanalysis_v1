# [ISSUE] usecase_id規約（試験→本番）

- Status: 未決
- Related decisions: docs/issues/DECISIONS.md

## 背景

usecase_idはタグ/プロパティ/プロジェクト階層に影響するため、
試験段階での運用と本番移行の両方を意識した規約が必要になる。

## 現象 / 期待

- 現象: usecase_idの表記ゆれが起こり得る
- 期待: 試験で使っても本番移行しやすい規約を選びたい

## 影響範囲

- tags/propertiesの検索性
- project階層の設計
- 将来のmodel registry運用

## いまの暫定対応

- 明確な命名則を固定していない
- 試験データで複数案の見え方を比較する

## 恒久対応案（候補）
- 案A: `uc_<domain>_<problem>_<v1>`
- 案B: `uc_<domain>_<problem>` + project_rootで環境分離
- 案C: `uc_<domain>_<problem>__<env>`（test/prodなど）

## 判定に必要な検証

- UIの一覧性とソート性
- 既存usecaseとの衝突リスク
- 本番移行時の変更コスト

## 決定ログ（いつ/誰が/なぜ）
