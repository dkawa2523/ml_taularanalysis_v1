# T073 ClearML Script の repository/branch が platform を指してしまう不具合を修正（solution repo を指す）

## 背景（症状）
現状 `run.clearml.execution=pipeline_controller` で pipeline を起動すると、ClearML に作成される pipeline task の Script が:

- repository = `https://github.com/dkawa2523/ml_platform_v1`
- branch = `ml_platform_v1/master`

になってしまい、Agent は platform repo を clone して `python -m tabular_analysis.cli ...` を実行しようとして **即死（ModuleNotFoundError）**します。
結果として pipeline controller が DAG を作る前に落ち、子タスク（preprocess/train/leaderboard）が作られません。

このタスクでは **Script の repository/branch を solution repo（= このリポジトリ）に合わせる**ように修正します。

---

## 目的
- ClearML の Task Script (repository/branch) が「実行すべきコードが存在する repo」を常に指す
- polyrepo 前提で、platform repo と solution repo を混同しない

---

## 実装方針（重要）
- platform_adapter が `Task.set_script(...)` で repository/branch を上書きしている箇所があるはずなので、そこを修正する
- 既定値を platform repo に固定するのは NG
- **既定は “auto”**（git から検出）にし、必要なら config で上書き可能にする

---

## 変更内容
### 1) 新しい設定キー（Hydra）
`conf/run/base.yaml` など適切な場所に追加：

- `run.clearml.code_repository`: `"auto"` または URL
- `run.clearml.code_branch`: `"auto"` または ブランチ名

設計意図:
- `"auto"` のときは、リポジトリルート（`conf/` があるディレクトリ）を基準に `git` から検出する
- 明示指定された場合はそれを優先

### 2) git から repo/branch を検出するヘルパ追加
`src/tabular_analysis/platform_adapter.py` 内に、以下を満たす関数を追加（場所は任意だが adapter 内で完結させる）:

- `detect_git_repository_url(repo_root: Path) -> str | None`
  - `git -C <root> remote get-url origin`
  - SSH形式 `git@github.com:org/repo.git` は `https://github.com/org/repo` に正規化（`.git` は削る）
- `detect_git_branch(repo_root: Path) -> str | None`
  - `git -C <root> rev-parse --abbrev-ref HEAD`
  - `HEAD` の場合は None でよい（commit hash は ClearML が持つため）

### 3) Task.set_script を呼ぶ箇所の修正
grep から `Task.set_script` を呼ぶ箇所がありそう（例: 1270〜1285付近）。
ここで決める repository/branch を次のルールにする:

- `run.clearml.code_repository == "auto"` → git検出結果を使う（Noneなら上書きしない）
- `"auto"` 以外 → その値を使う
- `run.clearml.code_branch` も同様

**注意:** 現状 branch に `ml_platform_v1/master` のような “repo名を含む” 文字列が入っているので、branch は “純粋なブランチ名” に修正する。

---

## 受け入れ基準（Acceptance Criteria）
- `python -m tabular_analysis.ops.print_clearml_identity ...` もしくは同等の確認コマンドで、repository/branch が solution を指していることが確認できる
- ClearML に新しく作る pipeline task の `Task.get_script()` が **ml_platform_v1 ではない**
- `python -m compileall -q src` が通る

---

## テスト（ローカル）
- `python -m compileall -q src`
- （任意）ClearML 接続できる環境では、pipeline を起動して `Task.get_script()` を確認

---

## 補足（調査のヒント）
- `src/tabular_analysis/platform_adapter.py` の `Task.set_script` を呼ぶ箇所が “犯人” です
- `manage_clearml_templates.py` が template task の repository を検証している場合、後続タスク（T076）で整合させます
