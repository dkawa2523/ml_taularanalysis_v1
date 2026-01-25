# T047 Reproducible Runtime（環境スナップショットと依存固定の土台）

## Objective
- 業務投入で必須の「再現性」を強化する
  - 実行環境（Python/OS/主要依存）のスナップショットを全タスクで残す
  - lockfile 運用の導線を用意（強制はしない）
- ClearML 有効時は artifact としてもアップロードし、UIから追跡できるようにする

---

## Scope
### 1) env snapshot の実装
- `src/tabular_analysis/ops/env_snapshot.py` を追加
  - `capture_env_snapshot(output_dir) -> (env.json, pip_freeze.txt)`
  - 内容：
    - python version / platform
    - pip freeze（大量でも artifact ならOK）
    - solution version（git hash が取れれば）
- 各プロセスの共通初期化で呼ぶ（重複を避ける）

### 2) lockfile の運用導線
- `uv.lock` を正とし、`docs/26_REPRODUCIBLE_RUNTIME.md` に更新手順を記載
  - 依存が増えたときに `uv lock` を更新する
- pip-only 環境向けの `requirements/lock.txt` は任意（必要なら手動生成）
- 既存 requirements 構成（base/optional）を壊さない

### 3) verify
- ローカル実行で env snapshot が出ることをテストで確認

---

## Acceptance Criteria
- 代表タスク実行後に `env.json` と `pip_freeze.txt` が出力される
- ClearML 無効でも出力される（artifact upload は no-op）
- docs が整備されている

---

## Verification
```bash
python -m compileall -q src
python tools/tests/test_env_snapshot.py
```
