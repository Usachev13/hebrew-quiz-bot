#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка данных о сокращениях.

Главное, за чем следит: чтобы в расшифровки не заползли огласовки.
Они там не случайно отсутствуют — так сокращения выглядят в жизни, и
навык именно читать неогласованное. Но соблазн «дополнить» велик, а
огласовки для этих слов взять негде: половины нет в доступных словарях,
и расставлять их по памяти означало бы ровно ту ошибку, которой в этом
разделе не должно быть по построению.

Ещё проверяет, что каждая запись полная и что у каждой указан источник
расшифровки, а не «кажется, так».

Запуск:  python3 tools/check_abbrev.py
"""

import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import abbrev                                    # noqa: E402
import quiz                                      # noqa: E402

SOURCES = {"поиск", "общее"}
GERSH = "\"'׳״."


def check_no_niqqud():
    """В расшифровках не должно быть огласовок — см. docstring модуля."""
    bad = []
    for a, full, _ru, _where, _src in abbrev.ITEMS:
        if any(unicodedata.combining(c) for c in full):
            bad.append(f"{a}: в расшифровке «{full}» появились огласовки")
    return "огласовки в расшифровке", bad


def check_complete():
    """Пустых полей быть не должно: разбор показывает все три."""
    bad = []
    for item in abbrev.ITEMS:
        a, full, ru, where, src = item
        for name, val in (("расшифровка", full), ("перевод", ru),
                          ("где встречается", where)):
            if not (val or "").strip():
                bad.append(f"{a}: пустое поле «{name}»")
    return "неполная запись", bad


def check_source():
    """У каждой расшифровки должна быть пометка, откуда она."""
    bad = [f"{i[0]}: источник «{i[4]}»" for i in abbrev.ITEMS
           if i[4] not in SOURCES]
    return "расшифровка без источника", bad


def check_looks_like_abbrev():
    """Сокращение обязано содержать гершаим или точку.

    Иначе это просто слово, и в этом разделе ему не место.
    """
    bad = [f"{i[0]}: не похоже на сокращение" for i in abbrev.ITEMS
           if not any(c in GERSH for c in i[0])]
    return "не похоже на сокращение", bad


def check_expansion_differs():
    """Расшифровка не может совпадать с сокращением."""
    bad = [i[0] for i in abbrev.ITEMS
           if re.sub(r"[^֐-׿]", "", i[0]) ==
              re.sub(r"[^֐-׿]", "", i[1])]
    return "расшифровка совпала с сокращением", bad


def check_unique():
    bad = []
    seen = set()
    for i in abbrev.ITEMS:
        if i[0] in seen:
            bad.append(i[0])
        seen.add(i[0])
    return "сокращение встречается дважды", bad


def check_cards():
    """Карточки должны собраться на всё показываемое."""
    pool = quiz.POOLS["abbrev"]
    bad = []
    if len(pool) != len(abbrev.all_items()):
        bad.append(f"карточек {len(pool)}, записей {len(abbrev.all_items())}")
    for c in pool:
        if not c.he.strip():
            bad.append(f"{c.ru}: пустой ответ")
        a = c.cid.split(":", 1)[1] if ":" in c.cid else ""
        if abbrev.meaning(a) is None:
            bad.append(f"{c.ru}: разбор не найдёт запись по ключу «{a}»")
    return "карточки не сходятся с данными", bad


def check_unconfirmed_hidden():
    """Неподтверждённое человеку не показываем."""
    shown = {i[0] for i in abbrev.all_items()}
    bad = [u[0] for u in abbrev.UNCONFIRMED if u[0] in shown]
    return "неподтверждённое сокращение попало в показ", bad


CHECKS = [check_no_niqqud, check_complete, check_source,
          check_looks_like_abbrev, check_expansion_differs, check_unique,
          check_cards, check_unconfirmed_hidden]


def main():
    failed = 0
    for check in CHECKS:
        title, bad = check()
        if bad:
            failed += 1
            print(f"✗ {title}: {len(bad)}")
            for line in bad[:12]:
                print("    ", line)
        else:
            print(f"✓ {title} — не найдено")
    by_src = {}
    for i in abbrev.ITEMS:
        by_src[i[4]] = by_src.get(i[4], 0) + 1
    print(f"\nсокращений: {len(abbrev.ITEMS)} "
          f"(подтверждено поиском {by_src.get('поиск', 0)}, "
          f"общеизвестных {by_src.get('общее', 0)}); "
          f"ждут проверки: {len(abbrev.UNCONFIRMED)}")
    print("Правильность расшифровок машина не проверяет — только полноту.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
