# リハーサルシナリオ（試験段階）

このドキュメントは、試験段階で **必ず1回通す**リハーサル手順をまとめたものです。
目的は「機能が動く」だけでなく、ClearML上の見え方（プロジェクト階層・Artifacts・Properties）が
意図通りかを確認することです。

## 前提

- まずは **ローカルClearMLサーバー**で試験
- 問題がなければ **社内ClearMLサーバー**へ接続先を切り替えて再実行
- Queue/権限/保持期間などの運用設計は **この段階では確定しない**

### テンプレTask準備（PipelineController/Clone を試す場合）

```bash
python -m tabular_analysis.ops.manage_clearml_templates --plan --project-root LOCAL
python -m tabular_analysis.ops.manage_clearml_templates --apply --project-root LOCAL --repo <repo_url> --branch <branch>
python -m tabular_analysis.ops.manage_clearml_templates --validate --project-root LOCAL --repo <repo_url> --branch <branch>
```

- repo/branch は必要に応じて指定する（未指定なら git の origin/HEAD を自動検出）

## リハーサルスクリプト（推奨）

`tools/rehearsal/run_rehearsal.py` で **毎回同じ手順**を再現できるようにします。

- `--mode local`：ClearML 無効
- `--mode logging`：ClearML 有効・ローカル実行
- `--dry-run`：コマンド一覧の表示のみ（`out/` と `toy.csv` は作成しないが `rehearsal_log.md` には記録する）
- `--usecase-id`：任意指定（未指定時は `test_<dataset>_<timestamp>` を自動生成）

実行後に残るもの：
- `work/rehearsal/rehearsal_log.md`（実行環境・usecase_id・結果）
- `work/rehearsal/out/<mode>/<usecase_id>/`（成果物。`report.md / decision_summary.md` を参照）
- `work/rehearsal/tmp/toy.csv`（リハーサル用の小さなデータ）

---

## シナリオA：完全ローカル（ClearML無効）で完走

目的：純粋に機能の完走（データ→前処理→学習→leaderboard）を確認する。

```bash
cd ml-solution-tabular-analysis
python tools/rehearsal/run_rehearsal.py --mode local
```

確認：
- `work/rehearsal/out/<mode>/<usecase_id>/` 配下に各工程の成果物が出る
- doctor lint が通る（T050までで既に導入済みの場合）

---

## シナリオB：ローカルClearML（loggingモード）で完走

目的：ClearML UI契約（Artifacts/Properties/Tags/Project）を確認する。

1) `clearml-init` 済みであることを確認し、ローカルサーバーへ接続
2) loggingモードで pipeline を1回実行

例：
```bash
python tools/rehearsal/run_rehearsal.py --mode logging
```

UIで確認すること（詳細: `docs/55_CLEARML_UI_CHECKLIST.md` / `docs/53_CLEARML_HYPERPARAMETERS_CONTRACT.md`）：
- Projects配下が `.../<solution_root>/<usecase_id>/<process_group>` になっている
- 各Taskに `config_resolved.yaml / out.json / manifest.json` がArtifactsとしてある
- leaderboardに `leaderboard.csv / recommendation.json / decision_summary.md` がある
- preprocess で processed dataset が Datasets に作成されている（`processed_dataset_id` と一致）
- train の Scalars/Plots/Debug Samples が UI に出ている（詳細は `docs/51_CLEARML_PLOTS_SCALARS_DEBUGSAMPLES_CONTRACT.md`）
- HyperParameters が最小セットである（`usecase_id`, `schema_version`, `clearml.execution` など）
- promoteは自動で走らない（recommendと分離されている）

processed dataset SDK確認（IDは preprocess の `out.json` から取得）：
```bash
python - <<'PY'
from clearml import Dataset

dataset_id = "<processed_dataset_id>"
dataset = Dataset.get(dataset_id=dataset_id)
print(dataset.id, dataset.name, dataset.get_tags())
PY
```

補足：
- 使用した `usecase_id` は `work/rehearsal/rehearsal_log.md` に記録される

