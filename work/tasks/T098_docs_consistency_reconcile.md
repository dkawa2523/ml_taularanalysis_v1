# T098 docs: check_docs 全体の整合性監査（T097/アンサンブル/パイプラインUI）と矛盾修正

## 背景
- `check_docs` ブランチでは、T097 までの改良（pipeline v2 / ensemble / ClearML運用ルール強化）により、docs が増えたり追記された結果、
  **ドキュメント間の齟齬**（古い想定・矛盾・記述漏れ）が発生しやすい状態になっている。
- 実運用（試験段階）では、docs が **テスト実行→ClearML UI での確認**に直結している必要がある。

## ゴール
1. `docs/` 以下の Markdown を横断で棚卸しし、T097 時点の実装と矛盾する記述を修正する。
2. 特に以下の論点を必ず整合させる：
   - **アンサンブルが「無し」扱いになっている箇所を撲滅**（T077〜T088/T089〜T097で ensemble 実装済みの前提）
   - pipeline v2（profile/groups/plan/driver）と **ClearML Pipelines タブでの見え方**
   - Local と Agent での “見え方一致” の方針（テンプレ clone 必須、commit pin 問題の回避）
   - optional deps（例: TabPFN/LightGBM/XGBoost/CatBoost 等）で落ちない SKIP 設計
   - partial failure（fail_policy / run_summary）
3. docs の増殖を避ける。
   - 既存ファイルがある場合は **追記・整理**を優先。
   - どうしても新規ファイルが必要な場合も、最小限（最大1ファイル）にする。

## 非ゴール
- 実装コードの仕様をこのタスクで大きく変更しない（docs を実装に合わせる）。

## 作業手順
### 1) まず “現状の実装（src/conf/tools）” を正として把握
- pipeline v2 の入口（Hydraキー、profile、groups、grid）
- preprocess variants / model variants の registry 方式
- ensemble（mean_topk / weighted / stacking）の実装位置と呼び出し方式
- ClearML のタグ・プロジェクト階層・hyperparameters 分類

> 重要：docs を読んで判断しない。コード（src/conf/tools）→ docs の順で整合させる。

### 2) docs 横断棚卸し（齟齬のパターンを検出）
以下を grep/検索して、矛盾候補を列挙してから修正する：
- 「アンサンブル無し」「ensemble 未対応」「not supported」など
- pipeline の説明が古い（dataset_register を pipeline に含める/含めない、テンプレ前提、controller の見え方など）
- ClearML UI での配置（Scalars/Plots/Artifacts/DebugSamples）
- hyperparameters のカテゴリ設計（全部 General に集約される前提が残っていないか）
- テンプレタスク増殖の運用（template:true、template_usecase_id、template_set、schema_version 等）

### 3) 修正方針（統一ルール）
- docs は次の “契約（Contract）” を優先する：
  - `03_CLEARML_UI_CONTRACT.md`
  - `50/51/52/53_..._CONTRACT.md`
  - `60_PIPELINE_TRAIN_CONTRACT.md`
  - `83_ENSEMBLE_POLICY.md`
  - `81_CLEARML_TEMPLATE_POLICY.md`

- 他の docs は「上記 Contract への参照」へ寄せる。
  - 例：個別 doc に UI の詳細を重複記述しない。リンク + 重要ポイントだけ。

- 重複ファイル（例：serving が複数ある等）がある場合：
  - **削除しない**（履歴や参照が壊れるのを避ける）
  - 代わりに冒頭へ「この文書は古い/統合先はこちら」を追記し、INDEX からは統合先のみ参照。

### 4) 変更対象の目安
必ず確認して矛盾があれば修正（ファイル名は実在するものに合わせる）：
- `docs/55_CLEARML_UI_CHECKLIST.md`（T099で本格修正するが、T098で矛盾の種は潰してよい）
- `docs/05_PROCESS_CATALOG.md`（ensemble / pipeline v2 を含む最新の処理カタログに）
- `docs/60_PIPELINE_TRAIN_CONTRACT.md`（profile/groups/grid/plan/driver と一致）
- `docs/83_ENSEMBLE_POLICY.md`（mean_topk/weighted/stacking の位置づけと leaderboard 比較）
- `docs/63_CLEARML_PIPELINES_VISIBILITY.md`（Pipelines タブに出る条件、テンプレ clone 前提の説明）
- `docs/81_CLEARML_TEMPLATE_POLICY.md`（commit pin / repo/branch 変更に強い運用）
- `docs/67_REHEARSAL_COMMANDS.md` or `docs/84_REHEARSAL_GUIDE.md`（55と整合するように）

### 5) INDEX の更新
- `docs/INDEX.md` に “現行の正” を明示する：
  - pipeline v2 の docs 入口
  - ensemble の docs 入口
  - UI checklist の docs 入口
  - トラブルシュート（agent/git/commit pin）

## 受け入れ基準
- docs 内に「ensemble 未対応」「アンサンブル無し」等、実装と矛盾する記述が残っていない。
- pipeline の説明が “controller型（Pipelines タブ）” と一致している。
- template/agent 実行での commit pin 問題（fatal: unable to read tree）に対する説明が docs に明記されている。
- docs が増えすぎていない（新規ファイルは最大1つまで、基本は既存修正）。

## テスト
- なし（T100で UI 自動検証 runner を追加する）

---

## Update (2026-01-13)
- docs は先行更新済みのため、pipeline v2 / ensemble / reporting 実装後に最終整合を行う（Phase 4, T101）
