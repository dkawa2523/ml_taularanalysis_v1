# T040 統合: verify_all / CI / docs 更新（新機能を運用に乗せる）

## Objective
- T029〜T039 で追加した機能を “壊れない” ように、検証導線とドキュメントを統合する
- CI は **quick** を基本にし、heavy（optional/時間がかかる）機能は full に分離して運用律速を避ける
- ClearML UI 契約（Artifacts/Properties）を更新し、増えた成果物の位置づけを明確化する

---

## Scope
### 1) verify_all 更新
- `tools/tests/verify_all.py` を更新
  - `--quick`: 既存の軽量スモーク + 最低限の新規スモーク（multiclass など）
  - `--full`: 不確かさ/CI/monitoring/serving(optional) 等を含む
- 新規テストを verify_all に登録（ただし optional dependency が必要なものは自動 skip）

### 2) CI 更新
- `.github/workflows/ci.yml` が存在する前提（T028）
  - quick を常時実行
  - full は手動/スケジュール等（必要なら）に分離
- “依存が無いと落ちる” を避ける（optional tests は skip）

### 3) docs 更新
- `docs/15_VERIFICATION.md` に T029〜の検証コマンドを追記
- `docs/03_CLEARML_UI_CONTRACT.md` に追加 artifacts（model_card, decision_summary, metrics_ci, drift_report）を追記
- `docs/19_NEXT_PHASE_FEATURES.md` を必要なら更新

### 4) tests
- `python tools/tests/verify_all.py --quick` が通ること
- （任意）`--full` はローカルで時間がかかっても良いが、CIには載せない方針でも可

---

## Acceptance Criteria
- quick/full の検証導線が明確で、CI が重くなりすぎない
- docs が更新され、運用担当が “どこを見ればよいか” 分かる
- `verify_all --quick` が通る

---

## Verification
- `python tools/tests/verify_all.py --quick`

---

## Notes / Risks
- optional dependency が増えると CI が壊れやすいので、必ず import guard と skip を徹底する
- “機能が増えたのに何を見ればいいか分からない” が運用最大の敵。docs を最小でも更新する

---

## RESULT（必ず記入）
- 変更点サマリ:
- verify 結果:
