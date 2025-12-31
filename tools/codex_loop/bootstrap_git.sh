#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

if [ -d .git ]; then
  echo "[bootstrap_git] .git already exists"
  exit 0
fi

git init
# Codex 実行環境で user.name/email が未設定でも commit できるようにする
git config user.email "codex@example.com"
git config user.name "codex"

git add -A
# 初回コミット（空でもOK）
git commit -m "bootstrap codex workspace" --allow-empty

echo "[bootstrap_git] initialized git repo"
