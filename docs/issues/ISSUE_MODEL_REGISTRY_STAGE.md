# [ISSUE] model registryのstage運用

- Status: 未決
- Related decisions: docs/issues/DECISIONS.md

## 背景

model registryのstageはpromote/rollbackと密接に関係する。
試験段階で候補を比較し、将来の運用負荷を見極めたい。

## 現象 / 期待

- 現象: stageの数や名称が未確定
- 期待: UIで理解しやすく、運用負荷が低い方式を選びたい

## 影響範囲

- promote/rollback運用
- champion/challenger運用
- モデルの検索/可視化

## いまの暫定対応

- stageの運用を固定しない

## 恒久対応案（候補）
- 案A: candidate -> staging -> prod
- 案B: challenger/champion
- 案C: dev/prod の2段階

## 判定に必要な検証

- promote/rollbackの手順と整合するか
- UIでの理解しやすさ
- 誤運用のリスク

## 決定ログ（いつ/誰が/なぜ）
