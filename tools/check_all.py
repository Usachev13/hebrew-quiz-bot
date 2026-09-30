#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Все проверки разом, с честным итогом.

Зачем отдельный скрипт
----------------------
Проверок стало полтора десятка, и прогонять их я привык одной строкой в
оболочке с фильтром по слову «СБОЙ». Фильтр оказался дырявым: часть
проверок сообщает о находках через «✗», и такие сбои молча проходили
мимо. Так пропустили семь разговорных выражений без английского
перевода — проверка их называла, а прогон говорил «всё прошло».

Здесь итог определяется КОДОМ ВОЗВРАТА, а не разбором вывода. Проверка,
которая нашла ошибку, обязана вернуть ненулевой код; это единственный
надёжный признак, и он не зависит от того, каким значком она печатает.

Отдельно учитываются проверки, которым нужны ключи (Azure, модель
разговора): без ключей они не могут ничего сказать, и считать их
падение сбоем неправильно — но и молчать о них нельзя.

Запуск:
    python3 tools/check_all.py
    python3 tools/check_all.py --quiet     # только итог
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Проверкам ниже нужен ключ, которого в разработке обычно нет. Их
# отсутствие ключа — не сбой данных, а отсутствие доступа.
NEEDS_KEYS = {"check_azure.py", "check_dialog_key.py"}

# Не проверки, а инструменты.
SKIP = {"check_all.py"}

# Не проверки, а инструменты, которые ходят в платные службы. Запускать
# их в общем прогоне значит тратить деньги при каждом «всё ли цело».
TOOLS = {"dialog_compare.py", "nakdan_sweep.py"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="только итог")
    args = ap.parse_args()

    scripts = sorted(p.name for p in HERE.glob("check_*.py")
                     if p.name not in SKIP | TOOLS)
    scripts.append("test_api.py")

    failed, skipped = [], []
    for name in scripts:
        path = HERE / name
        if not path.exists():
            continue
        res = subprocess.run([sys.executable, str(path)],
                             capture_output=True, text=True, cwd=str(ROOT))
        ok = res.returncode == 0
        if not ok and name in NEEDS_KEYS:
            skipped.append(name)
            print(f"  … {name:24} пропущено: нет ключа")
            continue
        print(f"{'  ✓' if ok else '  ✗'} {name}")
        if not ok:
            failed.append(name)
            if not args.quiet:
                tail = (res.stdout + res.stderr).strip().splitlines()
                for line in tail[-12:]:
                    print(f"      {line}")

    print()
    total = len(scripts) - len(skipped)
    if failed:
        print(f"СБОЙ: {len(failed)} из {total} — {', '.join(failed)}")
        return 1
    print(f"Все проверки прошли: {total}"
          + (f" (пропущено без ключей: {len(skipped)})" if skipped else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
