#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сверка всего банка с огласовщиком Dicta Nakdan.

Зачем это НЕ переогласовка
--------------------------
Огласовки словаря, спряжений и множественного числа добывались
словарями, таблицами форм и Академией — слово за словом, с перекрёстной
сверкой. Nakdan сильная машина, но не источник нормы, и класть его вывод
поверх выверенного нельзя: это шаг назад, даже когда он совпадает в
девяноста восьми случаях из ста.

Польза в РАСХОЖДЕНИЯХ. Ровно так уже сработали словари: сверка со
словарём форм дала 18 ошибок в спряжениях, сверка с ИРИС и hebrewerry —
пять в множественном числе. Здесь то же самое, только источник третий и
независимый.

Больше всего пользы там, где второго мнения у нас нет вовсе: 133
разговорные фразы, которые не смотрел никто.

Чего этот скрипт не делает
--------------------------
Ничего не меняет в данных. Он пишет отчёт, а решение по каждому
расхождению принимает человек: у Nakdan свои промахи, особенно на
именах, заимствованиях и сокращениях.

Запуск (нужна сеть; в песочнице разработки её нет):
    python3 tools/nakdan_sweep.py                 # всё
    python3 tools/nakdan_sweep.py --scope phrases # только фразы
    python3 tools/nakdan_sweep.py --limit 50      # проба
"""

import argparse
import os
import sys
import unicodedata
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import nakdan  # noqa: E402
import phrases  # noqa: E402
import syntax  # noqa: E402
from conjugations import CONJUGATIONS  # noqa: E402
from words import VOCAB, VERBS  # noqa: E402

REPORT = HERE.parent / "НЕСХОДИМОСТИ_NAKDAN.md"

SCOPES = ("all", "words", "verbs", "forms", "phrases", "syntax")


def norm(word):
    """Порядок огласовок при букве у разных источников разный.

    Тот же нормализатор, что в check_conjugations: без него отчёт полон
    расхождений, которых нет — строки отличаются только порядком
    комбинирующих знаков.
    """
    out = []
    for ch in word:
        if unicodedata.combining(ch):
            if out:
                out[-1] += ch
        else:
            out.append(ch)
    return "".join(g[0] + "".join(sorted(g[1:])) for g in out)


def collect(scope):
    """[(откуда, контекст, наш текст)] — по одной строке на сверку.

    Сверяем ЦЕЛЫМИ фразами, а не словами: Nakdan разбирает контекст, и
    отдельно взятое слово он огласует хуже, чем то же слово во фразе.
    Для словаря контекста нет по природе — там слово и есть строка.
    """
    items = []
    if scope in ("all", "words"):
        for cat, pairs in VOCAB.items():
            for ru, he in pairs:
                items.append((f"словарь/{cat}", ru, he))
    if scope in ("all", "verbs"):
        for cat, pairs in VERBS.items():
            for ru, he in pairs:
                items.append((f"глаголы/{cat}", ru, he))
        for root, data in CONJUGATIONS.items():
            items.append((f"инфинитив/{root}", data["ru"], data["inf"]))
    if scope in ("all", "forms"):
        for root, data in CONJUGATIONS.items():
            for tense in ("past", "present", "future"):
                for slot, form in data[tense].items():
                    if form:
                        items.append((f"{tense}/{root}", slot, form))
    if scope in ("all", "phrases"):
        for sit, item in phrases.all_phrases():
            for field in ("he", "he_f", "to_f"):
                text = item.get(field)
                # Фразы с пропуском не сверяем: вместо слова там метка,
                # и огласовщик честно попытается прочитать её как слово.
                # У таких фраз есть готовый пример — его и берём.
                if not text or phrases.SLOT in text:
                    continue
                items.append((f"фразы/{sit}", item["ru"], text))
            example = (item.get("example") or {}).get("he")
            if example:
                items.append((f"пример/{sit}", item["ru"], example))
    if scope in ("all", "syntax"):
        for ru, _en, right, _wrongs, frame in syntax.SENTENCES:
            items.append((f"собери/{frame}", ru, right))
    # Одинаковый текст сверять дважды незачем.
    seen, out = set(), []
    for where, label, he in items:
        if he in seen:
            continue
        seen.add(he)
        out.append((where, label, he))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=SCOPES, default="all")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    items = collect(args.scope)
    if args.limit:
        items = items[: args.limit]
    print(f"Строк к сверке: {len(items)}")

    texts = [he for _w, _l, he in items]

    def progress(done, total):
        if total and (done % 200 == 0 or done == total):
            print(f"  спрошено {done}/{total}…")

    theirs = nakdan.vocalize_many(texts, progress=progress)

    same, diff = 0, []
    for (where, label, ours), got in zip(items, theirs):
        if not got or nakdan.strip_niqqud(got) != nakdan.strip_niqqud(ours):
            # Согласные разошлись — значит служба не поняла строку
            # (сокращение, имя, опечатка на её стороне). Сравнивать
            # огласовки в таком случае бессмысленно.
            diff.append((where, label, ours, got, "не разобрано"))
            continue
        if norm(got) == norm(ours):
            same += 1
        else:
            diff.append((where, label, ours, got, "расходится"))

    by_kind = Counter(kind for *_r, kind in diff)
    by_where = Counter(where.split("/")[0] for where, *_r in diff)

    lines = [
        "# Расхождения с огласовщиком Nakdan", "",
        "Второе мнение, а не источник нормы. Наши огласовки выверены "
        "словарями, таблицами форм и Академией; здесь перечислено то, где "
        "независимая машина Бар-Иланского университета видит иначе.",
        "",
        "Каждая строка — повод перепроверить, а не готовое исправление. "
        "На пробе из тридцати фраз разошлось семь, и в шести случаях "
        "ошибся Nakdan, а не мы: «кассу» он прочитал как «кофе», «два» "
        "как «годы», а инфинитивы увёл не в тот биньян. Он силён в "
        "длинном тексте и слаб на короткой фразе без контекста — а у нас "
        "весь банк из коротких фраз.",
        "",
        "Поэтому читать отчёт снизу вверх: сперва те разделы, где у нас "
        "второго мнения нет вовсе (разговорные фразы), и только потом "
        "словарь и формы, выверенные по словарям.",
        "",
        f"Сверено строк: {len(items)}. Совпало: {same}. "
        f"Разошлось: {len(diff)}.", "",
        "| раздел | расхождений |", "|---|---|",
    ]
    for where, n in by_where.most_common():
        lines.append(f"| {where} | {n} |")
    lines += ["", "| вид | сколько |", "|---|---|"]
    for kind, n in by_kind.most_common():
        lines.append(f"| {kind} | {n} |")

    lines += ["", "## Построчно", "",
              "| где | что | у нас | у Nakdan | вид |", "|---|---|---|---|---|"]
    for where, label, ours, got, kind in diff:
        lines.append(f"| {where} | {label} | `{ours}` | `{got}` | {kind} |")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print()
    print(f"Совпало {same} из {len(items)}, расхождений {len(diff)}.")
    for where, n in by_where.most_common():
        print(f"  {where}: {n}")
    print(f"Отчёт: {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
