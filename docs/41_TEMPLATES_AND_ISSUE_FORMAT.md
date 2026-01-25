# テンプレTask運用（将来）と Issue（md）テンプレ

試験段階では ClearMLサーバー側で「UIからClone→Queue投入」を手で行います。
一方で、本番に向けてテンプレTask運用を導入しやすいよう、**検討内容をIssue形式で残す**ことが目的です。

## 試験段階の前提（明文化）

- **テンプレTaskの作成・運用は任意**（運用の強制はしない）
- **コード側でQueueを強制しない**（UI運用で切り替え可能にする）
- テンプレTaskの有無に依存せずに実行できることを優先する

## テンプレTask運用の基本方針（将来）

- テンプレは「用途/工程」で最小限に分ける
  - dataset_register / preprocess / train_model / leaderboard / infer / promote / retrain
- テンプレTaskは `TEMPLATES/...` のプロジェクト配下に置ける設計を想定する
- テンプレの更新は頻繁にしない（更新する場合は version を付けて新テンプレを追加）

## テンプレTask作成手順（試験段階）

1. 該当プロセスを **loggingモード**で1回実行し、Taskが正しく登録されること
2. Taskの SCRIPT（repo/branch/entrypoint/working_dir）が正しいことを確認する
   - ローカル絶対パスが混ざっていない
3. Taskの tags/properties/Artifacts が UI契約に沿っていることを確認する
4. `TEMPLATES/...` へ配置して命名し、Cloneでパラメータを変更して動作確認する

## ローカルClearMLでテンプレTaskを作成/更新する（試験段階）

ローカルClearMLで template を作る場合は CLI を使う。

```bash
python -m tabular_analysis.ops.manage_clearml_templates --plan --project-root LOCAL
python -m tabular_analysis.ops.manage_clearml_templates --list --project-root LOCAL
python -m tabular_analysis.ops.manage_clearml_templates --apply --project-root LOCAL --repo <repo_url> --branch <branch>
python -m tabular_analysis.ops.manage_clearml_templates --cleanup-obsolete --project-root LOCAL
python -m tabular_analysis.ops.manage_clearml_templates --validate --project-root LOCAL --repo <repo_url> --branch <branch>
```

- `--repo/--branch` は後から変更できる（未指定なら git の origin/HEAD を自動検出）
- template_set の世代は `run.clearml.template_set_id` で切り替える
- tags は `template:true` / `template_set:<...>` / `process:<...>` / `solution:tabular-analysis` を含める
- template 探索は tags ベース（task_id 固定はしない）

## 確認ポイント（チェックリスト）

- 実行情報: repo/branch/entrypoint/working_dir が正しく、作業端末の絶対パスが残っていない
- パラメータ: 変更対象（datasetやmodel指定など）がUIから変更でき、反映される
- UI契約: tags/properties/artifacts が `docs/03_CLEARML_UI_CONTRACT.md` を満たす
- 再現性: Clone後の実行でも out/manifest 生成とログが同じ形式で残る
- 配置: テンプレProject配下で識別でき、Queue運用をコードに依存しない

## よくある失敗

- SCRIPT にローカルの絶対パスが残り、Clone先で動かない
- loggingモードのTaskを本番テンプレとして扱ってしまう
- tags/properties/Artifacts が欠落し、UI契約を満たせない
- テンプレ更新時に名称/版管理が曖昧で、どれが最新かわからない
  - 更新時は version を付けて新テンプレを追加する

## Issue（md）テンプレ

試験段階で見つけた運用課題は、以下の形式で `docs/issues/`（または `docs/` 直下）に残します。

```md
# [ISSUE] <短い題名>

## 背景

## 現象 / 期待

## 影響範囲

## いまの暫定対応

## 恒久対応案（候補）
- 案A:
- 案B:

## 判定に必要な検証

## 決定ログ（いつ/誰が/なぜ）
```

### 例（テンプレTask運用）

- 「テンプレTaskをどのプロジェクト階層に置くべきか」
- 「テンプレの更新のたびに model registry の stage 運用に影響が出ないか」
