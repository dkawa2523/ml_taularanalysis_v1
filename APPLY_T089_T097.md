# 追加タスク（T089〜T097）適用手順

このZIPは **ml-solution-tabular-analysis リポジトリに “追記” するための Codex CLI 指示ファイル群**です。  
（既存のコードは含まず、work/tasks と queue 追記のみを提供します）

## 1) 配置（展開）
1. `ml-solution-tabular-analysis` のリポジトリルートへ移動
2. このZIPを **リポジトリルートに展開**してください（`work/` が既にある前提で上書き/追記）

展開後に以下が存在することを確認：
- `work/tasks/T089_pipeline_v2_config_schema.md` 〜 `T097_docs_ops_rules_and_extension_guide.md`
- `work/queue_additions_T089_T097_v1.json`

## 2) work/queue.json への追記（jq不要）
`work/queue.json` に tasks を追加します。  
※ `queue_additions_*.json` は **参考用**で、そのままでは codex_loop から読み込まれません。

### 追記（Pythonワンライナー）
```bash
python - <<'PY'
import json
from pathlib import Path

repo = Path(".")
queue_path = repo/"work/queue.json"
adds_path = repo/"work/queue_additions_T089_T097_v1.json"

queue = json.loads(queue_path.read_text(encoding="utf-8"))
adds = json.loads(adds_path.read_text(encoding="utf-8"))["append_tasks"]

# queue.json のトップレベルが {"tasks":[...]} である想定
if "tasks" not in queue or not isinstance(queue["tasks"], list):
    raise SystemExit("ERROR: work/queue.json の形式が想定と違います。手動で tasks 配列へ追記してください。")

existing = {t.get("id") for t in queue["tasks"]}
for t in adds:
    if t["id"] in existing:
        print("[skip] already exists:", t["id"])
    else:
        queue["tasks"].append(t)
        print("[add] ", t["id"], t["title"])

queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
print("updated:", queue_path)
PY
```

## 3) 実行（T089 から順に）
### 状態確認
```bash
python tools/codex_loop/run.py --repo . --status
```

### 1タスクずつ実行（推奨）
```bash
python tools/codex_loop/run.py --repo . --once
```

T089 → T090 → … の順に進む想定です。

### まとめて実行（任意）
```bash
python tools/codex_loop/run.py --repo . --until T097
```

## 4) 実装後の検証（概要）
T096 で Python rehearsal runner が追加される想定なので、T096完了後に docs の手順に従って実行してください。  
（runner 名はタスク内で確定します）

## 5) うまく進まない時
- `work/last_failure.md` と `work/runs/<timestamp>_Txxx/` のログを確認
- `must_change_globs` で止まる場合：
  - そのタスクで実際に変更されたファイルが globs に含まれているか確認
  - 必要なら `work/queue.json` の該当タスクの `must_change_globs` を調整して再実行
