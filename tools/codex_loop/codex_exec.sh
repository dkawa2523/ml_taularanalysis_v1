#!/usr/bin/env bash
set -euo pipefail

# Codex CLI wrapper (portable)
#
# Some Codex CLI builds do NOT support a `--prompt-file` option.
# To stay compatible across builds (and avoid command length limits),
# we feed the prompt file via stdin using `codex exec ... -`.
#
# Usage:
#   bash tools/codex_loop/codex_exec.sh <profile> <prompt_file>

PROFILE=${1:-default}
PROMPT_FILE=${2:-}

if [[ -z "$PROMPT_FILE" ]]; then
  echo "[codex_exec] ERROR: prompt_file is required" >&2
  echo "[codex_exec] Usage: bash tools/codex_loop/codex_exec.sh <profile> <prompt_file>" >&2
  exit 2
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "[codex_exec] ERROR: prompt_file not found: $PROMPT_FILE" >&2
  exit 2
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "[codex_exec] ERROR: codex command not found in PATH" >&2
  echo "[codex_exec] Hint: install Codex CLI, or adjust PATH." >&2
  exit 127
fi

# Feed the prompt via stdin.
#
# Codex CLI supports using `-` as the PROMPT argument to read from stdin.
# This avoids OS command-length limits and any quoting issues.
#
# Reference: Codex CLI `codex exec` accepts PROMPT as "string | - (read stdin)".
exec codex exec --profile "$PROFILE" - < "$PROMPT_FILE"
