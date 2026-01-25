# ClearML Issue運用ルール（試験段階）

このフォルダは、試験段階のClearML運用について
「何を試し、何が良く/悪く、どれを採用するか」を文書化するためのIssue置き場です。

## 基本ルール

- Issueは `docs/issues/` 配下にMarkdownで保存する
- `docs/issues/ISSUE_TEMPLATE.md` をコピーして作成する
- 本番運用ルールを押し付けず、候補を複数残す
- ClearMLサーバー設定（権限/queue/retention）はここでは変更しない

## ファイル命名

- `ISSUE_<TOPIC>.md` を基本とする
- 例: `ISSUE_PROJECT_HIERARCHY.md`, `ISSUE_TAGS_PROPERTIES_MIN_SET.md`

## 書き方の要点

- 事実/期待/影響/暫定対応を分離して書く
- 恒久対応案は「案A/B/C」など候補を列挙する
- 判定に必要な検証を明記する
- 決定したら `docs/issues/DECISIONS.md` に反映し、Issueにも決定ログを追記する

## 関連ドキュメント

- テンプレTask運用とIssueフォーマット: `docs/41_TEMPLATES_AND_ISSUE_FORMAT.md`
- 試験段階ポリシー: `docs/40_CLEARML_TEST_PHASE_POLICY.md`
