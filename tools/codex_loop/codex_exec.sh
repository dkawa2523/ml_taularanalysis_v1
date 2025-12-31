#!/usr/bin/env bash
set -euo pipefail

# Portable Codex CLI wrapper.
#
# Why this script exists:
# - Codex CLI has evolved and different installations support different flags.
# - Some environments do NOT have a "default" profile in ~/.codex/config.toml.
# - Some builds may not support convenience flags like --full-auto.
#
# This wrapper makes codex_loop resilient by:
# - Feeding PROMPT via stdin: `codex exec - < prompt.md` (no --prompt-file).
# - Treating --profile as OPTIONAL. If the requested profile is missing,
#   we automatically retry without --profile.
# - Treating --full-auto as OPTIONAL. If unsupported, we retry without it.
#
# Usage:
#   bash tools/codex_loop/codex_exec.sh <prompt_file>
#   bash tools/codex_loop/codex_exec.sh <profile> <prompt_file>
#
# Optional environment variables:
#   CODEX_PROFILE    : override profile argument
#   CODEX_MODEL      : passed as `--model <MODEL>`
#   CODEX_FULL_AUTO  : "1" (default) to include --full-auto, "0" to disable

PROFILE=""
PROMPT_FILE=""

# Parse args
if [[ $# -eq 1 ]]; then
  PROMPT_FILE="$1"
elif [[ $# -ge 2 ]]; then
  # Backward compatible: if first arg is a file, treat it as prompt_file.
  if [[ -f "$1" ]]; then
    PROMPT_FILE="$1"
  else
    PROFILE="$1"
    PROMPT_FILE="$2"
  fi
else
  echo "[codex_exec] ERROR: prompt_file is required" >&2
  echo "[codex_exec] Usage: bash tools/codex_loop/codex_exec.sh <prompt_file>" >&2
  echo "[codex_exec]    or: bash tools/codex_loop/codex_exec.sh <profile> <prompt_file>" >&2
  exit 2
fi

# Env override
if [[ -n "${CODEX_PROFILE:-}" ]]; then
  PROFILE="$CODEX_PROFILE"
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

USE_FULL_AUTO="${CODEX_FULL_AUTO:-1}"

run_codex() {
  local _profile="$1"
  local _use_full_auto="$2"
  local _stderr_file="$3"

  local -a cmd
  cmd=(codex exec)

  if [[ "${_use_full_auto}" == "1" ]]; then
    cmd+=(--full-auto)
  fi

  if [[ -n "${CODEX_MODEL:-}" ]]; then
    cmd+=(--model "$CODEX_MODEL")
  fi

  if [[ -n "${_profile}" ]]; then
    cmd+=(--profile "${_profile}")
  fi

  # Read prompt from stdin.
  cmd+=(-)

  set +e
  "${cmd[@]}" < "$PROMPT_FILE" 2> >(tee "$_stderr_file" >&2)
  local rc=$?
  set -e
  return $rc
}

# Retry loop with compatibility fallbacks.
for attempt in 1 2 3; do
  tmp_err="$(mktemp)"
  if run_codex "$PROFILE" "$USE_FULL_AUTO" "$tmp_err"; then
    rm -f "$tmp_err" || true
    exit 0
  fi
  rc=$?
  err_txt="$(cat "$tmp_err" 2>/dev/null || true)"
  rm -f "$tmp_err" || true

  # Fallback 1: profile missing
  if [[ -n "$PROFILE" ]] && echo "$err_txt" | grep -qiE "config profile.*not found"; then
    echo "[codex_exec] WARN: profile '$PROFILE' not found. Retrying without --profile." >&2
    PROFILE=""
    continue
  fi

  # Fallback 2: --full-auto unsupported
  if [[ "$USE_FULL_AUTO" == "1" ]] && echo "$err_txt" | grep -qiE "unexpected argument '--full-auto'"; then
    echo "[codex_exec] WARN: --full-auto not supported. Retrying without it." >&2
    USE_FULL_AUTO="0"
    continue
  fi

  exit $rc
done

exit 1
