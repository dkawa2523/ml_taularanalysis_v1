# T094 Pipeline: タスク爆発防止（limits）と並列上限（parallelism）と dry-run を実装し、運用事故を防ぐ

## 背景
- 処理グループやモデルが増えると、意図せず大量のタスクを生成しやすい。
- 試験段階では特に「うっかり100タスク起動」「Queueを詰まらせる」事故が起きやすい。
- そのため、実行前に plan を検証して止められる仕組みが必要（dry-run と limits）。

## ゴール
1. `pipeline.limits.*` を実装し、plan が上限を超える場合は実行を止める（dry-run なら表示のみ）。
   - `max_preprocess_variants`
   - `max_train_tasks`
   - `max_ensemble_tasks`
2. `pipeline.parallelism.*` を実装し、PipelineController 実行時の並列数（特にtrain）を制御できる。
   - `max_concurrent_steps`
   - `max_concurrent_train`
3. `--dry-run`（または `pipeline.dry_run=true`）を追加し、実行せずに plan を出力して終了できる。
   - plan の task 数、内訳、想定 project 階層を表示
   - `plan.json` は保存する（ClearML有効時はartifact、無効時はoutput_dir）

## 非ゴール
- すべての並列実行最適化（まずは “上限をかける” だけ）。
- 失敗ポリシーの再設計（T093 で固定済み）。

## 作業手順
### 1) plan から “タスク数” を算出できることを確認
- T091 の plan 表現から、以下が数えられること：
  - preprocess tasks 数
  - train tasks 数
  - ensemble tasks 数

### 2) limits チェックを追加
- plan 生成後、実行前にチェックする：
  - preprocess > max_preprocess_variants → error（ユーザーに原因と対策を表示）
  - train > max_train_tasks → error
  - ensemble > max_ensemble_tasks → error
- error のメッセージは「どの設定が考えられる原因か」を具体的に書く
  - include/exclude の見直し
  - mode を none にする
  - max_* を一時的に上げる（試験時のみ）

### 3) parallelism の適用
- ClearML PipelineController 側で並列数を制御できる API があるならそれを使う
  - 例: `pipeline_controller.set_default_execution_queue` 以外にも `add_step(..., execution_queue=..., ...)` や `set_max_concurrent_steps` 等
- API が無い場合は、少なくとも “train を最大N個ずつ投入” のような制御を driver で行う（ただし最小の実装で）

### 4) dry-run の追加
- CLI / Hydra のどこでフラグを受けるのが自然か確認し、既存設計に合わせる。
- dry-run は次を出す：
  - plan の内訳（preprocess x, train y, ensemble z）
  - 適用された fail_policy / limits / parallelism の値
  - project 階層の例（root/TabularAnalysis/usecase/...）

### 5) docs 追記
- 試験段階の推奨 limits 値（小さめ）
- “full runしたい時の手順” と “事故防止の考え方”

## 受け入れ基準
- limits 超過で、実行が安全に停止する（ClearMLに無駄タスクを大量に作らない）。
- dry-run で plan が確認できる（jq不要、pythonのみで読める）。
- parallelism の設定が反映される（少なくとも train の同時起動数が抑えられる）。

## テスト
- `python -m compileall -q src`
- dry-run で plan 出力が得られる
- limits を小さくして実行し、止まることを確認
