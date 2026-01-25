# T028 品質ゲート: CI（GitHub Actions）+ 運用Runbook整備

## Objective
- 業務投入前提のため、最低限の品質ゲート（CI）を用意し、main に壊れたコードが入らないようにする
- 運用担当/開発者が迷わないよう、Runbook（運用手順）を整備する

---

## Scope
1) CI 追加（GitHub Actions）
- `.github/workflows/ci.yml` を追加
- 実行内容（最小）
  - `pip install -r requirements/base.txt`
  - `pip install -e .`
  - `python tools/tests/verify_all.py --quick`

2) dev ドキュメント
- `docs/16_OPERATIONS_RUNBOOK.md` を充実（T025 で新規追加済みの想定）
- `docs/18_CONTRIBUTING.md`（新規）: 開発者向け（branch/PR/verify の手順）

3) テスト追加（CIファイルの最低検査）
- `tools/tests/smoke_ci_config.py`
  - `.github/workflows/ci.yml` が存在し、`verify_all.py --quick` を実行する記述があることを文字列で検査

---

## Acceptance Criteria
- `.github/workflows/ci.yml` が存在する
- `smoke_ci_config.py` が通る

---

## Verification（runner 側で実行）
- `python tools/tests/smoke_ci_config.py`
