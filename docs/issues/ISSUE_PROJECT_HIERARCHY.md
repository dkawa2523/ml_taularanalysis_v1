# [ISSUE] ClearMLのproject階層（案A/B/C）

- Status: 未決
- Related decisions: docs/issues/DECISIONS.md

## 背景

ClearMLのproject階層は、UIの一覧性と検索性に直結する。
試験段階では複数案を試し、後で選べるようにしておきたい。

## 現象 / 期待

- 現象: project階層が未確定で、運用の比較がしづらい
- 期待: UIでの一覧性とテンプレTask運用が両立する案を選びたい

## 影響範囲

- すべてのTask（dataset_register, preprocess, train_model, leaderboard, inferなど）
- テンプレTaskの配置方針

## いまの暫定対応

- 特定の階層に固定しない
- 試験では案ごとの見え方を記録する

## 恒久対応案（候補）
- 案A: `<project_root>/<usecase_id>/<process>`
- 案B: `<project_root>/<usecase_id>/<run_group>/<process>`
- 案C: `<project_root>/experiments/<usecase_id>/<process>`

## 判定に必要な検証

- UI検索性（projectでの絞り込みが自然か）
- テンプレTaskの配置とclone運用の相性
- 既存runとの見分けやすさ

## 決定ログ（いつ/誰が/なぜ）
