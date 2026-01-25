


以下は、あなたの **目的（多用途×複数人開発×ClearMLで非DSの製造開発エンジニアに提供サイクル高速化）** に対して、**リポジトリ管理を“最適解”寄りに再設計**した提案です。
（結論：**モノリポをやめる or 役割分離したハイブリッド**が、ClearML運用と組織スケールに最も効きます）

---

# 1. まず前提整理：何がボトルネックか

あなたが挙げた課題は、実は3つの軸に分解できます。

## A) 開発者側（複数人・多用途）の課題

* 1つのモノリポに **用途A/B/C…の前処理・特徴量・学習・推論**が混在
  → “読む量”が指数的に増え、**把握コストが上がる**
* 変更影響範囲が広くなり、レビュー・CI・リリースが重くなる
  → **提供サイクルが遅くなる**
* 不要ファイルが残りやすい（古い構成が混ざる）
  → **保守コストが高騰**

## B) ClearML側（非DSが使う面）の課題

* ClearMLタスクは **Task.init** で「実行したGitリポジトリ（commitやdiff）」にリンクされる ([ClearML][1])
  → すべてが同一URLだと、非DSが「どの用途の処理か」を誤認しやすい
* 用途ごとに Dataset/Task/Pipeline の設計が必要なのに、**ClearML上の整理軸（プロジェクト/タグ/Properties/Artifact）が統一されていない**と迷う

## C) 運用側（高速サイクル）の課題

* 変更をリリースする単位が不明瞭（どこまでが“共通”、どこまでが“用途固有”か）
  → 影響調査が遅く、結局慎重になって速度が落ちる

---

# 2. 結論：推奨する最適解は「Platform + Solutions のポリレポ構成」

## ✅ 推奨（最もバランスが良い）

**(1) 共通基盤リポジトリ（Platform）** と
**(2) 用途別リポジトリ（Solutions）** に分割します。

ClearMLで「どの用途のタスクか」が一瞬で分かり、開発も用途ごとに独立して回せます。

---

## 2.1 リポジトリの役割分担（責務の分離）

## Repo A: `ml-platform`（共通基盤）

**目的**：ClearML/Hydra/Artifact契約/タスク雛形/共通I/Oを提供する“土台”

含めるもの（例）

* ClearML UI 契約（HyperParameters汚染防止 / Properties / Artifacts / Plots の定石）
* Dataset/Task/Model/Pipelineの共通ユーティリティ（ClearML SDK wrapper）
* 代表ワークフローの「型」（dataset_register / preprocess / train_model / train_parent / infer_* / pipeline_controller）
* registryインタフェース（モデル/前処理/評価の拡張点）
* “テンプレとしてのdocs/agentskills/work/tasks”もここに置く（あなたのZIPの思想）

> ClearMLの「プロジェクト階層（`a/b/c`）」運用や、Properties活用は基盤で統一します ([ClearML][2])

---

## Repo B: `ml-solution-<usecase>`（用途別）

**目的**：用途固有の前処理/特徴量/モデル/評価/推論モードを実装する“製品”

含めるもの（例）

* 用途固有の `conf/`（Hydra設定）
* 用途固有の `registry/`（モデル/前処理/評価の追加登録）
* 用途固有の pipeline 定義（どのタスクを繋ぐか）
* 用途固有の README / 運用手順（非DS向けも含む）
* ClearML Project名やタグ設計（用途別に固定）

**重要**：このRepoがClearMLに紐づくことで
「ClearML上で同じGit URLだらけで分かりにくい」問題が消えます（用途別URLになる）。

---

## 2.2 依存関係（Solutions → Platform）

SolutionsはPlatformを依存として使います。選択肢は2つ：

### A案（推奨）：PlatformをPythonパッケージとして配布

* `ml-platform` を社内PyPIやGitタグで配布
* solutions は `ml-platform==X.Y.Z` にpinする
  → **再現性と安定性が高い**（ClearMLでの再実行も揺れにくい）

### B案：git submodule / subtree

* 速度は出るが、運用が複雑化しやすい
  → 長期運用では避けたい（人が増えるほど地獄化しやすい）

---

# 3. ClearML上の“見え方”を用途別に最適化する設計

リポ構成だけでなく、ClearML側の整理軸を用途別に固定すると、非DSが迷わなくなります。

## 3.1 ClearML Project階層を用途別に固定

ClearMLは `project_name="A/B/C"` のように **スラッシュ区切り階層**で整理できます ([ClearML][2])

例（推奨）

* `MFG/<UseCase>/01_dataset`
* `MFG/<UseCase>/02_preprocess`
* `MFG/<UseCase>/03_train`
* `MFG/<UseCase>/04_infer`
* `MFG/<UseCase>/99_pipeline`

こうすると、ClearML UI の「Projects」自体が用途別フォルダになります ([ClearML][3])

---

## 3.2 “Git URLが同じで分かりにくい”問題の最終手段

仮にモノリポ維持や、一時的に同URLが混在する場合でも、ClearMLは **Task.set_script** で
`repository / branch / working_dir / entry_point` を明示できます ([ClearML][4])

```python
task.set_script(
  repository="https://github.com/org/ml-solution-usecaseA.git",
  branch="main",
  working_dir=".",
  entry_point="src/app/cli/pipeline.py",
)
```

* **用途別リポURL**にできるならそれがベスト
* できない場合でも `working_dir/entry_point` を必ず出して視認性を上げる

---

## 3.3 User Properties / Tags を “検索UI”として使う

ClearMLの User Properties は **実行に影響せず、タスクテーブルの列に出せて検索・フィルタに強い** ([ClearML][5])

用途別の標準プロパティ例：

* `usecase_id`
* `dataset_id`
* `preprocess_dataset_id`
* `model_id`
* `recommended_model_id`
* `primary_metric`
* `best_score`

これにより、非DSは
「UseCaseのフォルダ → task table → recommended_model_id」
の流れで迷わず辿れます。

---

## 3.4 “比較”はTracking Leaderboardで固定化

ClearMLにはタスクテーブルをカスタムして比較に使える **Tracking Leaderboard** の仕組みがあります ([ClearML][6])
用途別に「Train Parent のプロジェクト」へleaderboardを作ると、非DSが最短で判断できます。

---

# 4. それでもモノリポにしたい場合の「破綻しない」条件

ポリレポが最適ですが、組織事情でモノリポを継続する場合は、次の条件を満たさないとほぼ確実に破綻します。

## 4.1 “Repo内ポリレポ化”をする（ワークスペース構造）

```
repo/
  platform/          # 共通基盤（パッケージ）
  solutions/
    usecase_a/
    usecase_b/
  tools/
  docs/
```

ClearMLからは同一URLになりますが、**Project階層 + entry_point + properties** で分離します。

## 4.2 ClearMLの「プロジェクト階層」を強制する

用途Aのタスクが用途Bのプロジェクトに出ないように
`project_name` をコードで固定します ([ClearML][2])

## 4.3 Pipeline実行キューを用途別に分ける

