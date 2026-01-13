# T075 ClearML Agent で Hydra の list override が “分割”されないよう entry_point を正規化

## 背景
ClearML Task の Script entry_point に

`pipeline.grid.model_variants=["catboost", "elasticnet", ...]`

のような “スペースを含む JSON 文字列” が入ると、Agent 側で CLI 引数が分割されて
Hydra override が壊れます（`[catboost,` と `elasticnet,` が別トークンになる等）。

---

## 目的
- Agent が実行する entry_point が常に “安全な1トークン” の override 形式になる
- 特に `pipeline.grid.preprocess_variants` / `pipeline.grid.model_variants` を壊さない

---

## 実装方針
- `Task.set_script(entry_point=...)` を上書きするタイミングで、entry_point を **cfg から再生成**する
  - raw `sys.argv` をそのまま保存しない
- list は Hydra list 形式に統一する:
  - `[a,b,c]`（スペース無し、クォート無し）
- `pipeline.grid.*` が list でなく string の場合も想定し、JSON 文字列なら parse して list にする（防御的）

---

## 変更内容（例）
`src/tabular_analysis/platform_adapter.py` に helper を追加:

- `def hydra_list(values: list[str]) -> str:`
  - return `"[" + ",".join(values) + "]"`

そして pipeline controller の script entry_point 生成で:

- `pipeline.grid.preprocess_variants=<hydra_list(...)>`
- `pipeline.grid.model_variants=<hydra_list(...)>`

にする。

---

## 受け入れ基準
- 新しく作成する pipeline task の Script entry_point に
  - `pipeline.grid.model_variants=[catboost,elasticnet,...]`
  - `pipeline.grid.preprocess_variants=[stdscaler_ohe]`
  のような形式で入る
- Agent ログで `'pipeline.grid.model_variants=[catboost,' elasticnet, ...` のような分割が起きない
- `python -m compileall -q src` が通る

---

## テスト
- `python -m compileall -q src`
- （任意）ClearMLで新しく pipeline を起動し、Task.get_script() を確認
