# T089 Pipeline v2: 設定スキーマ（profile + groups + policy）を導入し、Hydra strict を落とさない

## 背景
- 現状の pipeline は `pipeline.grid.*` を中心に動いているが、将来的な処理グループ増加（次元削減/特徴量生成など）や運用の柔軟性を考えると、pipeline 設定を「グループ単位で none/default/custom を選べる」形に寄せたい。
- ただし設定拡張で Hydra strict が落ちやすい（未定義キー上書き）ため、まず **スキーマ（キー定義）を conf に追加**して strict でも安全にする。

- 重要：将来的に処理/モデルが増えても **pipelineテンプレートタスクが増殖しない** ことを狙う（=選択は pipeline の Hyperparameters で行う）。
- 本タスクでは「実行ロジックの大改修」はしない。**設定の受け皿を先に用意**し、後続タスクで段階的に pipeline を v2 解釈へ切り替える。

## ゴール
1. `pipeline.profile`（default/custom）と `pipeline.groups.*`（none/default/custom）などの v2 キーを **conf 側で定義**し、Hydra strict でも未定義キーエラーが出ない。
2. 追加で必要な運用ポリシーキーも同時に定義する（後続で実装する）  
   - `pipeline.fail_policy.*`（部分失敗許容）
   - `pipeline.limits.*`（タスク数爆発抑止）
   - `pipeline.parallelism.*`（並列上限）
3. 既存の `pipeline.grid.*` は **後方互換のため残す**（削除しない）。
4. ClearML Hyperparameters のカテゴリ設計（inputs/dataset/eval/pipeline/clearml）を **v2 で崩さない**土台を作る。

## 非ゴール
- pipeline 実行が v2 へ完全移行すること（それは T091 以降）。
- registry や skip の実装（T090/T092 以降）。

## 作業手順
### 1) 既存 config の実態確認（必須）
- `conf/run/base.yaml` / `conf/pipeline*.yaml` / `conf/config.yaml`（または Hydra defaults）を確認し、
  - 現在定義されている `pipeline` キー
  - strict 設定（`hydra.strict` 相当）がどこで有効化されているか
  を把握する。

### 2) pipeline v2 スキーマの追加（conf）
以下のいずれかの最小変更でよい（既存設計に合わせて選ぶ）：
- 方式A: `conf/pipeline/v2.yaml` を追加し、`conf/pipeline.yaml`（または defaults）から参照する
- 方式B: 既存 `conf/pipeline.yaml` に v2 のキーを追記する（ファイル増を避けたい場合はこちら推奨）

**必須で定義するキー**
- `pipeline.profile: default`
- `pipeline.groups.preprocess.mode: default`
- `pipeline.groups.train.mode: default`
- `pipeline.groups.ensemble.mode: default`
- `pipeline.groups.leaderboard.mode: default`
- `pipeline.groups.<group>.custom.base: default`
- `pipeline.groups.<group>.custom.include: []`
- `pipeline.groups.<group>.custom.exclude: []`
- `pipeline.groups.preprocess.custom.on_inapplicable: skip`
- `pipeline.groups.train.custom.on_missing_dependency: skip`
- `pipeline.groups.ensemble.custom.on_insufficient_candidates: skip`

**運用ポリシー（後続で実装するがキーはここで定義）**
- `pipeline.fail_policy.allow_skipped: true`
- `pipeline.fail_policy.allowed_failures: 0`
- `pipeline.fail_policy.fail_fast: false`
- `pipeline.fail_policy.min_successful_train_tasks: 1`
- `pipeline.limits.max_preprocess_variants: 3`
- `pipeline.limits.max_train_tasks: 30`
- `pipeline.limits.max_ensemble_tasks: 10`
- `pipeline.parallelism.max_concurrent_steps: 4`
- `pipeline.parallelism.max_concurrent_train: 4`

### 3) 既存 grid 設定との共存を明確化（コメントでOK）
- `pipeline.grid.preprocess_variants` / `pipeline.grid.model_variants` は残す。
- v2 へ移行するまでは現行ロジックが grid を使うはずなので、
  - v2 のキーは「現行に影響しない（まだ参照されない）」ことをコメントで明記する。
- 後続で `pipeline.profile=custom` の時のみ v2 解釈を有効化する想定をコメントに残す。

### 4) docs に “スキーマ追加” をメモ（最小でOK）
- 既存 docs に追記 or 新規 1ファイル追加のどちらでも良いが、ファイル増を避けるため既存 doc（運用系）への追記が望ましい。
- 「T089ではスキーマのみ、実行はまだ切り替わらない」を明記。

## 受け入れ基準（Acceptance）
- strict 環境で、以下のような上書きがエラーにならない  
  - `pipeline.profile=custom`
  - `pipeline.groups.preprocess.mode=custom`
  - `pipeline.fail_policy.allowed_failures=2`
- 既存の pipeline 実行（grid方式）が壊れない（少なくとも起動まで到達）。

## テスト
- `python -m compileall -q src`
- `python -m tabular_analysis.doctor`（存在するなら）
- 既存の最小 pipeline dry-run/起動コマンドを1つ（プロジェクト既定の手順に合わせる）

---

## Update (2026-01-13)
- pipeline v2 スキーマは未導入のため、Phase 2 (T101) で conf 追加から着手