PipelineControllerは default queue を設定し、stepごとに queue を分けられます ([ClearML][7])
用途別にAgentを分けるなら、ここも用途軸で分けた方が事故が減ります。

---

# 5. リポジトリ戦略の意思決定（おすすめの判定表）

| 方式                                | 開発効率 | ClearMLの分かりやすさ（非DS） | 運用コスト | 拡張性 |
| --------------------------------- | ---: | ------------------: | ----: | --: |
| **推奨：Platform + Solutions（ポリレポ）** |    ◎ |           ◎（用途別URL） |     ○ |   ◎ |
| モノリポ（厳格な分離＋ClearML設計で補う）          |    ○ |            △（URL同一） |     △ |   ○ |
| なんでもモノリポ（現状に近い）                   |    △ |                   ✕ |     ✕ |   △ |

あなたの課題（ClearML上で同URLだと分かりにくい、用途別のタスク設計が必要）を踏まえると、**ポリレポが最適解に近い**です。

---

# 6. 移行プラン（現実的に“事故らない”順番）

## Step 0: Platform repo を確定（契約とテンプレを固定）

* 先ほどのZIP（docs/work/agentskills/tools/codex_loop）を **Platform側**の基盤にする
* “UI契約”と“Artifacts契約”をPlatformで不変にする

## Step 1: パイロット用途を1つだけ Solutions repo 化

* UseCase A を `ml-solution-usecaseA` として切り出す
* ClearML Project を `MFG/UseCaseA/...` に固定
* 製造開発エンジニアに、ClearML上での導線を試してもらう

## Step 2: Platformをバージョン固定して配布

* `ml-platform` を `0.1.0` などでtag
* Solution repo は `ml-platform==0.1.0` に固定

## Step 3: UseCaseを順次移行（リリース単位を用途にする）

* UseCase B/C…を同様にSolution化
* モノリポ側は “参照専用・廃止予定” に寄せていく

---

# 7. 最後に：あなたの目的に直結する「設計の芯」

あなたのゴールはコード整理そのものではなく、

* **非DSがClearMLだけで迷わない**
* **用途別に提供サイクルを高速に回せる**
* **複数人で拡張しても複雑化しない**

です。

そのためのアーキテクチャ上の最適解は、

1. **共通契約（Platform）を固定し**
2. **用途ごとの速度と可読性（Solution）を最大化**し
3. ClearMLの **プロジェクト階層 + Properties + Leaderboard** を用途軸で統一する

この3点セットになります。ClearMLはタスク作成時にgit情報を自動で紐づけるので ([ClearML][1])、用途別リポジトリ化は “UIの理解速度” に直接効きます。

---

もし次に進めるなら、あなたの現状（チーム数、用途数、リリース頻度、Agent運用、オンプレ/クラウドなど）を前提に、以下のどちらかを作ります：

* **推奨案（ポリレポ）**の “具体的なrepo一覧・命名規約・ClearML Project命名・タグ体系” を完全に確定した `docs/`（不変契約）
* “当面モノリポ継続” のための **破綻しない最低限のガード**（境界・CI・ClearML set_script/Project運用・依存方向・削除規約）を完全に確定した `docs/`

どちらを前提にしますか？（※迷うなら、まずは **UseCase 1つをSolution repo化**が最も安全で効果が見えやすいです）

[1]: https://clear.ml/docs/latest/docs/clearml_sdk/task_sdk/ "Task | ClearML"
[2]: https://clear.ml/docs/latest/docs/fundamentals/projects/ "Projects | ClearML"
[3]: https://clear.ml/docs/latest/docs/webapp/webapp_projects_page/?utm_source=chatgpt.com "Projects Page"
[4]: https://clear.ml/docs/latest/docs/references/sdk/task/ "Task | ClearML"
[5]: https://clear.ml/docs/latest/docs/fundamentals/hyperparameters/ "Hyperparameters | ClearML"
[6]: https://clear.ml/docs/latest/docs/guides/ui/building_leader_board/?utm_source=chatgpt.com "Tracking Leaderboards"
[7]: https://clear.ml/docs/latest/docs/pipelines/pipelines_sdk_tasks/ "PipelineController | ClearML"


了解です。**推奨案（ポリレポ：Platform + Solutions）を前提**に、前回ZIP（単一repo前提）を **0から設計し直した新ZIP**を作成しました。
目的は一貫して同じ（非DSがClearMLで迷わず辿れる／複数人・多用途で開発効率化／ClearML運用高速化）で、さらに今回の条件として：

* **Localから核処理実行・pipeline実行ができる**
* **ClearML Agentでの実行**もできる
* **ClearML上でリポジトリURL設定しやすい（UI clone mode）**ことを仕様として入れる（`task.set_script(...)` をconfig制御で可能にする）

…を **docsとタスク（work/queue.json）に反映**しています。

---

## ダウンロード（ZIP）

### ✅おすすめ：2リポジトリ同梱ワークスペース（最短で始められる）

* [Download: ml_polyrepo_workspace_v1.zip](sandbox:/mnt/data/ml_polyrepo_workspace_v1.zip)
  中身:

  * `ml-platform/`（共通基盤）
  * `ml-solution-template/`（用途別テンプレ）

### 個別に欲しい場合

* [Download: ml_platform_scaffold_v1.zip](sandbox:/mnt/data/ml_platform_scaffold_v1.zip)
* [Download: ml_solution_template_scaffold_v1.zip](sandbox:/mnt/data/ml_solution_template_scaffold_v1.zip)

---

# この新ZIPの設計方針（ポリレポ版）

## 1) Repo分割（責務境界を固定）

### `ml-platform`（共通基盤）

* **契約の正**（UI契約、Artifacts契約、評価規約、誤認防止ルール）
* ClearML/Hydraの **共通ユーティリティ**（Task/Dataset/Model/Pipelineの薄いラッパ）
* 将来拡張（時系列/画像/多目的）でも **壊れない骨組み**
* `codex_loop` / `agentskills` / `work/tasks` を保持（＝プロジェクト運用の中心）

### `ml-solution-<usecase>`（用途別）

* 用途固有の `conf/`（Hydra）
* 用途固有の registry 拡張（モデル・前処理・指標）
* 用途固有 pipeline 定義
* 非DS向け導線 docs（ClearML上での見る順・判断方法）
* ClearML上で「用途」が混ざらないよう **project名階層・usecase_idを固定**

---

## 2) 実行モードを仕様として標準化（Local / Agent / UI clone）

このZIPでは、docs/とタスクに次を **必須対応**として入れています：

* **Local mode**: `run.clearml.enabled=false` で核処理実行（開発・デバッグ）
* **ClearML logging mode**: `run.clearml.enabled=true` でTask作成・Artifacts/Plots/Propertiesを記録
* **Agent mode**: `enqueue=true` で `task.execute_remotely(queue_name=...)`（タスク単体）
* **UI clone mode**: `task.set_script(repository/branch/entry_point/working_dir)` を **configで設定可能**
  → 「ClearML上でリポジトリURL設定しやすい」を仕様として担保