---

## シナリオC：PipelineController で子タスク生成（テンプレ + Agent）

目的：template 作成 → controller 実行 → 子タスク生成までを通しで確認する。

1) テンプレ Task を作成（未作成の場合）
```bash
python -m tabular_analysis.ops.manage_clearml_templates --plan --project-root LOCAL
python -m tabular_analysis.ops.manage_clearml_templates --apply --project-root LOCAL --repo <repo_url> --branch <branch>
python -m tabular_analysis.ops.manage_clearml_templates --validate --project-root LOCAL --repo <repo_url> --branch <branch>
```

2) ClearML Agent を起動（queue を合わせる）
```bash
clearml-agent daemon --queue default --foreground
```

3) PipelineController で実行（同じデータ条件を使う）
```bash
python -m tabular_analysis.cli task=dataset_register \
  run.clearml.enabled=true run.clearml.execution=logging \
  data.dataset_path=/path/to/data.csv data.target_column=target

python -m tabular_analysis.cli task=pipeline \
  run.clearml.enabled=true \
  run.clearml.execution=pipeline_controller \
  run.clearml.queue_name=default \
  data.raw_dataset_id=<RAW_DATASET_ID>
```

UIで確認すること：
- template tasks に `template:true` と `process:<...>` の tags が付いている
- pipeline task から子タスクが生成され、Queue に投入されている
- child tasks の `clearml.execution` が `logging` になっている（HyperParameters）
- `pipeline_run.json` が pipeline task の artifact にある
- 子タスクが `.../<solution_root>/<usecase_id>/02_Preprocess` などの階層に生成される

---

## シナリオD：社内ClearMLへ接続先切替 → 同じ条件で再実行

目的：環境差（ストレージ、python依存、Agent環境）による問題を洗い出す。

補助ツール：
```bash
python tools/rehearsal/plan_migration.py --from local --to internal
```

### 差分チェックリスト（最低限）

- ClearML接続先（API/Web/Files）と認証キーが社内向けに切替済みか
- Artifacts保存先（files host / object storage）の権限・容量・アップロード制限
- データ/モデルの参照パスがAgent環境で解決できるか（共有ストレージ/マウント差分）
- Agent実行環境の差分（Python/依存/OSライブラリ/GPU/コンテナ）
- 権限（Project作成/Clone/Artifacts/Report）と監査ログ
- ネットワーク/プロキシ/DNS/証明書による疎通
- UI契約（project root / tags / properties）が変わらないこと

### 切替手順（試験段階）

1) `clearml.conf`（または環境変数）を社内サーバーへ
2) まずは logging で動作確認（Agentを使う前に）
3) UIからCloneしてQueue投入（Queue名はコードで固定しない）
4) Artifacts/Reportの表示と大きなファイルのアップロード可否を確認
5) 差分やNGは `docs/issues` に記録

確認：
- Artifactsのアップロード先が社内環境で問題ないか
- large artifact（predsなど）で失敗しないか
- 同一usecase_idで実行したときに UI上で追えるか

### よくあるエラー / つまずきポイント

- 401/403: 権限不足、APIキーのスコープ不足
- files host 404/timeout: ホスト設定/プロキシ/DNSの不整合
- Upload失敗: ストレージ権限/容量/サイズ制限
- Agent失敗: Python/依存/OSライブラリ/GPUドライバの差
- データパス不一致: 共有ストレージやマウント位置の差分
- Queue詰まり: Agentが未起動、またはQueueに紐づいていない

---

## シナリオE：複数仕様案の試験（命名・タグ・Properties）

目的：本番運用に向けて「どの仕様がUI上で扱いやすいか」を比較する。

- `ops/usecase_id_policy` を切り替える
- `run.clearml.project_root` を切り替える（または環境変数）
- `ops/clearml_policy` を切り替える

比較時は、各実行の `report.md / decision_summary.md` を見比べ、
非DSの視点で「判断しやすいか」を評価する。
