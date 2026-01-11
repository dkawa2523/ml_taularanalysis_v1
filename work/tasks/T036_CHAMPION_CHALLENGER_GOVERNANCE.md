# T036 ガバナンス: champion-challenger（promote/rollback を“運用で使える”形に）

## Objective
- T025 の promote_model を “業務運用で使える” 形に拡張する
  - staging / production のステージ管理
  - champion（現行採用モデル）の記録
  - rollback（前の champion に戻す）
- platform 改修を避け、solution 側で完結させる（必要なら docs に platform 昇格候補を記載）

---

## Scope
### 1) config / CLI I/F
- `task=promote_model` の引数を拡張（yaml/cli）
  - `promote.stage: staging | production`（default: production）
  - `promote.set_champion: true|false`（default true）
  - `promote.rollback: true|false`（default false）  ※ rollback時は target を “前の champion” にする
- “champion registry” を solution 内の固定パスに保存
  - 例: `work/registry/champions.json`（git ignore 推奨）
  - usecase_id ごとに現在 champion を保持（train_task_id / model_id / metric など）

### 2) promote_model 実装
- promote するとき:
  - `champions.json` を更新
  - `promotion.json` を出力（既存互換）
- rollback するとき:
  - champions.json の履歴（最低2世代）から戻す
  - 何を戻したかを promotion.json に記録
- ClearML 有効時:
  - Model/Task に stage/champion 情報を tags/properties に反映（可能な範囲）
  - ただし “APIが無い/権限が無い” 場合は落とさず warn + local registry だけ更新

### 3) tests
- `tools/tests/smoke_champion_registry.py`
  - ダミーの promote を2回行い champion が更新されること
  - rollback で前の champion に戻ること
  - ファイルフォーマット（JSON）が壊れないこと

---

## Acceptance Criteria
- promote と rollback がローカルで再現できる（ClearML無しでも）
- champion registry が壊れない
- `smoke_champion_registry.py` が通る

---

## Verification
- `python -m compileall -q src`
- `python tools/tests/smoke_champion_registry.py`

---

## Notes / Risks
- champions.json は “単一ファイル” なので並行実行時の競合に注意（将来は platform へ昇格候補）
- ClearML Model Registry は環境依存が大きいので “best effort” に留める

---

## RESULT（必ず記入）
- 変更点サマリ:
- 新規ファイル/出力:
- verify 結果:
