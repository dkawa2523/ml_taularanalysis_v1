# T097 docs/ 運用ルール・拡張ガイドの整備（コードレビューで追いやすい形に固定）

## 背景
- 今回の改良は “運用ルール” に関わる部分が多い（テンプレ運用、partial failure、skip、limits、project階層、profile/group設定）。
- 特に「テンプレートタスク増殖を避ける（template_set / schema_version / 単一pipelineテンプレ）」は運用事故につながるため、明文化しておく。
- 後から別の開発者が入った時に、コードだけ見ても意図が読めないと破綻しやすい。
- そのため docs/ に「なぜこのルールなのか」「どこを変えれば良いか」を明文化する。

## ゴール
1. docs/ 以下に、以下を満たす運用ドキュメントを追加/更新する（新規は最小限、既存があれば追記優先）：
   - Pipeline v2 設計（profile / groups.mode / base+差分）
   - テンプレートタスク運用（template_set / schema_version / repo/branch）
   - optional deps と SKIP の扱い（落ちないが嘘を出さない）
   - partial failure（fail_policy）と run_summary の読み方
   - limits/parallelism/dry-run（事故防止）
2. “開発者がどこを見れば良いか” をディレクトリ単位で明確化する：
   - registry（variant追加）
   - pipeline plan/driver（挙動変更）
   - ClearML表示（hparams/tags/projects/plots）
   - preprocess/train/ensemble/leaderboard 各処理の拡張点
3. コードレビューで追いやすいように、ルールは **箇条書き** と **表** を使い、冗長な文章を避ける。

## 非ゴール
- 社内サーバ/権限/Queue名などを固定する（試験段階では固定しない方針）。

## 作業手順
### 1) 既存 docs の棚卸し
- `docs/70_CHATGPT_HANDOFF.md` を含め、ClearML/運用系の docs を確認する。
- 既に同等の doc がある場合は “追記・整理” を優先し、新規ファイル乱立を避ける。

### 2) 追加/更新する doc の最小構成（例）
- `docs/80_PIPELINE_V2_OVERVIEW.md`（新規 or 既存に追記）
  - profile/groups/base差分
  - preprocess×model 展開
  - project階層規約
- `docs/81_CLEARML_TEMPLATE_POLICY.md`
  - template_set / schema_version
  - テンプレ増殖を避けるルール
  - clone対象の選び方
- `docs/82_EXECUTION_POLICY_SKIP_FAIL.md`
  - skip理由の一覧
  - fail_policy の意味
  - run_summary の見方
- `docs/83_DEVELOPER_EXTENSION_GUIDE.md`
  - 「新しいモデルを追加する」「新しい前処理を追加する」「新しい処理グループを追加する」
  - どのファイルを触るか（パスで明示）

※ファイル名は既存docsの命名に合わせて調整してよい。

### 3) “運用ルールは変更しやすい” 形に
- ルールの多くは `conf` で変更できる（profile/groups/fail_policy/limits/parallelism）。
- ただし “固定したい設計意図” は doc に残し、むやみに変えないようにする。

## 受け入れ基準
- 新規参入の開発者が docs を読めば、
  - どの仕組みがどこにあるか
  - 何を変えるべき/変えてはいけないか
  が把握できる。
- docs が冗長に増えず、既存 docs と矛盾しない。

## テスト
- なし（ただし markdown lint 等があるなら通す）