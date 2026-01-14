# T081 ClearML Configuration → Hyperparameters をカテゴリ分割して表示する（inputs/dataset/preprocess/model/eval/pipeline/clearml）

## 背景（課題）
現状、ClearML の CONFIGURATION → HYPERPARAMETERS に **GENERAL しか出ず**、
- 入力
- データセット
- 前処理
- モデル
- 評価
- pipeline
- clearml連携
が混在して見づらい状態です。

---

## 目的
- ClearML UI 上で “設定の見通し” を良くする（非DSも使えるように）
- Local/Agent どちらでも同じ区分で表示
- 新しい設定項目が増えても、開発者が **conf/ を編集するだけで** 表示対象を調整できる

---

## 実装方針
### 1) hyperparameters の “セクション定義” を conf/ に追加
例: `conf/clearml/hyperparams_sections.yaml`（新設）

```yaml
run:
  clearml:
    hyperparams:
      sections:
        inputs:
          - run.usecase_id
          - run.output_dir
        dataset:
          - data.raw_dataset_id
          - data.processed_dataset_id
        preprocess:
          - preprocess.variant
          - preprocess.*
        model:
          - model.variant
          - model.params
          - model.*
        eval:
          - eval.*
        pipeline:
          - pipeline.grid.*
          - pipeline.ensemble.*
        clearml:
          - run.clearml.*
```

ポイント:
- `foo.*` は「foo配下を dict として丸ごと」接続できるようにする（実装で対応）
- 既存の config 構造に合わせて dotpath は調整する（本タスクで repo を見て最適化）

### 2) dotpath 抽出ヘルパを実装
`src/tabular_analysis/clearml/hyperparams.py` などを追加し、以下を提供:

- `extract_by_dotpaths(cfg, dotpaths: list[str]) -> dict`
  - OmegaConf / dict どちらでも動く
  - `a.b` は scalar を拾う
  - `a.*` は a 配下 dict を拾う（無ければ skip）
  - 抽出結果は “ClearMLに出して良い最小限” のみ

### 3) Task.init 後に connect する
platform_adapter の ClearML init の流れで:

- `task.connect(section_dict, name="dataset")` のように **section ごと**に connect する
- GENERAL（旧）に全部押し込む動きはやめる（後方互換が必要なら GENERAL は “要約” のみにする）

> 注意: ClearML SDK で `task.connect` の引数が微妙に異なる可能性があるので、実際の SDK signature に合わせる。
> うまくいかない場合は `task.connect_configuration` ではなく **task.connect** を優先。

---

## 受け入れ基準（Acceptance Criteria）
- ClearML UI の HYPERPARAMETERS に:
  - inputs / dataset / preprocess / model / eval / pipeline / clearml
  が分かれて表示される
- `conf/clearml/hyperparams_sections.yaml` を編集すると表示対象が変わる
- `python -m compileall -q src` が通る

---

## Update (2026-01-13)
- `conf/clearml/hyperparams_sections.yaml` を追加し、sections を外部定義に移した
- `clearml/hparams.py` が sections をロードして dotpath 抽出 + 明示値の上書きで connect するように変更
- `run.clearml.code_ref.*` は legacy の `run.clearml.code_*` へフォールバックする実装を追加

---

## テスト
- `python -m compileall -q src`
- （ClearML接続あり）preprocess/train など任意タスクを1つ実行し UI を確認