※これを `docs/21_EXECUTION_MODES.md` と `docs/02_CLEARML_TASK_UI_CONTRACT.md` に明文化してあります。

---

# ZIPの中身（重要ファイル）

## Platform側（`ml-platform/`）

* `docs/01_POLYREPO_ARCHITECTURE.md`：境界・依存・混在防止ルール
* `docs/02_CLEARML_TASK_UI_CONTRACT.md`：UI契約（HyperParameters汚染防止含む）
* `work/queue.json`：Platform実装タスク（P0/P1）
* `tools/codex_loop/run.py`：誤DONE防止つきCodexループ

## Solution側（`ml-solution-template/`）

* `docs/20_USECASE_GUIDE.md`：非DS導線（ClearMLで見る順）
* `docs/21_EXECUTION_MODES.md`：Local/Agent/UI cloneの仕様
* `work/queue.json`：Solution実装タスク（P0/P1）
* `conf/`：作成対象（タスク内で生成する前提）

---

# 使い方（最短）

## 0) 展開

```bash
unzip ml_polyrepo_workspace_v1.zip -d <workspace>
cd <workspace>
```

---

## 1) Platformを先に実装（Codex loop）

```bash
cd ml-platform
bash tools/codex_loop/bootstrap_git.sh

python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements/base.txt

clearml-init   # 初回のみ
bash tools/codex_loop/selfcheck_codex_exec.sh

python tools/codex_loop/run.py --repo . --once
python tools/codex_loop/run.py --repo .
```

---

## 2) Solution側を実装（Platformを依存）

```bash
cd ../ml-solution-template
bash tools/codex_loop/bootstrap_git.sh

python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements/base.txt

# 開発中はPlatformをeditable install（推奨）
pip install -e ../ml-platform

clearml-init   # 初回のみ
bash tools/codex_loop/selfcheck_codex_exec.sh

python tools/codex_loop/run.py --repo . --once
python tools/codex_loop/run.py --repo .
```

---

# 何が「前回ZIP」から変わったか（あなたの要望反映ポイント）

* **モノリポ前提を撤回**し、最初から **ポリレポ運用（用途別repo）**に合わせた docs/work/tasks を再設計
* ClearML上での識別性改善（用途別repo URL、usecase_id、project階層固定）
* **Local / Agent / UI clone** を仕様として明文化し、タスクにも実装要求として入れた
* Codexループの誤DONE問題に対して、前回同様に **NONCE必須 + must_change_globs + 差分検出 + Verification必須** を維持

---

必要なら次に、あなたの組織・運用に合わせて **ClearML Project階層命名規約（例：`MFG/<usecase>/01_dataset` など）** と **Properties/Tagsの固定キーセット**を、docsにさらに強く固定した版に更新したZIPも作れます。





















以下は、**polyrepo（ml-platform / ml-solution）前提**で、**tabular-analysis を「今後の基準（ワークフロー事例の軸）」として新規実装する**ための **仕様・設計（契約）**を、**Markdown形式**で “コピペできる” 形で提示します。
（※ここに書く内容は「実装がどうあるべきか」の**不変契約**です。Codex-cli のタスクや実装は必ずこれに従います）

---

File: `ml-solution-template/usecases/tabular-analysis/docs/README.md`

```md
# tabular-analysis 設計ドキュメント（読む順）

この `tabular-analysis` は、今後のMLワークフロー事例の「軸」になることを目的に、**拡張しやすく・運用しやすく・ClearML上で迷わない**ことを最優先に設計する。

## 読む順（最短）
1. 00_SCOPE.md
2. 01_POLYREPO_INTENT.md
3. 02_ARCHITECTURE.md
4. 03_CLEARML_UI_CONTRACT.md
5. 04_CONFIG_CONVENTIONS.md
6. 05_PROCESS_CATALOG.md
7. 06_ARTIFACTS_AND_VERSIONING.md
8. 07_EVALUATION_PROTOCOL.md
9. 08_PIPELINE_ORCHESTRATION.md
10. 09_PLUGIN_REGISTRY.md
11. 10_OPERATION_LOCAL_AND_AGENT.md
12. 11_REVIEWER_GUIDE.md
13. 12_CLEANUP_POLICY.md

## 目的（不変）
- **ユーザー（非データサイエンティスト）**が ClearML 上で「結果の把握・参照・業務活用」まで迷わず辿れること
- **開発者**が ClearML や各ライブラリ仕様を深掘りしなくても、拡張ポイント（前処理/モデル/評価/可視化/情報付与）を守れば安全に追加できること
- テーブルデータ解析の基盤であるが、将来の拡張（多次元目的変数、画像/時系列、深層学習など）を阻害しない骨格であること

## 最重要ポイント
- `preprocess` / `train` / `infer` / `leaderboard` は **ClearML上でも独立タスク**（親子タスク禁止）
- `leaderboard` は「親」ではなく **後段の集計タスク**（対象 task_id を受け取り、比較・評価・可視化する）
- `pipeline` は **接着剤**：複数タスクを作成・実行し、task_id を後段へ受け渡す（ローカル/Agent両対応）
```

---

File: `ml-solution-template/usecases/tabular-analysis/docs/00_SCOPE.md`

```md
# スコープと非スコープ

## スコープ（v1）
- 入力：テーブルデータ（CSV/Parquet）
- 目的変数：単一スカラー（回帰を主軸、分類は拡張枠として用意）
- タスク：
  - dataset_register（Dataset Task）
  - preprocess（Dataset Task：前処理済みデータセット作成）
  - train（Training Task：1モデル×1前処理データセット）
  - infer（Inference Task：single/batch/optimize）
  - leaderboard（集計比較タスク：trainタスク群の比較）
  - pipeline（複数タスクの一括実行）

## 初期に「動く」前提（スモークの基準）
- 前処理：StandardScaler（数値） / OneHot（カテゴリ）/ 欠損補完
- モデル：LightGBM / Ridge / GPR（GaussianProcessRegressor）
- 推論：single / batch / optimize（optuna等は拡張）

## 非スコープ（v1でやらない）
- 画像/動画/音声/時系列の専用IO・モデル（拡張設計はする）
- 多次元目的変数（拡張設計はする）
- 分散学習・大規模DLトレーニング（拡張設計はする）
- 企業固有のデータ権限・ガバナンス実装（docsでTODO管理）
```

---

File: `ml-solution-template/usecases/tabular-analysis/docs/01_POLYREPO_INTENT.md`

