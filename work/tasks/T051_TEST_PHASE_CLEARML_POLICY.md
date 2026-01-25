# T051 試験段階: ClearML命名/タグ/Propertiesのポリシーをyamlで切替可能にする

## Objective

試験段階では、ClearML運用ルール（プロジェクト命名・usecase_id命名・tags/properties）を**固定しない**。
しかし後で本番仕様を決めやすいように、運用設計をコードから分離し、**yamlのポリシー差し替え**で試せる状態にする。

具体的には：
- `usecase_id` の自動生成ルール（例：`test_<datasetid>_<timestamp>`）を**選択式**に
- 上位プロジェクトはユーザーが決める想定で、下位は `TabularAnalysis/<usecase_id>/...` をテンプレ化
- tags/properties は “最小セット” を基本とし、候補案を切り替えられる

## Constraints

- ml-platform は変更しない（platform_adapter 経由で接続し、Solution側で吸収）
- ClearMLの設定は「試験段階で複数仕様を試す」ため、**デフォルトは保守的**に（情報量増やさない）
- 既存のUI契約（manifest/out/configのArtifacts）を壊さない

## Implementation Outline

1) `conf/ops/clearml_policy/` を追加
   - `test_minimal.yaml`：最小tags/properties
   - `test_richer.yaml`：検索性を上げるがノイズ増（試験用）

2) `conf/ops/usecase_id_policy/` を追加
   - `test_dataset_timestamp.yaml`：`test_<datasetid>_<timestamp>`
   - `explicit.yaml`：必ず user が指定（自動生成しない）

3) `src/tabular_analysis/ops/clearml_identity.py` を追加
   - 入力：hydra config（run.*）
   - 出力：
     - `project_root`（上位は環境変数/設定から）
     - `usecase_id`（指定が無ければポリシーから生成）
     - `tags`（最小セット）
     - `user_properties`（最小セット）
   - 注意：Propertiesに詰め込みすぎない（詳細は artifact へ）

4) 各プロセスの Task init の直前で identity を確定させ、platform_adapter に渡す
   - project名の組み立て：`<ROOT>/TabularAnalysis/<usecase_id>/<stage>`
   - stage は既存のプロセス命名を踏襲

5) CLIに “dry-run 表示” を追加
   - `python -m tabular_analysis.ops.print_clearml_identity --config ...` のように
     「この設定だと project/tags/properties はこうなる」を表示できるようにする
   - 試験段階で仕様比較がしやすくなる

## Acceptance Criteria

- `run.usecase_id` を指定しない場合でも、`usecase_id_policy` に従い自動生成される
- 2つ以上のポリシー（minimal/richer）が yaml で切り替えられる
- `print_clearml_identity` が、選択中のポリシーに基づく結果を表示する
- 既存の `tools/tests/smoke_local.py` が引き続き通る（ClearML無効でも）

## Verification

```bash
python -m compileall -q src

# ヘルプが出る
python -m tabular_analysis.ops.print_clearml_identity --help

# 既存スモークが落ちない（ClearML無効）
python tools/tests/smoke_local.py --until pipeline
```

---

## Update (2026-01-13)
- `test_minimal` / `test_richer` に `solution:tabular-analysis` を追加し、UI チェックリストの前提に合わせた

## Notes for Codex

- DONE条件：verificationが全て成功し、`RESULT: DONE (nonce: <nonce>)` を末尾に記載すること。
- 変更対象外：`work/queue.json`, `work/tasks/**` は変更しない（保護対象）。

## RESULT

<!-- Codex fills: RESULT: DONE (nonce: ...) + changed files + verification output -->
