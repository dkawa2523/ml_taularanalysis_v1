# T072 docs整備：開発者が迷わない構成・運用（ディレクトリマップ/命名/リハーサル手順）を確定

## 目的
今回の拡張で開発者/ユーザーが迷わないよう、docsを更新し、構造・命名・ClearML運用・リハーサル手順を一箇所に整理する。

## 背景 / なぜ必要か
機能が増えると『どこを直すべきか』が不明になり、運用が破綻しやすい。最小のドキュメントで保守性を担保する必要がある。

## スコープ（やること / やらないこと）
- やる: docs/60-67を実装と一致させる
- やる: READMEや入口ドキュメントから参照できるようにする
- やらない: 運用ルールの固定（試験段階なので複数案を許容）

## 実装手順（Codexはこの順で実施）
1. docs/65 のディレクトリマップを実装の実体に合わせて更新。
2. docs/66 の命名/タグ/Properties を実装と一致させる（単一の正）。
3. docs/67 のリハーサルコマンドを最新化（dataset_register→pipeline→infer等）。
4. 可能なら `docs/INDEX.md` を追加し、入口を作る（任意）。


## 受け入れ条件（Acceptance Criteria）
- docs を読めば、開発者がどこを直せばよいか分かる。
- コマンド例が update-3_clearml の実装と一致している。
- 命名/タグ/HyperParametersの契約が矛盾しない。

## 検証コマンド（ローカル）
```bash
python - <<'PY'
from pathlib import Path
req = [
 'docs/60_PIPELINE_TRAIN_CONTRACT.md',
 'docs/61_CLEARML_HPARAMS_SECTIONS.md',
 'docs/62_CLEARML_PLOTS_REGRESSION.md',
 'docs/63_CLEARML_PIPELINES_VISIBILITY.md',
 'docs/64_INFER_BATCH_OPTIMIZE_CONTRACT.md',
 'docs/65_DEV_GUIDE_DIRECTORY_MAP.md',
 'docs/66_NAMING_TAGGING_POLICY.md',
 'docs/67_REHEARSAL_COMMANDS.md',
]
missing = [p for p in req if not Path(p).exists()]
print("missing:", missing)
assert not missing
print("docs ok")
PY

```

## 注意 / 設計ガードレール（冗長化・破綻防止）
- ClearML 連携のAPI呼び出しは可能な限り `src/tabular_analysis/clearml/` に集約する（process側に散らさない）。
- 可視化は `src/tabular_analysis/viz/` に集約し、各processは「何を可視化するか」だけ宣言する。
- HyperParameters は “全文” を入れない。**最小キー**をカテゴリ別に接続する（docs/61参照）。
- タスク名/タグ/Properties の付与ルールは docs/66 を単一の正とし、コード内にルールを散在させない。
- pipeline は「データ登録が前提」ではなく「dataset_id入力が前提」。dataset_register は独立運用（docs/60参照）。

