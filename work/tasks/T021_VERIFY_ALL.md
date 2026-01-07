# T021 検証統合: verify_all.py（ローカルで1コマンド検証）

## Objective
- T020 までで増えたスモークテスト群を **1コマンド**で回せるようにし、検証手順の属人化を防ぐ
- Codex 開発の verify を強化し、「中途半端に通って次タスクに進む」を減らす

---

## Scope
1) `tools/tests/verify_all.py` を追加
   - `--quick` と `--full` を用意
   - **quick** は "日常開発/CI" 向け（短時間）
   - **full** は "リリース前" 向け（やや長い）

2) quick の内容（最低限）
- `python -m compileall -q src`
- `python tools/tests/smoke_local.py --until pipeline`
- `python tools/tests/smoke_classification.py --until leaderboard`
- `python tools/tests/check_optional_models.py --models lgbm,xgboost,catboost,tabpfn`
- `python tools/tests/smoke_hpo.py`
- `python tools/tests/smoke_report.py`
- `python tools/tests/smoke_plots.py`

3) full の内容（目安）
- quick + 以下を追加（存在する場合のみ実行）
  - `tools/tests/smoke_train_regression_model.py`（少数モデル）
  - 重いモデルの学習は原則含めない（build-only は OK）

4) ドキュメント更新
- `docs/15_VERIFICATION.md` に verify_all を追記
- README の "開発者向け" セクションに verify_all を追記（短く）

5)（任意）Makefile
- `make verify` が `python tools/tests/verify_all.py --quick` を呼ぶ

---

## Implementation Notes
- `subprocess.run` で順に実行し、失敗した時点で非ゼロ終了にする
- `--repo` オプションを用意して、どこから呼んでも repo root を基準に実行できるようにする
- 実行コマンドと stdout/stderr を簡潔に表示（CI で追える程度）

---

## Acceptance Criteria
- `python tools/tests/verify_all.py --quick` が 0 で終了する
- `docs/15_VERIFICATION.md` と README に利用方法が書かれている

---

## Verification（runner 側で実行）
- `python tools/tests/verify_all.py --quick`
