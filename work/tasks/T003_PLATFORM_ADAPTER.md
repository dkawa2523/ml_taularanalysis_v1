# T003 Platform 連携: platform_adapter を P201〜P204 に合わせて完成

## Objective
- `src/tabular_analysis/platform_adapter.py` を、あなたが改良した `dkawa2523/ml_platform_v1`（P201〜P204）に合わせて完成させる
- Solution の各プロセスが **platform の恩恵**（ClearML init_task拡張 / manifest/hashes/out writer）を安定して利用できるようにする

## Context
- platform API 名は変わり得るため、Solution 側は adapter に閉じ込める
- plan2 の基本方針：共通化は platform、用途固有は solution

## Instructions
1. platform API の実体調査
   - `python tools/codex_loop/platform_scan.py` を実行して `work/platform_api_summary.txt` を生成
   - summary を見て、P201〜P204 で追加された関数（init_task/manifest/hashes/out）がどのモジュールにあるか特定する

2. adapter の更新
   - `init_task_context()` が platform の init_task を正しく呼べるようにする
   - 可能なら `save_config_resolved / write_out_json / write_manifest` も platform の writer を使用する（存在する場合）
   - properties/tags の標準キーを docs/03 の契約に合わせて自動付与する
     - usecase_id, process, schema_version, code_version, platform_version, grid_run_id

3. フォールバック方針
   - clearml 無効（local）の場合は現在の実装のまま noop で良い
   - clearml 有効なのに platform API が見つからない場合は **明示的に例外**を出す（握りつぶさない）

4. docs 更新
   - `docs/13_PLATFORM_INTEGRATION.md` に「実際に接続した API パス」と「期待する入力/出力」を追記する

## Acceptance Criteria
- `platform_scan.py` が実行でき、summary が生成される
- `import tabular_analysis.platform_adapter` が成功する
- clearml 無効（run.clearml.enabled=false）で `init_task_context()` が task=None の context を返す

## Verification
```bash
python tools/codex_loop/platform_scan.py > work/platform_api_summary.txt || true
python -c "import tabular_analysis.platform_adapter as a; print('ok')"
```
