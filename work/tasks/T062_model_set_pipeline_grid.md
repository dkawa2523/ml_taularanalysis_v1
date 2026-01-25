# T062 回帰モデル「ほぼ全て」をmodel_setで実行できるようにし、pipelineのgridを整理

## 目的
回帰モデルを一括学習するための `pipeline.model_set=regression_all` を導入し、利用可能な回帰モデルを自動列挙/固定リスト化して pipeline から実行できるようにする。

## 背景 / なぜ必要か
ユーザーは前処理を選び、回帰モデルをできる限り網羅的に実行して比較したい。毎回モデル名リストを手で書くのは運用負荷。

## スコープ（やること / やらないこと）
- やる: `conf/pipeline/model_sets/` を追加し regression_all を定義
- やる: registry から task_type=regression を抽出できる仕組みを追加
- やらない: モデル実装の全面改修（既存 registry を活かす）

## 実装手順（Codexはこの順で実施）
1. `conf/pipeline/model_sets/regression_all.yaml` を追加（または既存に追記）し、回帰向けモデルvariant一覧を定義する。
2. `src/tabular_analysis/registry/models/` を調査し、各モデルが regression/classification を持つ仕組みがあるならそれを利用して自動列挙関数を追加する（無い場合は最小のマッピングを作る）。
   - 例: `list_model_variants(task_type="regression") -> list[str]`
3. pipeline で `pipeline.model_set` が指定されたら、それを `pipeline.model_variants` に展開する。
4. docs/60 を更新（model_setの説明）。


## 受け入れ条件（Acceptance Criteria）
- `pipeline.model_set=regression_all` で train が複数モデル分生成される。
- 新しい回帰モデルを registry に追加すると model_set に反映できる（固定リストの場合は docsに手順を明記）。

## 検証コマンド（ローカル）
```bash
python -m compileall -q src
python - <<'PY'
# 簡易: registry側に列挙APIができたらimportして表示
try:
    from tabular_analysis.registry.models import list_model_variants
    print(list_model_variants(task_type="regression")[:10])
except Exception as e:
    print("skip:", e)
PY

```

## 注意 / 設計ガードレール（冗長化・破綻防止）
- ClearML 連携のAPI呼び出しは可能な限り `src/tabular_analysis/clearml/` に集約する（process側に散らさない）。
- 可視化は `src/tabular_analysis/viz/` に集約し、各processは「何を可視化するか」だけ宣言する。
- HyperParameters は “全文” を入れない。**最小キー**をカテゴリ別に接続する（docs/61参照）。
- タスク名/タグ/Properties の付与ルールは docs/66 を単一の正とし、コード内にルールを散在させない。
- pipeline は「データ登録が前提」ではなく「dataset_id入力が前提」。dataset_register は独立運用（docs/60参照）。

