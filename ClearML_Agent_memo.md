# ClearML Agent 運用メモ（Tabular Analysis）

本ドキュメントは、**現状の安定運用を前提**に、ClearML 実行の設定・運用・更新手順・トラブル回避のガイドラインをまとめたものです。

---

## 1. 現状の運用方針（必ず守る）

- **dataset_register はローカル実行が前提**
  - Agent 実行ではデータファイルが repo 内に存在せず失敗するケースが多いため
- **学習 pipeline は ClearML Agent 実行**
  - 実行時に **queue を必ず指定**する（例: `services`）
  - **queue 名は固定しない**（環境により変わるため）

---

## 2. 実行時に必須な入力（失敗防止）

### pipeline 実行時に必ず指定

- `data.raw_dataset_id=<dataset_register で取得した ID>`
- `run.usecase_id=<dataset_register 実行時と同じ>`
- `run.clearml.queue_name=<実行対象 queue>`

> `pipeline.run_dataset_register=false` の場合、`data.raw_dataset_id` が **必須**。未指定は必ず失敗。

---

## 3. ClearML UI 上での標準動線（推奨フロー）

### A) dataset_register（ローカル）

1. ローカルから実行
2. `outputs/<timestamp>/01_dataset_register/out.json` で `raw_dataset_id` を確認
3. ClearML UI でも Dataset 登録を確認

### B) pipeline（Agent）

1. ClearML UI で **template:true の pipeline テンプレ**を探す
2. **Clone**
3. パラメータを更新（必須項目を反映）
4. **Queue を `services` 等に指定して enqueue**

---

## 4. テンプレート運用ルール

- **clone 元は必ず `template:true` のタスクのみ**
- **clone した実行タスクからは `template:true` を外す**
  - テンプレ管理に混ざるのを防ぐ
- **旧テンプレは自動で deprecated**
  - `template:deprecated` が付いたテンプレは利用禁止

---

## 5. Pipelines タブに表示される条件

- pipeline controller タスクは **usecase 配下の project**に配置する
- project に **system tag `pipeline`** が付いていること
- `.pipelines` など hidden project は使用しない

---

## 6. 学習処理を更新する場合の対応

### 6.1 コード更新後

1. Git で commit & push
2. テンプレ再適用
   ```bash
   PYTHONPATH=src python3 -m tabular_analysis.ops.manage_clearml_templates --apply
   ```
3. UI 上で **template:true の新しいテンプレ**から clone

### 6.2 既存テンプレの更新後

- **旧テンプレは deprecated にする**（自動付与される想定）
- 実行は **常に最新の template:true から clone**

---

## 7. ClearML 設定を変更する場合

### 7.1 queue を変える場合

- **テンプレに固定しない**
- **実行時に `run.clearml.queue_name` を指定**

### 7.2 project 構成を変える場合

- project layout は `conf/clearml/project_layout.yaml` に従う
- pipeline の controller が **usecase/00_Pipelines** に入ることを確認

---

## 8. Agent 先（実行環境）を変える場合

### 8.1 Agent を変更する時の注意点

- **queue 名が変わる可能性がある** → 実行時の指定を必ず変える
- **データファイルが Agent から参照できるか確認**
  - dataset_register はローカルで固定
  - pipeline は raw_dataset_id を渡すことで OK

### 8.2 Agent 依存を避けるための確認

- `run.clearml.env.bootstrap=uv`
- apt パッケージは task 側で指定（例: `libgomp1`）
- Agent 側の環境差異に依存しないよう、テンプレ管理で統一

---

## 9. よくある失敗と再発防止

### 失敗例1: dataset_register を agent で実行
- **原因:** データファイルが repo に無い
- **対策:** dataset_register は必ずローカル

### 失敗例2: raw_dataset_id 未指定
- **原因:** `pipeline.run_dataset_register=false` なのに ID 未入力
- **対策:** pipeline 実行時に必ず指定

### 失敗例3: queue 未指定
- **原因:** pipeline step に queue が割り当てられず失敗
- **対策:** 実行時に `run.clearml.queue_name` を指定

### 失敗例4: template ではないタスクを clone
- **原因:** 古い clone タスクに依存し誤作動
- **対策:** `template:true` のみ clone

---

## 10. 実行チェックリスト（簡易）

- [ ] dataset_register はローカルで完了
- [ ] raw_dataset_id を取得済み
- [ ] pipeline clone 元は template:true
- [ ] run.usecase_id を dataset_register と合わせた
- [ ] run.clearml.queue_name を実行時に指定した

---

## 11. 将来改善（任意）

- **dataset_register → pipeline を自動連携するスクリプトの追加**
  - out.json から raw_dataset_id を自動取得して enqueue
- **実行時に必須パラメータ未指定なら UI で警告する仕組み**

---

## 12. メモ（現状確認済みの事実）

- pipeline 実行は `services` queue で成功
- dataset_register はローカル実行が安定
- pipeline タスクは usecase 配下に配置する運用が安定

---

必要に応じて、このメモを運用ルールとして README / docs に統合してください。
