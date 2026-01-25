# 09_RISKS_AND_MITIGATIONS（課題と対応策）

この Solution を継続運用する上で起きやすい課題と、仕様に組み込む対応策をまとめます。

## 1. Platform API 変更で Solution が壊れる
**課題**：platform の関数名/引数変更が複数 Solution を壊す。

**対応策**
- platform は SemVer + deprecate 期間を運用
- Solution は version pin（plan2 A案）
- Solution は platform の呼び出しを `platform_adapter.py` に集約する（影響範囲を最小化）

## 2. ClearML UI の統一感が崩れて非DSが迷う
**対応策**
- Project 階層・Tags・Properties の固定キーを docs/03 で契約化
- platform の init_task を必ず利用し、Task.init の直叩きを禁止

## 3. 比較可能性が崩れて leaderboard が無意味になる
**対応策**
- split は preprocess のみが生成し、train は再生成しない
- leaderboard は `processed_dataset_id` と `split_hash` の一致チェックを必須化

## 4. grid が増えすぎて運用破綻
**対応策**
- pipeline に max_jobs/top_k/budget を持たせる
- grid_run_id を全タスクへ付与し、まとめて追えるようにする

## 5. train と infer の前処理不一致（スキュー）
**対応策**
- preprocess bundle を model_bundle に同梱
- infer は必ず model_bundle をロードし再fit禁止

## 6. Codex CLI が途中で止まる（迷走/やったつもり）
**対応策**
- work/tasks を小粒にし、各タスクに verify を必須化
- tools/codex_loop は NONCE + verification gate + must_change_globs + failure memo 注入を標準化
