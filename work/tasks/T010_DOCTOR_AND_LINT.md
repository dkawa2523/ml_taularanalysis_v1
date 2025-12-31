# T010 doctor/contract lint: 実行前検査 + UI契約チェック

## Objective
- Codex 開発中・運用前に「環境が壊れていないか」を検査できる doctor を実装する
- ClearML UI 契約（docs/03）の必須項目が揃っているか、ローカル run_dir を対象に lint できるようにする

## Scope
- `src/tabular_analysis/doctor.py` に実装（CLI でも呼べる）

## Checks（推奨）
1. platform
   - `import ml_platform` できるか
   - platform version を取得できるか
2. clearml（enabled=true の時のみ）
   - Task.init ができるか（接続テスト）
3. solution structure
   - `conf/` が見つかるか
4. contract lint（run_dir 指定時）
   - config_resolved.yaml / out.json / manifest.json の存在
   - out.json の必須キー（process 依存）

## Acceptance Criteria
- `python -m tabular_analysis.doctor` が 0 で終了する（clearml 無効時）
- `python -m tabular_analysis.doctor --lint-dir outputs/<...>/03_train_model` のように run_dir lint ができる

## Verification
```bash
python -m tabular_analysis.doctor || true
```
