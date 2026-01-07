# ml-solution-tabular-analysis

このリポジトリは **テーブル（tabular）データ解析**に特化した Solution Repo です。

- 共通基盤（Platform）は **別リポジトリ**：`dkawa2523/ml_platform_v1`（P201〜P204 まで改良済み）
- 本リポジトリは **用途固有（tabular）の実装**と、
  **Codex CLI で自動開発を進めるための指示ファイル群**（`work/` 配下）を提供します。

> 目的：plan2.md の方針（Platform + Solutions のポリレポ）に沿い、
> ClearML UI 上で「非DSでも迷わない」表示契約と、独立タスク + manifest/out.json での追跡性を担保した
> tabular-analysis ワークフローを、Codex CLI で段階的に実装します。

---

## 前提（必須）

1. Python 3.10+
2. Git
3. Codex CLI（あなたの環境に合わせて `tools/codex_loop/runtime.json` の `cmd` を設定）
4. `ml-platform`（dkawa2523/ml_platform_v1）を **先にインストール**しておくこと
   - P201〜P204 で追加された「manifest/hashes/out.json」「ClearML init_task 拡張」等が前提です。

---

## セットアップ（ローカル開発）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip

# 1) 先に ml-platform を editable install（例）
pip install -e ../ml-platform

# 2) 本 solution をインストール
pip install -r requirements/base.txt
pip install -e .  
```

> `pip install -e /path/to/ml_platform_v1` のパスは、あなたのローカル環境の配置に合わせてください。

---

## Codex CLI で自動開発を進める（推奨）

このリポジトリは `work/queue.json` と `work/tasks/` に **段階的な実装タスク**を用意しています。

### 1) （推奨）git 初期化

```bash
bash tools/codex_loop/bootstrap_git.sh
```

### 2) Codex CLI 実行設定（runtime.json）

```bash
bash tools/codex_loop/selfcheck_codex_exec.sh
```

- `tools/codex_loop/runtime.json` が生成されます。
- Codex CLI の呼び出し方は環境差が大きいので、必要ならこの JSON を編集してください。

### 3) Codex ループを回す

```bash
# 次の1タスクだけ
python tools/codex_loop/run.py --repo . --once

# 連続実行（途中で失敗したら失敗ログを差し戻して継続します）
python tools/codex_loop/run.py --repo .
```

- タスク定義：`work/queue.json`
- タスク本文：`work/tasks/T00x_*.md`
- 実行ログ：`work/runs/`

---

## 実装が進んだ後の実行（例）

Codex が T001〜 を完了すると、以下のように CLI から各プロセスを単独実行できるようになります。

```bash
# 例：前処理のみ
python -m tabular_analysis.cli task=preprocess \
  data.dataset_path=/path/to/data.csv \
  data.target_column=target

# 例：学習のみ（model と preprocess のバリアント指定）
python -m tabular_analysis.cli task=train_model \
  group/model=lgbm \
  group/preprocess=stdscaler_ohe

# 例：パイプライン
python -m tabular_analysis.cli task=pipeline
```

---

## ドキュメント

- `docs/00_SCOPE.md`：スコープ
- `docs/03_CLEARML_UI_CONTRACT.md`：ClearML UI 契約（Project/Tags/Properties/Artifacts/Plots）
- `docs/05_PROCESS_CATALOG.md`：各タスクの I/O 契約
- `docs/06_ARTIFACTS_AND_VERSIONING.md`：manifest/out.json 等の追跡性
- `docs/07_EVALUATION_PROTOCOL.md`：比較可能性（split_hash 等）

---

## 「ml-platform の追加改良は必要か？」

基本方針として、本 Solution は **P201〜P204 の改良済み ml-platform を前提**に進めるため、
通常は追加の platform 改良は必須ではありません。

ただし、開発を進める中で
- 「これは全 Solution に共通で欲しい」
- 「Solution 側で毎回同じ実装をしている」

という項目が出た場合は、plan2.md の方針に従い、
**共通化候補を platform 側の新タスク（例：P205〜）として昇格**することを推奨します。
