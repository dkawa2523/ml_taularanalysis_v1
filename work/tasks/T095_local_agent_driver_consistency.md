# T095 Local/Agent 実行の “見え方一致” を設計で固定（plan + driver 分離、テンプレclone必須、project階層統一）

## 背景
- 過去の問題で、Agent 実行時に repository/commit pin で clone 失敗し、pipeline が子タスクを作れず止まった。
- 現在はテンプレートタスク（template:true）運用が導入されているが、
  - Local 実行と Agent 実行で “ClearML上の見え方” が揃わないと、運用/保守で混乱が起きる。
- そのため、pipeline は **必ず plan を生成し、driver が実行方式（Local/Agent）を変える**という構造を固定する。

- 追加要件：処理/モデルが増えても pipeline テンプレート自体は原則1つ（または最小）に保ち、ON/OFF やセット選択は pipeline の Hyperparameters で行える設計に寄せる。
## ゴール
1. pipeline の実装を「plan生成」と「実行(driver)」に分離し、Local/Agent で同じ plan を使う。
2. Agent 実行では **子タスク生成はテンプレからの clone を必須**とする（過去の clone 失敗対策と、再現性のため）。
3. Local 実行でも、子タスク相当を作成して記録する（= 1コマンドで複数処理が走り、ClearML上も子タスクが残る）。
   - ただし Local 実行は PipelineController ではなく、同等の “見え方” を目指す（親子関係/タグ/プロジェクト階層）。
4. project 階層・タグ・Hyperparameters のカテゴリが Local/Agent で一致する（または差分が最小で説明可能）。

## 非ゴール
- 完全な同時並列の一致（Local は逐次でも良い）。重要なのは “見え方/構造/メタ情報の一致”。

## 作業手順
### 1) 現状の実行分岐を特定
- `run.clearml.execution`（例: local / pipeline_controller / agent など）がどこで分岐しているか確認。
- PipelineController での step 追加箇所がどこか確認。

### 2) plan 生成を “純粋関数” に寄せる
- 入力：cfg / registry / schema / fail_policy / limits
- 出力：plan（ステップと依存関係、taskパラメータ、projectパス、タグ）
- plan 生成は ClearML に依存しない（ClearML無効でも動く）

### 3) driver を2系統に分ける
- `LocalDriver(plan)`：
  - plan に従い preprocess → train → ensemble → leaderboard を順に呼ぶ
  - 各処理は “通常の単体タスク実行” と同じコード経路を考虑（重複禁止）
  - ClearML 有効なら各タスクは Task を作り、project/tags/hparams をセットして実行
- `AgentDriver(plan)`：
  - pipeline テンプレを clone して PipelineController を起動
  - 子タスクは process テンプレ（dataset_register/preprocess/train_model/ensemble/leaderboard）を clone して投入
  - commit pin は使わない（branch/ repo はテンプレ由来、または設定で上書き可能）
  - queue は `run.clearml.queue_name` を使う

### 4) テンプレ検索/clone の安定化
- 既存の `manage_clearml_templates` の仕様と整合させる。
- “template_set + usecase_id=TabularAnalysis” をキーにしてテンプレを特定する（増殖対策）。
- テンプレが複数見つかった場合は、
  - schema_version を優先
  - template_set が一致するものを優先
  - それでも複数なら明示的にエラー（事故防止）

### 5) 子タスクの project 階層統一
- T091 で定義した project ルールを、driver のどちらでも同じ関数から取得する。
- 子タスク名には重要情報を入れる（例：train ならモデル名/略語、preprocess なら variant_id）

### 6) docs 追記
- Local/Agent の違い（“実行方式が違っても見え方が揃う”を目標）
- Agent はテンプレclone必須、Local は plan に従って逐次実行
- どこを改修すれば挙動を変えられるか（driver/plan/registryの責務分離）

## 受け入れ基準
- Agent 実行で pipeline が子タスク（preprocess/train/ensemble/leaderboard）を生成できる。
- Local 実行でも usecase tag で子タスク相当が追える。
- project 階層・タグ・hparamsカテゴリが Local/Agent で一致する（少なくとも命名とカテゴリが同じ）。

## テスト
- `python -m compileall -q src`
- Local driver で toy データを 1 preprocess + 2 models で実行し、ClearML タスクが複数作成される
- Agent driver で同条件を実行し、子タスクが作成される（Pipelinesタブ/Experimentsで確認）

---

## Update (2026-01-13)
- plan + driver 分離は未実装。template_set / code_ref 方針と合わせて Phase 2 (T101) で対応する
