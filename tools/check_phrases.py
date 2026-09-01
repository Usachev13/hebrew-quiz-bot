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

# Приметы обращения на «ты». Мужские и женские формы местоимения и
# притяжательных окончаний: если они есть, фраза зависит от пола
# собеседника, а не говорящего.
YOU_M = ("אַתָּה", "שֶׁלְּךָ", "לְךָ", "אִתְּךָ", "אוֹתְךָ")
YOU_F = ("אַתְּ", "שֶׁלָּךְ", "לָךְ", "אִתָּךְ", "אוֹתָךְ", "תִּכְתְּבִי", "עוֹשָׂה")
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

            # 4. Форма, совпадающая с основной, — почти наверняка
            #    недосмотр: её тогда незачем указывать.
            if p.get("he_f") and p["he_f"] == p["he"]:
                problems.append(f"{where}: форма говорящей совпадает с мужской")
            if p.get("to_f") and p["to_f"] == p["he"]:
                problems.append(f"{where}: форма к женщине совпадает с мужской")

            # 4б. Две оси нельзя мешать в одной модели: если фраза
            #     зависит и от говорящего, и от собеседника, форм должно
            #     быть четыре, а такого случая у нас нет — значит это
            #     ошибка разметки.
            if p.get("he_f") and p.get("to_f"):
                problems.append(f"{where}: заданы обе оси рода сразу")

            # 4в. Обращение на «ты» без поля to_f — след того, что форму
            #     положили не в ту ось. Ровно так и случилось в первый
            #     раз: «מֵאַיִן אַתְּ?» лежало в he_f, то есть женщине
            #     показывали бы её при разговоре с мужчиной.
            #
            #     Опираемся на сам иврит, а не на текст примечания:
            #     первая версия этой проверки искала слово «собеседник» в
            #     вольном пояснении и промолчала, стоило пояснение
            #     переписать.
            if any(m in p["he"] for m in YOU_M) and not p.get("to_f"):
                problems.append(f"{where}: обращение на «ты», а формы to_f нет")
            if p.get("to_f") and not any(m in p["to_f"] for m in YOU_F):
                problems.append(f"{where}: в to_f нет женского обращения")

            # 5. Огласовки. Без них чтение не построится, а фраза
            #    показывается новичку.
            marks = sum(1 for ch in p["he"] if "֑" <= ch <= "ׇ")
            if marks < 2:
                problems.append(f"{where}: почти нет огласовок")

            # 6. Ключ карточки должен находиться обратным поиском.
            cid = phrases.card_id(sit, i)
            if phrases.by_id(cid) is not p:
                problems.append(f"{where}: ключ {cid} не находит модель")

            # 6б. У фразы со слотом обязан быть пример. Без него диктор
            #     произносит обрубок: «אֲנִי גָּר בְּ» — предлог «в» без
            #     того, к чему он относится.
            if p.get("slot"):
                ex = p.get("example")
                if not ex:
                    problems.append(f"{where}: слот есть, а примера нет")
                else:
                    if phrases.SLOT in ex.get("he", ""):
                        problems.append(f"{where}: в примере остался слот")
                    if not HEB.search(ex.get("he", "")):
                        problems.append(f"{where}: в примере нет иврита")
                    if not CYR.search(ex.get("ru", "")):
                        problems.append(f"{where}: у примера нет перевода")
                    # Если сама фраза меняется по говорящему, пример тоже
                    # обязан: иначе женщина услышит мужскую форму.
                    if p.get("he_f") and not ex.get("he_f"):
                        problems.append(f"{where}: у примера нет женской формы")

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
