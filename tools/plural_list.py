#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Список форм множественного числа для проверки носителем.

Таблицу в ВОПРОСЫ_ВАДИМУ.md не пишут руками: 119 строк, и при любой
правке в nouns.py список в файле разошёлся бы с тем, что спрашивает
приложение. Этот скрипт перезаписывает блок между маркерами.

Порядок — по цене ошибки: сперва то, где правило не работает
(исключения и другие основы), потом парные, потом обычные. Если Вадим
дойдёт только до первой части, проверено будет самое рискованное.

Запуск:  python3 tools/plural_list.py          # напечатать
         python3 tools/plural_list.py --write  # вписать в файл
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import nouns                                   # noqa: E402
import quiz                                    # noqa: E402

DOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                   "ВОПРОСЫ_ВАДИМУ.md")
START = "<!-- множественное: начало -->"
END = "<!-- множественное: конец -->"

CONSONANT_DOTS = "ּׁׂ"


def _dual(plural):
    clean = "".join(c for c in plural if c not in CONSONANT_DOTS)
    return clean.endswith("ַיִם")


def groups():
    """Слова по риску: чем правило слабее, тем выше в списке."""
    gloss = {c.he: c.ru for c in quiz.VOCAB_FLAT}
    out = {"suppletive": [], "exception": [], "dual": [], "plain": []}
    for he, (gender, plural) in nouns.NOUNS.items():
        if plural == nouns.COUNT_NONE:
            continue
        # Парное проверяем ПЕРВЫМ. Иначе группа выходит пустая: почти
        # все парные слова попутно меняют основу или расходятся с родом,
        # и они уезжали в соседние разделы, а «Парные — 0» в файле
        # выглядело так, будто их у нас нет вообще.
        if _dual(plural):
            key = "dual"
        elif he in nouns.SUPPLETIVE:
            key = "suppletive"
        elif he in nouns.EXCEPTIONS:
            key = "exception"
        else:
            key = "plain"
        out[key].append((he, plural, gender, gloss.get(he, "")))
    return out


TITLES = [
    ("dual", "Парные",
     "Окончание ־ַיִם, и основа у них тоже меняется. Заодно вопрос: "
     "не нужно ли их спрашивать иначе — они отвечают на «пара», а не "
     "на «много»."),
    ("suppletive", "Основа меняется целиком",
     "Здесь правило не помогает вообще. Если ошибка есть, она тут."),
    ("exception", "Окончание не по роду",
     "Род один, окончание от другого. Проверить и окончание, и огласовки."),
    ("plain", "Обычные",
     "Правило работает, но основа почти всегда меняется — вопрос в огласовках."),
]


def mark(plural):
    """Чем форма подтверждена. Словарь весомее: он даёт и гласные."""
    out = []
    if nouns.iris_checked(plural):
        out.append("ИРИС")
    k = nouns.skeleton_checked(plural)
    if k:
        out.append("пособие" + (" (ктив мале)" if k == "male" else ""))
    return ", ".join(out) or "—"


def table(rows):
    """Сперва то, что подтвердить было нечем.

    Сортировка по этому признаку, а не по алфавиту: если Вадим дойдёт
    только до середины таблицы, проверено окажется именно то, где я
    остался единственным источником.
    """
    out = ["| единственное | множественное | род | перевод | проверено | верно? |",
           "|---|---|---|---|---|---|"]
    rows = sorted(rows, key=lambda r: (mark(r[1]) != "—", r[3]))
    for he, plural, gender, ru in rows:
        out.append(f"| {he} | {plural} | {gender} | {ru} | {mark(plural)} |  |")
    return "\n".join(out)


def render():
    g = groups()
    total = sum(len(v) for v in g.values())
    rows_all = [r for v in g.values() for r in v]
    iris = sum(1 for r in rows_all if nouns.iris_checked(r[1]))
    book = sum(1 for r in rows_all if nouns.skeleton_checked(r[1]))
    either = sum(1 for r in rows_all
                 if nouns.iris_checked(r[1]) or nouns.skeleton_checked(r[1]))
    parts = [
        f"Всего форм: **{total}**. Подтверждено носителем: **0**.",
        "",
        f"Машинная сверка с двумя источниками:",
        "",
        f"- **ИРИС** (иврит-русский словарь Подольского) — **{iris}** "
        f"форм сошлись по всем трём признакам: род статьи, согласный "
        f"скелет и гласные по русской транскрипции словаря.",
        f"- **Рабочая тетрадь «מפה לשם 1»** — **{book}** форм совпали "
        f"согласным скелетом. Огласовки она не подтверждает: написана "
        f"без них.",
        "",
        f"Итого чем-то подтверждено **{either}**, не подтверждено ничем "
        f"**{total - either}**. Непроверенные идут первыми в каждой "
        f"таблице — если дойдёте только до половины, проверено окажется "
        f"именно то, где я остался единственным источником.",
        "",
    ]
    for key, title, note in TITLES:
        rows = g[key]
        if not rows:
            continue
        parts += [f"### {title} — {len(rows)}", "", note, "", table(rows), ""]
    parts.append("Пересобрать список: `python3 tools/plural_list.py --write`")
    return "\n".join(parts)


def main():
    body = render()
    if "--write" not in sys.argv:
        print(body)
        return 0
    with open(DOC, encoding="utf-8") as f:
        doc = f.read()
    if START not in doc or END not in doc:
        print("В файле нет маркеров", START, END)
        return 1
    head, rest = doc.split(START, 1)
    _old, tail = rest.split(END, 1)
    with open(DOC, "w", encoding="utf-8") as f:
        f.write(head + START + "\n\n" + body + "\n\n" + END + tail)
    print("Вписано в ВОПРОСЫ_ВАДИМУ.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
