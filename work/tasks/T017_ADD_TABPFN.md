# T017 TabPFN 追加（optional + 重み未取得時の扱いを契約化）

## Objective
- 小規模データで強い可能性がある TabPFN を、**optional** として追加する
- 「重みが無い / DLできない」場合でも、追跡性を崩さずに **失敗として記録できる**ようにする

---

## Scope
1) `pyproject.toml` に extras を追加
   - 例: `[project.optional-dependencies] tabpfn = ["tabpfn>=0.1"]`
2) `conf/group/model/tabpfn.yaml` を追加（回帰/分類の両対応）
3) `registry/models.py` を拡張
   - tabpfn が無ければ T016 と同様に明確な例外
   - 重みが必要な場合:
     - `auto_download=false` がデフォルト（業務環境で勝手に外部DLしない）
     - `auto_download=true` の場合はライブラリの推奨手順で取得
     - 取得できなければ「失敗として out/manifest に残る」ようにする（try/exceptで握りつぶさず、契約化）
4) `tools/tests/check_optional_models.py` を拡張して tabpfn も扱えるようにする

---

## Acceptance Criteria
- tabpfn が無い環境で `group/model=tabpfn` を選んだ場合、インストール手順が明確なエラーになる
- tabpfn がある環境では instantiate できる（重み要件は config に従って扱う）
- check_optional_models.py が `--models tabpfn` で通る

---

## Verification（runner 側で実行）
- `python tools/tests/check_optional_models.py --models tabpfn`
