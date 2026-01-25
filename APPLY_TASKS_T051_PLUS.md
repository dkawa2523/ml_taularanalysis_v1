# T051〜T055 適用・実行ガイド（試験段階 / ClearML運用を固定しない）

このZIPは **T050まで完了した `ml-solution-tabular-analysis`** に対して、試験段階向けの追加タスク **T051〜T055** を “上乗せ” するための指示ファイル群です。

目的：
- **ClearML運用（命名・タグ・Properties・テンプレ運用など）を固定せず**に試験できるよう、設定の“差し替え容易性”を高める
- ローカルClearML → 社内ClearMLへ移行する際の **リハーサル手順**と**検証観点**を整備する
- 本番運用の検討事項は **docs/Issue形式**で残し、後で設計判断・改修しやすくする

---

## 1) 適用（既存repoへ上書きコピー）

`ml-solution-tabular-analysis/` が存在する **親ディレクトリ**で unzip してください。

```bash
cd <workspace>
unzip -o ml_solution_tabular_analysis_codex_tasks_T051_T055_v1.zip -d .
```

反映確認：

```bash
ls -la ml-solution-tabular-analysis/work/tasks | grep T051
ls -la ml-solution-tabular-analysis/docs | grep 40_CLEARML_TEST_PHASE_POLICY
```

---

## 2) queue.json への追加

このZIPは **追加分**として `work/queue_additions_T051_T055.json` を同梱しています。

### 推奨：マージスクリプトで追記

```bash
cd <workspace>/ml-solution-tabular-analysis
python tools/codex_loop/merge_queue_additions.py \
  --queue work/queue.json \
  --add work/queue_additions_T051_T055.json
```

> もし既存repoに `merge_queue_additions.py` が無い場合は、このZIP内の `tools/codex_loop/merge_queue_additions.py` を上書きコピーしてください。

---

## 3) Codex CLI 実行（T051から開始）

```bash
cd <workspace>/ml-solution-tabular-analysis

# 次に実行されるタスクの確認
python tools/codex_loop/run.py --repo . --status

# 1タスクだけ進める（推奨）
python tools/codex_loop/run.py --repo . --once

# 連続実行
python tools/codex_loop/run.py --repo .
```

トラブル時：

```bash
# in_progress のまま止まった
python tools/codex_loop/run.py --repo . --reset-in-progress

# lock が残っている（異常終了など）
python tools/codex_loop/run.py --repo . --force-lock --once
```

---

## 4) 試験段階のリハーサル（人が実行する想定）

T053/T055 で **ローカルClearML→社内ClearML** の試験手順を整備します。

まずは docs を読み、実施の順番を確認してください：

- `docs/42_REHEARSAL_SCENARIOS.md`
- `docs/40_CLEARML_TEST_PHASE_POLICY.md`

---

## 5) 何が追加される？（概要）

- **T051**：命名・タグ・properties を “複数ポリシーで試験”できる設定スイッチ（yaml）とコードの分離
- **T052**：ClearML運用検討を Issue（md）で残す仕組み（候補案の比較表 + 決定ログ）
- **T053**：試験用リハーサル（ローカルClearML / ロギングモード）用の手順・スクリプト整備
- **T054**：テンプレTask（UI clone）運用を見据えた docs と “テンプレ作成チェックリスト”
- **T055**：社内ClearMLへ移行する前提のリハーサル計画（差分の観点、微調整ポイント）
