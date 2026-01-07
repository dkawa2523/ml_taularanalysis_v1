# T020 可視化: 重要度/残差/混同行列など軽量プロット（heavyはオプトイン）

## Objective
- ClearML UI 契約（docs/03）に沿って、**軽量な可視化**をデフォルトで提供する
- heavy（SHAP 等）は **オプトイン**（デフォルトOFF）として追加余地を残す

---

## Scope
1) `src/tabular_analysis/viz/plots.py` を追加
   - `plot_feature_importance(...)`
   - `plot_regression_residuals(...)`
   - `plot_confusion_matrix(...)`
   - （必要なら）`plot_roc_curve(...)`（binaryのみから開始）
2) train_model で必要に応じて plot を生成し artifacts に出す
   - 例: `feature_importance.png`, `residuals.png`
3) leaderboard で推薦モデルに対する “代表プロット” を生成（任意）
4) config に `viz.enabled` / `viz.heavy.enabled` を追加（heavyはfalse）
5) テスト追加: `tools/tests/smoke_plots.py`
   - 回帰 or 分類の最小 run を実行し、少なくとも1枚の png が生成されることを確認

---

## Implementation Notes
- matplotlib 依存をどうするか:
  - 追加するなら base に入れるか、optional にするか判断する
  - 現場運用では “入っていないと可視化だけ落ちる” 事故があるため、軽量可視化は base 推奨
- 画像が増えすぎないよう、デフォルトは topN のみ

---

## Acceptance Criteria
- 少なくとも feature_importance.png か confusion_matrix.png のどちらかが生成される
- heavy は明示的に enabled にしない限り実行されない
- smoke_plots.py が通る

---

## Verification（runner 側で実行）
- `python tools/tests/smoke_plots.py`
