# T035 意思決定支援: Model Card / Decision Summary の標準化（ClearML運用を壊さない）

## Objective
- 非DSでも “採用判断” ができるように、train/leaderboard の成果物として **Model Card / Decision Summary** を標準出力する
- 出力の増殖を避け、**Markdown 2枚 + JSON 1枚**程度に抑える
- ClearML UI 契約に沿い、Artifacts から迷わず辿れる構成にする

---

## Scope
### 1) train_model: model_card.md
- `outputs/<...>/model_card.md` を出力し artifact 化
- 章立て（例）
  - Dataset / split hash / schema version
  - Preprocess（encoding含む）/ recipe hash
  - Model / hyperparams / seed
  - Metrics（点推定 + CIがあればCI）
  - Calibration / thresholding / uncertainty（有効時のみ）
  - Limitations（データリーク注意、対象外ケースなど短く）

### 2) leaderboard: decision_summary.md (+ optional json)
- 推奨モデルの根拠を 1ページでまとめる
  - top-N 一覧（leaderboard.csvへのリンク/抜粋）
  - comparable 条件（split/metric など）
  - 推奨モデルの metrics / CI / 追加機能（校正/区間/不均衡）要約
  - promote 手順への導線（promote_model のコマンド例）

### 3) ClearMLノイズ制御
- Markdown を “Artifacts” にアップロード（Plotsの乱用はしない）
- Properties は増やしすぎない（既存キー + 数個）

### 4) tests
- `tools/tests/smoke_decision_summary.py`
  - train_model と leaderboard を通し
  - `model_card.md` と `decision_summary.md` が存在することを検証

---

## Acceptance Criteria
- model_card.md / decision_summary.md が生成される
- ClearML 連携時もArtifactsにアップロードされる（ローカルでもファイルが残る）
- `smoke_decision_summary.py` が通る

---

## Verification
- `python -m compileall -q src`
- `python tools/tests/smoke_decision_summary.py`

---

## Notes / Risks
- Markdown は長くしすぎない（1〜2画面程度）。詳細は別JSONに逃がす
- 既存の summary.md と役割が被らないよう “意思決定に必要な要点” に絞る

---

## RESULT（必ず記入）
- 変更点サマリ:
- 追加/変更した出力ファイル:
- verify 結果:
