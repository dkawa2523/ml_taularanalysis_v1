# T092 実行の安定化: optional deps / inapplicable を “SKIP” として正規化し、落ちない・嘘を出さない

## 背景
- 現状、モデル依存差分（optional deps）やデータ内容により適用不能な前処理がある。
- それらでタスクが落ちると、運用（非DSユーザーの機械実行）が破綻しやすい。
- ただし「落ちない」だけでは不十分で、ClearML 上で **なぜスキップされたか** が分かり、leaderboard の集計にも正しく反映される必要がある。

## ゴール
1. preprocess/train/ensemble の各タスクで、次のケースを **FAILEDではなくSKIPPED** として扱える（ローカル/Agent共通）：
   - missing_dependency（例: xgboost/lightgbm/catboost/tabpfn が入っていない）
   - inapplicable（前処理の適用対象列が無い、など）
   - insufficient_candidates（アンサンブル候補が足りない）
2. SKIP の出力を統一する：
   - out.json に `status="skipped"` と `reason` を必ず書く
   - ClearML tags に `skipped:true`, `skip_reason:<reason>` を付ける
   - artifact に `skip_reason.json` を保存（詳細はここに）
3. leaderboard は SKIP を正しく扱う（ランキングには含めない/表示だけは可など、既存方針に合わせる）。

## 非ゴール
- pipeline 全体の部分失敗ポリシー（T093）。
- Local/Agent driver の統一（T095）。

## 作業手順
### 1) 現状の out.json / artifacts / tags 仕様確認
- preprocess/train/ensemble の出力（out.json など）と、ClearML tags/properties の付け方を確認する。
- 既に似た仕組みがある場合は、それを拡張して統一する（新規実装を増やさない）。

### 2) “SKIP” の共通ヘルパを用意（最小）
- `emit_skip(task, out_path, reason, detail)` のような形で、以下を一括で行う：
  - out.json へ status/reason を書く
  - tags を付ける（clearml有効時のみ）
  - artifact（skip_reason.json）を出す（clearml有効時のみ）
- 置き場は既存の utils / platform_adapter / clearml helper に寄せる（新規ファイルを増やしすぎない）。

### 3) optional deps: registry.requires を利用して判定
- T090 で導入した `requires` を参照し、
  - importできない → SKIP（reason="missing_dependency"）
  を各 train / ensemble /（必要なら preprocess）で実行前に判定する。
- “importできない”時は例外を投げない。SKIPで静かに終える。

### 4) preprocess applicability: registry.applicability_check を利用
- データスキーマに対して applicability を評価し、
  - 不適用 → SKIP（reason="inapplicable"、detailに理由）
- ここも例外ではなくSKIPで終える。

### 5) ensemble: 候補不足で SKIP
- mean_topk/weighted/stacking いずれも、候補となる学習済みモデルが不足する場合は SKIP。
- detail に “何が足りないか（成功タスク数/必要数）” を残す。

### 6) leaderboard: SKIP の扱いを明確化
- SKIP の train/ensemble をランキング対象から除外する（ただし一覧には出せる）。
- ClearML PLOTS/SCALARS の集計が壊れないようにする（SKIPが混ざっても集計できるように）。

## 受け入れ基準
- optional deps が入っていない環境でも pipeline 実行が “途中で落ちず”、該当モデルが SKIP として記録される。
- 前処理が適用不能でも SKIP として記録され、後続が続行できる（fail_policy次第で最終結果が変わる）。
- SKIP は ClearML UI から理由が追える（tags/artifact/out.json）。

## テスト
- `python -m compileall -q src`
- （依存が無い状態を模擬して）任意のモデルを `requires` に入れて SKIP になることを確認
- toyデータで、カテゴリ列無しのデータに OHE 前処理を指定して SKIP になることを確認