```md
# polyrepo（ml-platform / ml-solution）分離の意図（不変契約）

## 結論
- **ml-platform**：全ユースケース共通の「骨格」「契約」「ClearML/Hydra/Artifactの標準化」「安全な拡張点」を提供する
- **ml-solution（tabular-analysis）**：ユースケース固有の実装（前処理・モデル・可視化・解釈）を薄く載せる

この分離によって以下を達成する：
- ClearML上で「用途別Git URL」になる（=非DSが把握しやすい）
- 共通部分の変更をSemVerで管理し、各用途を壊さずに進化できる
- 用途別の責務が閉じ、レビュー・CI・運用が軽くなる

## ml-platform に置くべきもの（共通・抽象）
- ClearMLラッパ（Task/Dataset/Model/Logger/clone/agent/pipeline）
- Artifact契約のユーティリティ（manifest生成、config hash、標準ディレクトリ）
- 実行モードの共通化（local / clearml / agent / clone）
- registry の抽象（Registry interface、型、拡張パターン）
- テスト/doctor 共通（最小）

## ml-solution（tabular-analysis）に置くべきもの（具体・用途）
- テーブルデータのスキーマ推定、前処理レシピ、特徴量処理
- モデル群（LightGBM/Ridge/GPR + 拡張）
- 目的変数変換（回帰のtarget scaler等）
- 可視化（テーブル向けの標準プロット）
- ユースケースのClearMLプロジェクト階層、Properties命名などの具体

## 禁止事項（混乱の原因）
- tabular固有の処理を platform に持ち込まない（platformが肥大化する）
- ClearML UI 表示ルールを solution 側で勝手に変更しない（非DSが迷う）
- 同じ意味のメタ情報キーを用途ごとに変える（横断検索できなくなる）
```

---

File: `ml-solution-template/usecases/tabular-analysis/docs/02_ARCHITECTURE.md`

````md
# アーキテクチャ（独立タスク + 集計）

## 全体像（依存方向）
- solution は platform に依存する（platform → solution には依存しない）
- 各処理は独立タスクとして動く
- pipeline は「実行順とtask_id受け渡し」だけを担い、処理ロジックは持たない

```mermaid
flowchart LR
  subgraph Platform[ml-platform]
    P1[clearml adapters]
    P2[artifact/version utils]
    P3[execution modes]
    P4[registry interfaces]
  end

  subgraph Solution[tabular-analysis (ml-solution)]
    S0[conf (Hydra)]
    S1[process: dataset_register]
    S2[process: preprocess]
    S3[process: train]
    S4[process: infer]
    S5[process: leaderboard]
    S6[process: pipeline]
    R1[registry: preprocessors/models/metrics]
  end

  P1 --> S1
  P1 --> S2
  P1 --> S3
  P1 --> S4
  P1 --> S5
  P2 --> S1
  P2 --> S2
  P2 --> S3
  P2 --> S4
  P2 --> S5
  P3 --> S1
  P3 --> S2
  P3 --> S3
  P3 --> S4
  P3 --> S6
  P4 --> R1
  R1 --> S2
  R1 --> S3
  R1 --> S5
````

## タスク関係（親子禁止）

* preprocess と train は親子ではない
* train 同士も親子ではない
* leaderboard は後段の集計タスクであり、親ではない

```mermaid
flowchart TD
  A[dataset_register Task] --> B[preprocess Task (variant A)]
  A --> C[preprocess Task (variant B)]
  B --> T1[train Task (model LGBM, variant A)]
  B --> T2[train Task (model Ridge, variant A)]
  C --> T3[train Task (model LGBM, variant B)]
  C --> T4[train Task (model GPR, variant B)]
  T1 --> L[leaderboard Task]
  T2 --> L
  T3 --> L
  T4 --> L
  L --> I[infer Task (optional)]
```

## なぜ親子をやめるのか（運用の最適化）

* 「親」に集約するとPlotsが肥大化し、非DSの導線が崩れる
* 失敗時の再実行粒度が粗くなる（子が増えるほど辛い）
* 比較は “集計タスク” に分離したほうが透明性が高い

````

---

File: `ml-solution-template/usecases/tabular-analysis/docs/03_CLEARML_UI_CONTRACT.md`
```md
# ClearML UI 契約（HyperParameters / Info / Plots / Debug Samples）

## 目的
- 非DSが「何を見るべきか」迷わない
- 設定の誤認（関係ないパラメータがHyperParametersに出る問題）を防ぐ
- 比較が容易（Properties/Artifacts/Plotsが統一）

---

## 0. 共通ルール（全タスク）
### Project 名（階層）
`TABULAR/<usecase_id>/<process_name>`

例：
- `TABULAR/UseCaseA/01_dataset_register`
- `TABULAR/UseCaseA/02_preprocess`
- `TABULAR/UseCaseA/03_train`
- `TABULAR/UseCaseA/04_infer`
- `TABULAR/UseCaseA/05_leaderboard`
- `TABULAR/UseCaseA/99_pipeline`

### Task 名
`<process_name>__<short_context>__v<schema_version>`

例：
- `preprocess__stdscaler_ohe__v1`
- `train__lgbm__preproc=stdscaler_ohe__v1`
- `leaderboard__top=rmse__v1`

### Tags（最低限）
- `usecase:<usecase_id>`
- `process:<dataset_register|preprocess|train|infer|leaderboard|pipeline>`
- `schema:v1`
- （任意）`grid:<run_id>`（pipeline実行で付与）

### User Properties（共通）
- `usecase_id`
- `process`
- `schema_version`
- `code_version`（git commit or package version）
- `platform_version`

---

## 1. HyperParameters（最重要）
### 原則
**そのタスクの再実行に必要な“入力設定”のみ**を入れる  
（他プロセスの設定を入れない／自動推定値や出力は入れない）

### 入れるもの（例）
- preprocess：欠損値処理/カテゴリ処理/スケーリング/目的変数変換/列指定
- train：モデル名/モデルHP/CV設定/metric/seed/データセットID
- infer：model_id/mode/input形式/最適化範囲や制約
- leaderboard：対象task_id群/集計metric/選定ルール

### 禁止
- pipelineの設定を各タスクのHyperParametersに混ぜない
- 出力（recommended_model 等）をHyperParametersに入れない（Propertiesへ）

---

## 2. Configuration タブ
### 役割
- 「完全再現のためのフル設定」を保存する（Hydraの最終合成結果）

### 保存方法（推奨）
- `config_resolved.yaml` を artifact としても保存
- ClearMLの configuration object としても保存（可能なら）

---

## 3. Info タブ（非DSが読む）
- 先頭に「このタスクの目的」「入力」「出力」「見るべきPlots」を箇条書きで固定
- pipelineから起動された場合：
  - `grid_run_id`
  - `upstream_task_ids`（JSON要約へのリンク）

---

## 4. Plots（表示順を安定化）
### ルール
- タイトルに **番号プレフィックス**を付ける：`01_`, `02_` ...
- 「比較/意思決定に必要なもの」を上に、詳細は下に

### タスク別の必須Plots
#### preprocess
- `01_DataOverview`（欠損率、列型、サンプル統計）
- `02_PreprocessSummary`（カテゴリ別summaryを表で）
- `03_TargetTransform`（目的変数の変換前後分布）

#### train
- `01_ScoreSummary`（主要metric、CV分布）
- `02_Residuals`（残差の基本）
- `03_FeatureImportance`（利用可能なモデルのみ）
- `90_Debug`（必要時のみ）

#### infer
- mode=single: `01_Output`
- mode=batch: `01_PredsPreview`
- mode=optimize: `01_OptimizationCurve`, `02_TrialScatter`

