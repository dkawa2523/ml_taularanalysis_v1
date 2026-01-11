# T011〜T020 Codex Tasks 適用手順（ml-solution-tabular-analysis）

この ZIP は、`ml_solution_tabular_analysis_codex_scaffold_v6.zip`（T010完了済み）に **追記する形**で、
Codex CLI 開発用の指示ファイル（queue/tasks/docs）を追加します。

## 1) 適用（上書き配置）
あなたの作業ディレクトリ（例: `ml-solution-tabular-analysis/`）の **リポジトリ直下**で実行してください。

```bash
# 例: repo 直下で
unzip -o ml_solution_tabular_analysis_codex_tasks_T011_T020_v1.zip -d .
```

適用後に増える/更新される主なファイル:
- `work/queue.json`（T011〜T020 追加）
- `work/tasks/T011_*.md`〜`T020_*.md`（新規）
- `docs/14_MODEL_CATALOG.md`（新規）

> NOTE: `work/state.json` は runner が自動更新します（手で編集しない）

## 2) 実行（Codex loop）
T010 が done の状態で、次から続けて実行します。

```bash
python tools/codex_loop/run.py --repo . --once
# 連続で進めるなら
python tools/codex_loop/run.py --repo .
```

途中で止まった場合:
```bash
python tools/codex_loop/run.py --repo . --reset-in-progress
```

## 3) optional models の導入（必要な場合だけ）
GBDT 系（LightGBM/XGBoost/CatBoost）:
```bash
pip install -e ".[models]"
```

TabPFN:
```bash
pip install -e ".[tabpfn]"
```

> optional が無い環境でもテストが通るように設計しています（T016/T017）

## 4) 進め方の推奨
- まずは T011→T015 で “分類 + scikit-learn モデル群” を固める
- 次に T016/T017 で optional モデルの取り込み
- その後 T018 以降で HPO / レポート / 可視化を段階的に追加
