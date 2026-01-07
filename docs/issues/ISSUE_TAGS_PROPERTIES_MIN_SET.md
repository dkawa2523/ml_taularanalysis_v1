# [ISSUE] tags/propertiesの最小セット

- Status: 未決
- Related decisions: docs/issues/DECISIONS.md

## 背景

tags/propertiesは検索に効く一方、増やしすぎるとノイズになる。
試験段階では最小セットの候補を並走して比較したい。

## 現象 / 期待

- 現象: どのキーを最低限入れるべきかが未確定
- 期待: UI検索と運用負荷のバランスが良いセットを選びたい

## 影響範囲

- ClearML UI検索
- UI契約（最低限のproperties/tags）
- report/artifactへの情報分散

## いまの暫定対応

- ルールを固定せず、clearml_policyで切り替え

## 恒久対応案（候補）
- 案A: tags=[usecase_id, process], properties={usecase_id, dataset_id, model_id}
- 案B: tags=[usecase_id, phase], properties={usecase_id, run_id}
- 案C: tags=[], properties={usecase_id}（詳細はartifactに寄せる）

## 判定に必要な検証

- 検索性（usecase単位/工程単位で探せるか）
- 運用負荷（入力/維持コスト）
- UI契約の最低ライン

## 決定ログ（いつ/誰が/なぜ）