#### leaderboard
- `01_LeaderboardTable`
- `02_TopModelsBar`
- `03_MetricVsTime`（任意）
- `04_Recommendation`（推奨の根拠）

---

## 5. Debug Samples（混乱を防ぐ）
- サンプルは「少量」かつ「代表例」に限る
- preprocess: 変換前後の同一行比較（3〜10行）
- train: 予測 vs 実測のサンプル（3〜10行）
- infer: 入力と出力（singleはJSON、batchは先頭数行）
- optimize: 上位候補の入力/出力（上位5件まで）

※Debug Samplesは “大量保存禁止”。大量データはArtifact（CSV/Parquet）へ。
````

---

File: `ml-solution-template/usecases/tabular-analysis/docs/04_CONFIG_CONVENTIONS.md`

```md
# Hydra 設定規約（不変契約）

## 設計方針
- 1タスク = 1 config root（必要な設定だけ）
- pipeline config は「各タスク設定の束」だが、各タスクへ渡すのはサブツリーのみ
- seed / split / metric は比較可能性のため統一できるようにする

## ディレクトリ例
conf/
  process/
    dataset_register.yaml
    preprocess.yaml
    train.yaml
    infer.yaml
    leaderboard.yaml
    pipeline.yaml
  group/
    preprocess/
      stdscaler_ohe.yaml
      minmax_ohe.yaml
    model/
      lgbm.yaml
      ridge.yaml
      gpr.yaml
    infer_mode/
      single.yaml
      batch.yaml
      optimize.yaml
  env/
    local.yaml
    agent.yaml

## 重要キー（共通）
run:
  usecase_id: "UseCaseA"
  seed: 42
  output_dir: "outputs/${now:%Y%m%d_%H%M%S}"
  clearml:
    enabled: true|false
    execution: local|agent|clone
    project_root: "TABULAR/${run.usecase_id}"
    queue: "default"
    clone_from_task_id: null   # clone運用時に指定
data:
  dataset_id: null             # ClearML Dataset ID
  local_path: "data/input.csv" # local運用
  target: "y"
  id_col: null
  group_col: null              # group split用（将来拡張）
preprocess:
  variant_name: "stdscaler_ohe"
  ...
train:
  model_name: "lgbm"
  model_params: {}
  cv:
    enabled: true
    n_splits: 5
  metric:
    primary: "rmse"
infer:
  mode: "batch"
  input_path: "data/infer.csv"
leaderboard:
  task_ids: []                 # 基本
  query:
    project: null              # オプション
    tags: []                   # オプション
  select:
    primary_metric: "rmse"
    direction: "min"
    top_k: 10

## Hydra override 例
- 特定モデルで train を実行：
  python -m tabular_analysis.cli.train +group/model=lgbm
- 前処理variantを変えて preprocess：
  python -m tabular_analysis.cli.preprocess +group/preprocess=minmax_ohe
- pipelineで grid を回す（例：variant×model）：
  python -m tabular_analysis.cli.pipeline pipeline.grid.preprocess=[stdscaler_ohe,minmax_ohe] pipeline.grid.model=[lgbm,ridge,gpr]
```

---

File: `ml-solution-template/usecases/tabular-analysis/docs/05_PROCESS_CATALOG.md`

```md
# Process カタログ（I/O契約）

## 共通I/O（すべてJSONで受け渡し可能）
- 入力：`--in outputs/<prev>.json`
- 出力：`--out outputs/<this>.json`

pipeline は各プロセスの out を読み、次の in に渡す。

---

## 1) dataset_register（Dataset Task）
### 入力
- local_path（CSV/Parquet）
- dataset_name / version / tags

### 出力（out.json）
- raw_dataset_id
- raw_schema（簡易）
- preview_path（artifact）

### ClearML UI
- HyperParameters：入力パス、dataset名、タグ、スキーマ推定設定
- Artifacts：preview.csv, schema.json, out.json
- Plots：DataOverview

---

## 2) preprocess（Dataset Task）
### 入力
- raw_dataset_id もしくは local_path
- preprocess.variant 設定（欠損/カテゴリ/スケール/target変換）
- split 設定（seed, strategy）

### 出力
- processed_dataset_id
- preprocess_variant_name
- split_id（hash）
- bundle_artifact_ref（joblib等）

### 重要：前処理情報の保存
- `summary.md` をカテゴリ別に必ず出す
  - 入力特徴量の前処理
  - 目的変数の前処理
  - 欠損値処理
  - カテゴリ処理
  - 外れ値/クリップ（将来）
- `recipe.json`（構造化）

---

## 3) train（Training Task：独立）
### 入力
- processed_dataset_id（推奨）
- model_name + model_params
- evaluation 設定（CV/split/metric/seed）

### 出力
- model_id（ClearML Model Registry の id ）
- metrics.json
- preds_val.parquet（任意）
- model_bundle（model + preprocess bundle + schema + meta）

### ClearML UI
- HyperParameters：train.* だけ
- Properties：model_id, primary_metric, score, dataset_id, preprocess_variant
- Plots：スコア、残差、重要度（可能なら）
- Debug Samples：予測vs実測数行

---

## 4) infer（Inference Task：独立）
### 入力
- model_id
- mode: single|batch|optimize
- input（single=JSON, batch=CSV/Parquet, optimize=探索空間）

### 出力
- single：output.json
- batch：preds.csv + preds.parquet
- optimize：best.json + trials.csv

### ClearML UI
- HyperParameters：infer.* のみ
- Artifacts：入出力、trial
- Plots：optimize曲線など

---

## 5) leaderboard（集計比較タスク：独立）
### 入力
- task_ids（trainタスクのID群）※基本
- オプション：project/tags検索
- ranking ルール（metric/direction/top_k）

### 出力
- leaderboard.csv
- recommendation.json（推奨 train_task_id / model_id / 根拠）

### ClearML UI
- HyperParameters：対象task_ids と ranking ルールのみ
- Plots：比較表、上位棒グラフ、推奨根拠
```

---

File: `ml-solution-template/usecases/tabular-analysis/docs/06_ARTIFACTS_AND_VERSIONING.md`

```md
# Artifact契約・バージョニング

## 共通（全タスク必須）
- `config_resolved.yaml`
- `out.json`（このタスクの出力）
- `manifest.json`
  - schema_version
  - code_version（git commit）
  - platform_version
  - created_at
  - inputs（dataset_id/model_id/task_ids 等）
  - outputs（dataset_id/model_id 等）
  - hashes（config_hash, split_hash, recipe_hash 等）

## preprocess の成果物
- `summary.md`（カテゴリ別に必須）
- `recipe.json`（構造化）
- `bundle.joblib`（transformers + target transform）
- `schema.json`（列型、target、ID列など）
- `split.json`（indices/seed/strategy/hash）

## train の成果物
- `metrics.json`（主要metric + 補助metric）
- `cv_scores.json`（CV分布）
- `preds_val.parquet`（任意）
- `model_bundle/`
  - `model.bin` or `model.pkl`
  - `bundle.joblib`
  - `schema.json`
  - `meta.json`
- ClearML Model Registry への登録：
  - model_id を Properties に保存

## infer の成果物
- single：`input.json`, `output.json`
- batch：`preds.csv`, `preds.parquet`, `input_preview.csv`
- optimize：`search_space.json`, `trials.csv`, `best.json`

## leaderboard の成果物
- `leaderboard.csv`
- `recommendation.json`
- `summary.md`（推奨理由、差分、注意点）

## バージョニング方針
- schema_version（artifact契約の版）を solution 側で固定
- platform_version（ml-platform）を pin して Properties/manifest に必ず記録
- config_hash / recipe_hash / split_hash を比較可能性の鍵として扱う
```

