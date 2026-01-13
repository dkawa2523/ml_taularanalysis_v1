# T069 infer.mode=batch：サマリータスク + 条件ごとのchild推論タスクを生成し、集約可視化をPLOTSに表示

## 目的
batch 推論を「サマリー + child(single相当)」に分け、各条件の入力→出力テーブルと、全体集約のテーブル/分布グラフをPLOTSに表示できるようにする。

## 背景 / なぜ必要か
batchを1タスクに押し込むと検証・比較がしづらい。ケースごとに追跡でき、サマリーで全体が分かる構造が必要。

## スコープ（やること / やらないこと）
- やる: batch summary が child tasks を clone/enqueue で作る
- やる: summary が child の結果を集約し、PLOTSへ
- やらない: 推論を pipeline_controller 化しない

## 実装手順（Codexはこの順で実施）
1. `infer.mode=batch` の実装を追加:
   - summary task が入力条件を読み取る（csv/json）
   - 条件ごとに child task（infer.mode=single相当）を clone/enqueue
   - child は自分の入力→出力テーブルをPLOTSへ
2. summary は child 完了を待ち、結果（入力条件+予測）を DataFrame にして Plotly Table を PLOTS へ。
3. 予測値分布（hist）など軽量なグラフを追加。
4. ハイパーパラメータ:
   - summary: Inputs/Execution/Model を中心に
   - child: Inputs/Model/Dataset を最小で
5. docs/64 を更新（上限Nや注意事項）。


## 受け入れ条件（Acceptance Criteria）
- batch 実行で summary + 複数child推論タスクが ClearML に作成される。
- summary の PLOTS に全条件の入力→出力テーブルが表示される。
- child の PLOTS に各条件の入力→出力テーブルが表示される。

## 検証コマンド（ローカル）
```bash
python -m compileall -q src
python -m tabular_analysis.cli task=infer run.clearml.enabled=false infer.mode=batch infer.dry_run=true

```

## 注意 / 設計ガードレール（冗長化・破綻防止）
- ClearML 連携のAPI呼び出しは可能な限り `src/tabular_analysis/clearml/` に集約する（process側に散らさない）。
- 可視化は `src/tabular_analysis/viz/` に集約し、各processは「何を可視化するか」だけ宣言する。
- HyperParameters は “全文” を入れない。**最小キー**をカテゴリ別に接続する（docs/61参照）。
- タスク名/タグ/Properties の付与ルールは docs/66 を単一の正とし、コード内にルールを散在させない。
- pipeline は「データ登録が前提」ではなく「dataset_id入力が前提」。dataset_register は独立運用（docs/60参照）。

