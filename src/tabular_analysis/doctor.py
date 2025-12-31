"""Pre-flight checks (doctor).

T010 で実装予定。
- ml_platform が import できるか
- ClearML 接続（有効時）
- queue 名、clone template task_id の妥当性
- UI契約（必須 properties/tags/artifacts）チェック用の入口
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