---

File: `ml-solution-template/usecases/tabular-analysis/docs/07_EVALUATION_PROTOCOL.md`

```md
# 評価プロトコル（比較可能性の契約）

## 基本原則
- すべての train タスクは「比較可能」でなければならない
- 比較可能性は以下が一致したときに成立する：
  - dataset（processed_dataset_id）
  - split（split_hash）
  - metric（primary）
  - seed
  - leakage チェックを通っている

## split
- preprocess タスクが split を生成し、processed_dataset に保存する
- train は split をそのまま使う（再生成禁止）

## metrics
- primary metric を 1つ必ず指定（例：rmse）
- 補助 metric は任意（mae, r2 等）
- leaderboard の ranking は primary metric と direction で固定

## leakage / skew
- 目的変数に関する変換は preprocess bundle に保存し、推論で逆変換する
- train/infer で前処理の再fitは禁止（skew原因）
- preprocess bundle を model_bundle に同梱することで skew を排除
```

---

File: `ml-solution-template/usecases/tabular-analysis/docs/08_PIPELINE_ORCHESTRATION.md`

```md
# pipeline（接着剤）の設計

## pipeline の役割
- grid 実行（複数前処理×複数モデル）を作成・起動する
- 生成した train_task_id 群を leaderboard に渡す
- 親子タスクは作らない（リンクは Properties / Artifacts で追跡）

## 実行モード
- local: pythonプロセス内で順に実行（ローカル検証用）
- agent: task.execute_remotely でキュー投入（後から動作確認）
- clone: template task を clone して投入（本番運用の想定）

## task_id 受け渡し
- pipeline は `pipeline_run.json` に以下を保存：
  - preprocess_task_ids
  - train_task_ids
  - leaderboard_task_id
  - inference_task_ids（任意）
- leaderboard は `task_ids` を基本入力として受け取る
- project/tags検索は “補助” として実装する
```

---

File: `ml-solution-template/usecases/tabular-analysis/docs/09_PLUGIN_REGISTRY.md`

```md
# registry（拡張ポイント）規約

## 目的
- 追加実装が “差分” として閉じる
- コード探索しなくても追加箇所が一意

## 追加箇所（solution 側）
- `registry/preprocessors.py`
- `registry/models.py`
- `registry/metrics.py`
- `viz/plots.py`（標準プロット群）
- `io/`（入出力形式拡張）

## 追加時のルール
- 追加したら必ず：
  - registry への登録
  - conf/group/ に設定テンプレを追加
  - docs/CHANGELOG.md に簡潔に追記
  - smoke test を更新（最低1ケース）

## 初期有効モデル（必須）
- lgbm（LightGBM）
- ridge（Ridge）
- gpr（GaussianProcessRegressor）

## 初期有効前処理（必須）
- stdscaler_ohe（StandardScaler + OneHot）
```

---

File: `ml-solution-template/usecases/tabular-analysis/docs/10_OPERATION_LOCAL_AND_AGENT.md`

```md
# 運用：ローカル/Agent/clone の切り替え

## ローカル（主軸）
- ClearML disabled でも処理は最後まで動く（ログはローカルに残す）
- ClearML enabled の場合も、まずローカルで正しさ確認

推奨：
- preprocess/train/infer/leaderboard を単体実行して整合性を見る
- pipeline は最後に

## Agent 実行（後から動作確認）
- `run.clearml.execution=agent`
- `run.clearml.queue=...`

## clone 実行（テンプレ運用）
- 各プロセスに template_task_id を用意
- `run.clearml.clone_from_task_id` 指定時：
  - その task を clone してパラメータ上書き→enqueue
- UIから clone しても同じ挙動になること（再現性の要件）
```

---

File: `ml-solution-template/usecases/tabular-analysis/docs/11_REVIEWER_GUIDE.md`

