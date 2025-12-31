# CODEX_GUIDE（共通ルール）

このリポジトリは **Codex CLI による自動開発**を前提にしています。
`work/tasks/*.md` の指示は必ずこのガイドに従って実行してください。

## 0. 最重要の方針（逸脱禁止）
- plan2.md に従い、**Platform と Solution を分離する**
- tabular 固有ロジックを platform に入れない
- Platform の API 依存は **src/tabular_analysis/platform_adapter.py に集約する**（直 import 禁止）
- 親子タスクを作らない：比較は leaderboard、接着は pipeline
- split は preprocess が生成し固定（train は再生成しない）

## 0.1 進捗・指示ファイルの保護（重要）
次のファイルは **Codex が編集してはいけません**（進捗が壊れたり、タスクが飛ぶ原因になります）。
- `work/queue.json`
- `work/state.json`
- `work/tasks/**`

※ runner（`tools/codex_loop/run.py`）側で変更検知し、変更されていた場合は **失敗扱い**にします。

## 0.2 途中停止・中途半端防止の原則
- 1タスク = 1目的 = 1回の verify 成功 でのみ完了（verify が通らない限り次へ進まない）
- 失敗したら「最小差分で修正」し、原因を docs/ またはコードに反映する
- 例外で握りつぶして “通す” のは禁止（後段で必ず破綻します）

## 1. 変更範囲の原則
- 各タスクは `must_change_globs` に必ず変更を含める
- 仕様・契約変更は docs/ と conf/ の対応更新を必ず含める

## 2. 「DONE」の定義
- 検証コマンド（Verification）が全て成功していること
- 追跡性（config_resolved/out/manifest）を壊していないこと
- UI 契約（docs/03）を満たす properties/tags/artifacts のログが実装されていること（対象タスク）

### runner が強制する DONE 判定
runner は次を満たした場合のみ state を `done` にします。
- `must_change_globs` に一致するファイルが “このタスクの実行で” 変更されている
- `verify` がすべて成功している
- 保護対象ファイル（0.1）が変更されていない

## 3. エラー時のふるまい
- 失敗ログを読み、原因を最小変更で修正する
- 「とりあえず try/except で握りつぶす」は禁止（doctor で検出できなくなる）

### よくある停止要因と対処
- state が `in_progress` のまま止まった: `python tools/codex_loop/run.py --repo . --reset-in-progress` を実行
- work/lock が残っている: 前回の runner が異常終了の可能性。`--force-lock` で解除して再実行
- verify が弱くて中途半端で通る: タスクの verify を強化する（本パッケージは v2 で強化済み）

## 4. 実装の型（推奨）
- 各 process は次の流れを守る
  1) ctx = platform_adapter.init_task_context(...)
  2) platform_adapter.save_config_resolved(...)
  3) core logic
  4) out.json / manifest.json / properties / artifacts

## 5. platform への要求が出た場合
- まず solution 側で代替実装（adapter の内側）
- 2 Solution 以上で共通になったら platform へ昇格（新規 P205〜）
