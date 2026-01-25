# ClearML UI レイアウト候補（試験段階の比較用）

このドキュメントは、試験段階で「どのUI設計が扱いやすいか」を比較するための候補集です。
本番では1案に固定しますが、試験段階では複数案を回して、開発者と利用者の合意を形成します。

## 重要：固定する範囲と固定しない範囲

- 上位階層（組織やドメイン）は利用者が決める
- それ以下は `<solution_root>/<usecase_id>/...` の形に寄せる（候補は複数）

---

## 案A：process group をプロジェクトで分ける（config-driven）

```
<ROOT>/<solution_root>/<usecase_id>/01_Datasets
<ROOT>/<solution_root>/<usecase_id>/02_Preprocess
<ROOT>/<solution_root>/<usecase_id>/03_TrainModels
<ROOT>/<solution_root>/<usecase_id>/00_Pipelines（leaderboard もここに配置）
<ROOT>/<solution_root>/<usecase_id>/05_Infer
<ROOT>/<solution_root>/<usecase_id>/00_Pipelines
<ROOT>/<solution_root>/<usecase_id>/Misc
```

メリット：
- 非DSが工程ごとに辿りやすい
- 既存のUI契約と整合しやすい

デメリット：
- プロジェクトが増える（見慣れないとツリーが長い）

---

## 案B：工程をタグで分け、プロジェクトは用途だけ

```
<ROOT>/<solution_root>/<usecase_id>
```

メリット：
- ツリーが短くシンプル

デメリット：
- 目的の工程タスクを探すにはタグフィルタ必須（非DSにはハードル）

---

## 案C：用途＋目的（train/ops）だけに絞る

```
<ROOT>/<solution_root>/<usecase_id>/train
<ROOT>/<solution_root>/<usecase_id>/ops
```

メリット：
- ツリーは短く、工程も大きくは分かる

デメリット：
- dataset/preprocess/infer の導線が弱くなる可能性

---

## 推奨（試験段階の進め方）

まずは案Aでリハーサルし、非DSの観点で「迷わないか」を確認します。
もし「プロジェクト数が多すぎる」フィードバックが強い場合、案Cへ寄せる検討をします。

比較結果は `docs/issues/` に Issue形式で残し、最終決定を記録してください。
