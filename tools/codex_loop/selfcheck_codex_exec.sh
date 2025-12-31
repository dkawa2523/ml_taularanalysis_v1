#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
RUNTIME_JSON="$ROOT_DIR/tools/codex_loop/runtime.json"
TEMPLATE_JSON="$ROOT_DIR/tools/codex_loop/runtime.json.template"

if [ ! -f "$RUNTIME_JSON" ]; then
  cp "$TEMPLATE_JSON" "$RUNTIME_JSON"
  echo "[codex_loop] Created runtime.json from template: $RUNTIME_JSON"
fi

echo "[codex_loop] runtime.json:" 
cat "$RUNTIME_JSON"

echo ""
echo "[codex_loop] NOTE: Codex CLI の起動方法は環境差があるため、必要なら runtime.json の cmd/args を編集してください。"
echo "[codex_loop]      run.py は {prompt} / {prompt_file} / {repo} を置換して呼び出します。"

# best-effort check
RUNTIME_CMD0=$(python - <<'PY'
import json, pathlib
p=pathlib.Path("tools/codex_loop/runtime.json")
obj=json.loads(p.read_text(encoding="utf-8"))
cmd=obj.get("cmd", [])
print(cmd[0] if cmd else "")
PY
)

RUNTIME_CMD1=$(python - <<'PY'
import json, pathlib
p=pathlib.Path("tools/codex_loop/runtime.json")
obj=json.loads(p.read_text(encoding="utf-8"))
cmd=obj.get("cmd", [])
print(cmd[1] if len(cmd)>1 else "")
PY
)

if [[ "$RUNTIME_CMD0" == "bash" && "$RUNTIME_CMD1" == *"codex_exec.sh"* ]]; then
  echo "[codex_loop] runtime.json uses wrapper: $RUNTIME_CMD0 $RUNTIME_CMD1"
  if command -v codex >/dev/null 2>&1; then
    echo "[codex_loop] OK: codex command found: $(command -v codex)"
    echo ""
    echo "[codex_loop] codex exec --help (first 30 lines):"
    set +e
    codex exec --help 2>&1 | head -n 30 || true
    set -e
  else
    echo "[codex_loop] WARN: codex command not found in PATH"
    echo "[codex_loop]       -> Codex CLI をインストールしてください。"
  fi
else
  CMD="$RUNTIME_CMD0"
  if command -v "$CMD" >/dev/null 2>&1; then
    echo "[codex_loop] OK: command found: $CMD"
    echo ""
    echo "[codex_loop] $CMD exec --help (first 30 lines):"
    set +e
    "$CMD" exec --help 2>&1 | head -n 30 || true
    set -e
  else
    echo "[codex_loop] WARN: command not found: $CMD"
    echo "[codex_loop]       -> runtime.json をあなたの環境に合わせて修正してください。"
  fi
fi
