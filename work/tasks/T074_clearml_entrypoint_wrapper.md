# T074 ClearML Agent 実行で src/ レイアウトを import 可能にする（entrypoint wrapper 追加）

## 背景
このリポジトリは `src/` レイアウト（`src/tabular_analysis/...`）です。
ClearML Agent は通常 repo root を working_dir にして `python -m tabular_analysis.cli ...` を実行しますが、
このままだと `tabular_analysis` が import できず失敗します。

T073 で repository/branch を solution repo に直しても、この問題が残るため、
Agent 実行時に **確実に import 可能**にする wrapper を導入します。

---

## 目的
- Agent で `tabular_analysis` を import できる
- `conf/` の検出も壊さない

---

## 実装方針
- repo root に `tools/clearml_entrypoint.py` を追加
- この wrapper は以下を行う:
  1) repo root を特定（`conf/` の存在で判定）
  2) `repo_root/src` を `sys.path` に追加（PYTHONPATH 相当）
  3) `TABULAR_ANALYSIS_CONFIG_DIR` を `repo_root/conf` に設定（未設定時のみ）
  4) `tabular_analysis.cli` を import して `main(argv)` を呼ぶ

---

## 変更内容
### 1) 新規ファイル
`tools/clearml_entrypoint.py` を追加（実行可能であること）

### 2) platform_adapter の Script entry_point の更新
T073 で修正した `Task.set_script(...)` の箇所で、Agent 実行系（少なくとも pipeline_controller / agent 実行）では
entry_point を `-m tabular_analysis.cli ...` ではなく、

- `tools/clearml_entrypoint.py <元のHydra引数...>`

に変更する（working_dir は repo root のままで良い）。

---

## 受け入れ基準
- `python tools/clearml_entrypoint.py --help` がエラーにならない（HydraのhelpでもOK）
- Agent 実行で `ModuleNotFoundError: tabular_analysis` が起きない
- `python -m compileall -q src` が通る

---

## テスト
- `python -m compileall -q src`
- `python tools/clearml_entrypoint.py --help`
