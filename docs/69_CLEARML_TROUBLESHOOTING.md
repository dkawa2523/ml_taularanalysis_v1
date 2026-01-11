# 69_CLEARML_TROUBLESHOOTING（試験段階の手順と詰まりどころ）

## 目的
ClearML + PipelineController 運用で「古いテンプレ」「古い queue」「commit pin の罠」による失敗を避ける。

## 試験段階の推奨手順（テンプレ作成 → clone → enqueue → agent）
1. テンプレ作成/更新
   ```bash
   python -m tabular_analysis.ops.manage_clearml_templates --apply
   ```
2. テンプレ検証
   ```bash
   python -m tabular_analysis.ops.manage_clearml_templates --validate
   ```
3. Clone（UI）
   - ClearML UI で template task を開いて Clone
   - 変更するのは overrides のみ（entry_point/repo/branch はテンプレ固定）
4. Enqueue（UI）
   - Queue を選び enqueue
5. Agent 実行
   - 対象 queue を監視する agent を起動

## 診断コマンド（非破壊）
テンプレの有効/無効と queue 内の不一致タスクを確認します。
```bash
python -m tabular_analysis.ops.clearml_diagnose --queue default
```

## 詰まりどころ（重要）
### 1) queue に古い task が残る
コードを直しても、queue に残っている task は **そのまま失敗し続ける**。
- 例: repository が platform repo のまま
- 対処: UI で該当 task を queue から remove

### 2) commit pin の罠
template task に `version_num` が pin されると、存在しない commit で checkout が失敗する。
- 試験段階は `run.clearml.code_version_mode=branch_head` 推奨
- 本番で pin する場合は `pin_commit` に切り替える

### 3) entry_point の統一
remote 実行タスクは `tools/clearml_entrypoint.py` を使う。
- `-m tabular_analysis.cli` を直接指定しない

## 最小確認スクリプト
```bash
python tools/tests/clearml_pipeline_probe.py --dataset-path /path/to/data.csv --target-column target --queue default
```
pipeline task の repository/branch/entry_point/version_num を表示し、受け入れ条件を確認できます。