```md
# レビューワー向け：重要箇所の探し方

## まず見る
- `docs/03_CLEARML_UI_CONTRACT.md`（UI契約）
- `docs/05_PROCESS_CATALOG.md`（I/O）
- `registry/*`（拡張点）

## 変更が入ったときに影響が大きい場所
- split生成（preprocess）
- bundle保存/読み込み（preprocess/train/infer）
- model_bundle 形式（train/infer）
- leaderboard の ranking ロジック

## “ファイル増殖”の禁止
- 新規機能はまず registry/ と conf/group/ へ
- タスクを増やす前に、既存タスクの拡張で解決できないか検討
```

---

File: `ml-solution-template/usecases/tabular-analysis/docs/12_CLEANUP_POLICY.md`

```md
# クリーンアップ方針（冗長化防止）

## 原則
- 使っていないファイルは残さない（残すなら理由とTODO）
- ディレクトリが増えたら「責務の分離」になっているか確認
- サンプル/実験コードは `experiments/` に隔離し、mainline に混ぜない

## Codex タスク運用
- 各タスク完了時に「削除候補」を列挙し、必要なら削除タスクを起票
- vulture/ruff などで未使用検出を行い、P1で計画的に削除
```

---

# 補足：この仕様があなたの要件を満たす理由（要点）

* **親子タスク廃止**：preprocess/train/infer は独立、leaderboard は後段集計（要求通り）
* **ClearML UI 契約**：HyperParameters汚染防止、Info/Plots/Debug Samples の役割分離（非DS導線）
* **多前処理×多モデル**：pipeline が grid を回し、task_id を leaderboard へ受け渡す（比較可能）
* **local主軸 + Agent/clone対応**：execution を config で切替（運用切替が明確）
* **polyrepo意図**：platform を肥大化させず、solution の拡張点（registry）を明確化
* **ファイル増殖防止**：Process/I/O/Registry/Plot を固定し、増殖しやすい部分を規約化

---

必要なら次に、あなたが実際に使っている **ml-platform の公開API（clearml wrapper の関数名・I/F）** に合わせて、上記仕様を「実装I/Fレベル」にさらに落とし込んだ **`docs/13_PLATFORM_API_ASSUMPTIONS.md`**（TODO埋め版）も作れます。



以下は、提示した仕様（polyrepo + 独立タスク + leaderboard集計 + local主軸 + ClearML Agent/clone対応）を前提にしたときに、実運用・開発で起きがちな **想定課題** と **対応策**、そして改めて **ml-platform の役割**を整理したものです。
（長いですが、後々の事故を減らすために “起こりうる失敗” を先回りで網羅します）

---

# 1) 想定課題と対応策

## A. 独立タスク化による「全体の関連が見えにくい」

### 起こりうること

* 親子タスクをやめると、ClearML上で「どの preprocess がどの train に効いたか」「この leaderboard はどの train 群を集計したか」が一目で追いづらい。
* 非DSが「結局どれを見ればいいの？」となる。

### 対応策（仕様に入っている／入れるべき）

1. **リンクは “親子” ではなく “manifest + Properties + artifact” で追えるようにする**

   * `manifest.json` に `inputs` と `outputs` を必ず記録
   * pipeline は `pipeline_run.json` を必ず出す（train_task_ids 等）
2. **User Properties を「タスク一覧で追跡できる形」に統一**

   * train: `processed_dataset_id`, `preprocess_variant`, `split_hash`, `model_id`, `primary_metric`, `score`
   * preprocess: `raw_dataset_id`, `processed_dataset_id`, `recipe_hash`, `split_hash`
   * leaderboard: `train_task_ids_count`, `recommended_train_task_id`, `recommended_model_id`
3. **ClearML Project階層を固定**（`TABULAR/<usecase>/03_train` など）

   * 非DSは「まず 99_pipeline → 05_leaderboard → 04_infer」の順に辿れる。

> “親子”の代わりに “検索しやすいメタ情報” を前提にするのが独立タスク方式の肝です。

---

## B. Task ID 指定方式の運用負担（手で集めると辛い）

### 起こりうること

* leaderboard に task_id を渡すのが基本、となると手動運用では面倒。
* タスクIDを間違えて集計、誤った結論になる。

### 対応策

1. **Pipeline実行時は自動で task_id を受け渡す**（仕様の要件）

   * pipeline は `train_task_ids` を収集して leaderboard に渡す
2. **オプションの検索（project/tags）を “補助” として実装**

   * ただし検索は「誤集計」リスクがあるので、デフォルトは task_id が堅い
3. **leaderboard に “検証情報” を出す**

   * 集計対象の task_id リストを artifact として保存
   * 集計対象の `split_hash` / `processed_dataset_id` が一致しているかチェックし、違う場合は “比較不可” として除外 or 警告を出す

---

## C. 比較可能性の崩壊（スプリットや前処理のfitが揺れる）

### 起こりうること

* preprocess で split を作るのに、train でも split を作ってしまう
* train で再fitしてしまい、推論時のskew（学習・推論で前処理が一致しない）が起こる
* 同じdataset_idでもバージョン違いが混ざる

### 対応策（最重要）

1. **split は preprocess が生成し、train はそれを再利用する**（仕様で固定）

   * `split_hash` を必ず保持
2. **preprocess bundle を model_bundle に同梱**

   * train → infer で同じ bundle を使う（再fit禁止）
3. **model_bundle に schema を同梱**

   * 推論入力の列不足、型違いを検出して早期エラー

> “比較可能性”が崩れると、どんな可視化・leaderboardも意味がなくなるので、ここが最重要です。

---

## D. ClearML UI の “HyperParameters汚染” と “情報過多”

### 起こりうること

* pipelineの全設定が各タスクのHyperParametersに混入して、非DSが「どれがこのタスクの設定？」となる
* trainタスクに図が多すぎて理解できない（SHAPや散布図が大量）

### 対応策

1. **connectするconfigを “タスク関係部分だけ” に限定する**

   * preprocess は preprocess.* だけ
   * train は train.* だけ
   * infer は infer.* だけ
2. **Plotsは “意思決定に必要なものだけ” を番号付きで表示**

   * `01_`, `02_` … で順序固定
3. **重い可視化は “オンデマンド”**

   * 例えばSHAPは `train.plot.shap=true` のときだけ
4. **Debug Samples は少量、データ本体は Artifact へ**

   * UIの見やすさを死守する

---

## E. ローカル主軸＋Agent/clone対応の“二重管理”問題

### 起こりうること

* ローカルでは動くが、Agentでは依存やentry_pointが違って動かない
* clone運用で repository/working_dir/entry_point がズレて失敗
* “どの実行モードで動かす設定？” がわからない

### 対応策

1. **execution mode を config の単一箇所で切替**

   * `run.clearml.execution = local | agent | clone`
2. **Agent用の “doctor” を必須化**

   * `python -m tabular_analysis.cli.doctor` で

     * 依存チェック
     * clearml接続
     * queue存在確認
     * template_task_id存在確認
3. **clone運用のときは set_script を必ず使い、configで指定可能にする**

   * `repository`, `branch`, `entry_point`, `working_dir` を config化
4. **requirementsを固定**

   * platform_version / solution_version を記録して再現性を担保

---

## F. 多前処理×多モデルでタスク数が爆発する

### 起こりうること

* grid が大きくなると ClearML のTaskが大量にできる
* “どれが今回の実行セット？” がわからない

### 対応策

1. **grid_run_id を導入し、全タスクにタグ付け**

   * `grid:<run_id>` タグ
2. **pipeline_run.json を必ず artifact として残す**

   * “今回の集合”が一瞬で追える
3. **事前に候補を絞る**（運用ガード）

   * preprocess候補は 2〜4 程度から開始
   * モデル候補も段階的に増やす
4. **leaderboard で top_k と “比較不可除外” を強制**

   * 失敗タスクや比較不可が混ざっても結論が壊れない

---

## G. 冗長ファイル増殖・“どこを触れば拡張できるか”が不明になる

### 起こりうること

* あれもこれも追加して、構造が増殖
* 何が共通で何が用途固有かが曖昧になり、保守が破綻

### 対応策

1. **拡張ポイントを “registry” に寄せる**（仕様の中核）

   * 新モデル → `registry/models.py` と `conf/group/model/*.yaml` だけ
   * 新前処理 → `registry/preprocessors.py` と `conf/group/preprocess/*.yaml` だけ
2. **デバッグ/実験コードは mainline へ入れない**

   * `experiments/` に隔離
3. **cleanup policy を運用に組み込む**

   * unused検出、削除タスク起票、TODOがないファイルは残さない
4. **レビューワーガイドで重要箇所を固定**

   * “このプロジェクトで重要な場所はここ” を明文化して迷いを無くす

---

# 2) この仕様の中で ml-platform の役割は何か？

結論：**ml-platform は「全ユースケース共通の “契約と実行基盤”」**です。
tabular-analysis（ml-solution）は **その契約の上に乗る“用途固有の実装”**です。

## 2.1 ml-platform が提供するもの（やるべきこと）

### 1) 実行モード共通化（local / agent / clone）

* **同じCLI/同じconfigで**実行モードを切り替える枠組み
* clone運用の `repository/branch/working_dir/entry_point` の扱いを統一

→ solution側が「ClearMLの罠」を毎回踏まなくて済む

---

### 2) ClearML の “標準API” と “UI契約を実装する道具”

solutionは「何を出すべきか（仕様）」を持ちますが、
platformはそれを **簡単に実装できる部品**を持ちます。

例：

* `task_factory.init_task(process, project_root, ...)`
* `log_hparams(task, cfg_subset)`（汚染防止）
* `log_properties(task, dict)`
* `upload_artifacts(task, files)`
* `log_plot(task, fig, title="01_...")`
* `dataset_helper.create_versioned_dataset(...)`
* `model_helper.register_model(...)`

---

### 3) Artifact/Versioning の共通ユーティリティ

* `manifest.json` の生成
* `config_hash/recipe_hash/split_hash` を作る関数
* `model_bundle` の標準ディレクトリ構造

→ solutionごとにメタデータ設計がブレない

---

### 4) registry の “型と作法” を固定

* registryをどう作るべきか（interface, typing）
* 例外の扱い（未登録モデル名など）
* registryのテストテンプレ

→ 拡張しても破綻しない

---

### 5) doctor / smoke test / codex_loop の基盤

* Agent実行で詰まりやすい箇所（queue, template_task, git, dependency）を検査
* codexが勝手にDONEにしない runner と、その運用規約

→ “大規模でも着実に進む” を支える

---

## 2.2 ml-platform が “やってはいけないこと”

* **tabular固有の処理ロジックを持たない**

  * 例：StandardScalerやLightGBMの具体実装は solution に置く
* 可視化・評価ルールを用途別に勝手に変えない
* solutionの事情でplatformを肥大化させない（多用途で破綻する）

---

## 2.3 ml-solution（tabular-analysis）が担うべきこと

* テーブルデータの具体：

  * スキーマ推定、前処理レシピ、モデル、可視化
* どの情報を ClearML UI のどこへ出すか（契約の具体）
* 多前処理×多モデル×多推論モードの “ユースケース価値” を提供する

---

# 3) この設計が「今後の事例の軸」になれる理由

* **独立タスク + leaderboard集計** は、今後

  * 多次元目的変数
  * 画像/時系列
  * 深層学習
    に拡張しても **構造が壊れにくい**
    （それぞれの domain でも “独立学習” と “集計比較” が基本だから）
* platform が “契約” を保持するため、用途が増えても ClearML運用がブレない
* registry が拡張点を固定するため、チームが増えても追加が安全

---

もしよければ次に、あなたの `ml-platform` にすでにある実装（関数名やモジュール構造）に合わせて、

* **platform側の期待API一覧（I/F契約）**
* tabular-analysis側が呼ぶ `platform.*` の具体呼び出し場所

を `docs/13_PLATFORM_API_CONTRACT.md` として追記する形で、仕様をさらに “実装に落ちた形” にできます。









了解です。**想定課題と対応策（リスク潰し込み）を指示ファイル群に組み込み**、さらに **Codex が既存の ml-platform / ml-solution の雛形（共通ユーティリティ）を探索・再利用しながら実装**できるように改良した **v4 ZIP** を作りました。

---

## ✅ ZIPダウンロードリンク（v4）

* [Download: tabular_analysis_polyrepo_pack_v4.zip](sandbox:/mnt/data/tabular_analysis_polyrepo_pack_v4.zip)

---

# v4で入れた改良（何が変わったか）

## 1) 想定課題→対応策を「契約」として追加

* `docs/09_RISKS_AND_MITIGATIONS.md` を追加

  * 独立タスク化の追跡性（manifest/properties/pipeline_run.json）
  * leaderboardの誤集計防止（split_hash/processed_dataset_id整合性チェック）
  * leak/skew排除（split再生成禁止・bundle同梱・逆変換）
  * UI汚染防止（hparams subset / plots最小 / heavy plot optional）
  * local→agent/cloneの落とし穴（doctor / set_script / queue確認）
  * grid爆発対策（grid_run_idタグ＋pipeline_run.json）
  * 増殖防止（registry集中＋cleanup）

## 2) Codexが **ml-platform を再利用**できるように明文化＋自動探索

* `docs/10_PLATFORM_TEMPLATE_USAGE.md` を追加（再利用の不変ルール）
* `tools/platform_scan.py`（platform探索→ `work/runs/_platform_scan.txt`）
* `tools/doctor_platform.py`（platform import準備チェック）

さらに、タスクの必須項目として：

* `Platform reuse checklist` を全タスクに追加（何を再利用したか/足りないか/移管候補）
* `Risks addressed` を全タスクに追加（A〜Gのどれを潰したか）

## 3) Codexが「勝手にDONE」にしない＆止まらず進む強化

* `tools/codex_loop/run.py` を強化

  * **RESULT: DONE** に加え、**NONCE貼り付け必須**
  * `must_change_globs`（デフォ `src/**`）未達ならDONE不可
  * verification失敗ならDONE不可
  * **platform_scan結果** と **前回失敗理由** を次プロンプトに注入
* `tools/codex_loop/selfcheck_codex_exec.sh` を **実行可能な形に修正**（stdin実行）

---

# 配置方法（既存フォルダにどう置くか）

あなたのワークスペースがこうなっている前提です：

```
<workspace>/
  ml-platform/
  ml-solution-template/
```

## 1) 既存の tabular-analysis を削除（混合を防止）

```bash
rm -rf <workspace>/ml-solution-template/usecases/tabular-analysis
```

## 2) ZIPを workspace 直下で展開（重要）

```bash
cd <workspace>
unzip /path/to/tabular_analysis_polyrepo_pack_v4.zip -d .
```

展開確認：

```bash
ls ml-solution-template/usecases/tabular-analysis
```

---

# 実行方法（Codexで開発を回す手順）

## 0) usecase に移動

```bash
cd <workspace>/ml-solution-template/usecases/tabular-analysis
```

## 1) venv & 依存（ローカル主軸）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements/base.txt

# solution を editable install（必須）
pip install -e .

# platform を editable install（必須：既存雛形再利用のため）
pip install -e ../../../ml-platform
```

## 2) ClearML（使う場合のみ初回）

```bash
clearml-init
```

## 3) codex exec 自己診断（必須）

```bash
bash tools/codex_loop/selfcheck_codex_exec.sh
```

## 4) platform 再利用準備チェック（推奨）

```bash
python tools/doctor_platform.py
python tools/platform_scan.py
```

## 5) Codexループ（まず1回だけ）

```bash
python tools/codex_loop/run.py --repo . --once
```

問題なければ連続：

```bash
python tools/codex_loop/run.py --repo .
```

---

# Codexが「着実に進める」ための見える化

* 進捗：`work/queue.json` の status が `todo → doing → done`
* 実行ログ：`work/runs/task_XXX/`

  * `prompt.txt`（渡した指示）
  * `codex_output.txt`（Codex出力）
  * `verification.txt`（検証結果）
* platform探索結果：`work/runs/_platform_scan.txt`

---

必要なら次に、あなたの **ml-platform 側の実装（実際のモジュール名/関数名）**に合わせて、`docs/10_PLATFORM_TEMPLATE_USAGE.md` の「期待API」を **“実在するAPIに完全一致する”**形に寄せた v4.1 も作れます。
その場合は `ml-platform/src` 配下の主要モジュール構成（ツリーでOK）を貼ってください。
