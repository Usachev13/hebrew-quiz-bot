# -*- coding: utf-8 -*-
"""Проверка речевых моделей.

Появилась потому, что ошибки здесь дороже, чем в словаре: фразу человек
произнесёт вслух и запомнит именно так. Проверяется то, что можно
проверить машиной; правильность самого иврита проверяет носитель.

    python3 tools/check_phrases.py
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import phrases          # noqa: E402
import quiz             # noqa: E402
from translit import translit   # noqa: E402

HEB = re.compile(r"[֐-׿]")
CYR = re.compile(r"[а-яА-ЯёЁ]")


def check():
    problems = []
    cats = {c for _, _, c in quiz.POOLS["vocab"]}

    for sit, items in phrases.PHRASES.items():
        if sit not in phrases.SITUATIONS:
            problems.append(f"ситуация {sit} без названия")
        for i, p in enumerate(items):
            where = f"{sit}[{i}] «{p['ru']}»"

            # 1. Слот должен быть в обеих строках или ни в одной: иначе
            #    подстановка развалит фразу для половины пользователей.
            has_ru = phrases.SLOT in p["ru"]
            has_he = phrases.SLOT in p["he"]
            if has_ru != has_he:
                problems.append(f"{where}: слот есть только с одной стороны")
            if p.get("he_f") and (phrases.SLOT in p["he_f"]) != has_he:
                problems.append(f"{where}: слот разошёлся между родами")

            # 2. Заявленный слот обязан существовать в словаре, иначе
            #    подставлять будет нечего.
            if p.get("slot"):
                if not has_he:
                    problems.append(f"{where}: категория задана, а слота нет")
                elif p["slot"] not in cats:
                    problems.append(f"{where}: нет такой категории — {p['slot']}")

            # 3. Иврит должен быть ивритом, а перевод — русским.
            if not HEB.search(p["he"]):
                problems.append(f"{where}: в поле he нет ивритских букв")
            if not CYR.search(p["ru"]):
                problems.append(f"{where}: в переводе нет кириллицы")
            if p.get("he_f") and not HEB.search(p["he_f"]):
                problems.append(f"{where}: в женской форме нет ивритских букв")

            # 4. Женская форма, совпадающая с мужской, — почти наверняка
            #    недосмотр: её тогда незачем указывать.
            if p.get("he_f") and p["he_f"] == p["he"]:
                problems.append(f"{where}: женская форма совпадает с мужской")

            # 5. Огласовки. Без них чтение не построится, а фраза
            #    показывается новичку.
            marks = sum(1 for ch in p["he"] if "֑" <= ch <= "ׇ")
            if marks < 2:
                problems.append(f"{where}: почти нет огласовок")

            # 6. Ключ карточки должен находиться обратным поиском.
            cid = phrases.card_id(sit, i)
            if phrases.by_id(cid) is not p:
                problems.append(f"{where}: ключ {cid} не находит модель")

            # 7. Строка для озвучки: без слота, без висящих знаков и не
            #    пустая. По ней ищется звуковой файл, и разойдись она с
            #    той, что записал генератор, звука не будет молча.
            for fem in (False, True):
                if fem and not p.get("he_f"):
                    continue
                sp = phrases.spoken(p, fem)
                tag = "жен." if fem else "муж."
                if phrases.SLOT in sp:
                    problems.append(f"{where} ({tag}): слот остался в озвучке")
                if re.search(r"\s[,?!.]", sp):
                    problems.append(f"{where} ({tag}): пробел перед знаком")
                if not sp.strip():
                    problems.append(f"{where} ({tag}): строка озвучки пустая")

            # 8. Чтение должно строиться — на нём держится подсказка.
            try:
                r = translit(p["he"].replace(phrases.SLOT, ""))
                if not r.strip():
                    problems.append(f"{where}: чтение вышло пустым")
            except Exception as e:
                problems.append(f"{where}: чтение падает — {e}")

    return problems


def main():
    st = phrases.stats()
    print(f"моделей {st['total']} в {st['situations']} ситуациях; "
          f"по роду говорящего {st['gendered']}, со слотом {st['slotted']}")
    problems = check()
    for p in problems:
        print("  СБОЙ", p)
    if not problems:
        print("  Машинных ошибок нет. Иврит должен проверить носитель.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
