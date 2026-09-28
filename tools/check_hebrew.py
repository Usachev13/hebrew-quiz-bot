#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка ивритских данных на соглашения огласовки.

Зачем
-----
Ошибка в огласовке не ломает ничего: слово выводится, звук проигрывается,
проверка ответа проходит — сравнение идёт по согласным. Её видит только
человек, который читает, и принимает за правду. То есть цена ошибки не
«приложение упало», а «выучил неправильно».

Первая находка этой проверки: генератор спряжений превращал последнюю
букву в конечную, но шва к конечному кафу не дописывал. Получалось
«הוֹלֵך» и «הָלַך» — «он идёт» и «он пошёл», два из самых частых слов
языка, оба с опечаткой. В словаре рядом лежало правильное «דֶּרֶךְ»,
и никто не замечал расхождения три месяца.

Чем эта проверка НЕ является
----------------------------
Она не проверяет, верна ли огласовка. Правильно ли «כּוֹתֵב» против
«כּוֹתב» машина знать не может — для этого нужен носитель, и такие
вопросы копятся в ВОПРОСЫ_ВАДИМУ.md. Здесь только те правила, которые
формальны и не требуют знания языка: по ним расхождение — всегда ошибка,
а не стилистический выбор.

Запуск:  python3 tools/check_hebrew.py
"""

import os
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import phrases                                   # noqa: E402
import syntax                                    # noqa: E402
from conjugations import CONJUGATIONS            # noqa: E402
from words import VOCAB, VERBS                   # noqa: E402

SHVA = "ְ"

# Конечный каф в огласованном тексте несёт шва-нах, остальные софиты —
# нет. Проверено по словарю проекта: у кафа шва во всех случаях, у
# прочих — ни в одном из 76.
SOFIT_WITH_SHVA = "ך"
SOFIT_WITHOUT = "םןףץ"


def hebrew_strings():
    """Все ивритские строки проекта с указанием, откуда они."""
    for cat, pairs in VOCAB.items():
        for ru, he in pairs:
            yield f"словарь/{cat}", ru, he
    for cat, pairs in VERBS.items():
        for ru, he in pairs:
            yield f"глаголы/{cat}", ru, he
    for root, data in CONJUGATIONS.items():
        yield f"инфинитив/{root}", data["ru"], data["inf"]
        for tense in ("past", "present", "future"):
            for slot, form in data[tense].items():
                if form:
                    yield f"{tense}/{root}", slot, form
    for sit, item in phrases.all_phrases():
        for field in ("he", "he_f", "to_f", "he_en"):
            if item.get(field):
                yield f"фразы/{sit}", item["ru"], item[field]
    # «Собери фразу». Проверяем и неверные варианты: они тоже попадают
    # человеку на экран, и огласовка в них должна быть настоящей —
    # неверным вариант делает правило, а не испорченная запись слова.
    for ru, _en, right, wrongs, frame in syntax.SENTENCES:
        for word in right.split():
            yield f"фраза/{frame}", ru, word
        for wrong, rule in wrongs:
            for word in wrong.split():
                yield f"фраза/{frame}/{rule}", ru, word


def check_final_kaf():
    """Конечный каф обязан нести шва."""
    bad = []
    for where, label, he in hebrew_strings():
        for word in he.split():
            w = word.rstrip(".,?!»")
            if w.endswith(SOFIT_WITH_SHVA):
                bad.append(f"{where}: «{label}» -> {he}  (нужно {w}{SHVA})")
    return "конечный каф без шва", bad


def check_other_sofits():
    """У прочих конечных букв шва, наоборот, быть не должно."""
    bad = []
    for where, label, he in hebrew_strings():
        for word in he.split():
            w = word.rstrip(".,?!»")
            if len(w) >= 2 and w[-1] == SHVA and w[-2] in SOFIT_WITHOUT:
                bad.append(f"{where}: «{label}» -> {he}  (лишний шва)")
    return "лишний шва у конечной буквы", bad


def check_sofit_position():
    """Конечная буква не может стоять в середине слова.

    Опечатка при ручном наборе: рука тянется к конечной форме, а слово
    ещё не кончилось. Читается такое как другое слово.
    """
    bad = []
    for where, label, he in hebrew_strings():
        for word in he.split():
            # Берём только ивритские буквы. Первый заход этого не делал,
            # и запятая после «חֶשְׁבּוֹן,» оказывалась последним знаком —
            # а «нун» из-за этого «серединой слова». Шесть ложных тревог
            # на ровном месте: проверка обязана смотреть на буквы, а не
            # на всё подряд, что не является огласовкой.
            letters = [c for c in word
                       if "א" <= c <= "ת"
                       and unicodedata.combining(c) == 0]
            for ch in letters[:-1]:
                if ch in SOFIT_WITH_SHVA + SOFIT_WITHOUT:
                    bad.append(f"{where}: «{label}» -> {he}  ({ch} в середине)")
                    break
    return "конечная буква в середине слова", bad


def check_double_niqqud():
    """Две гласные подряд на одной букве — всегда опечатка."""
    VOWELS = "ְֱֲֳִֵֶַָֹֻ"
    bad = []
    for where, label, he in hebrew_strings():
        for i in range(len(he) - 1):
            if he[i] in VOWELS and he[i + 1] in VOWELS:
                bad.append(f"{where}: «{label}» -> {he}")
                break
    return "две огласовки подряд", bad


CHECKS = [check_final_kaf, check_other_sofits, check_sofit_position,
          check_double_niqqud]


def main():
    total = sum(1 for _ in hebrew_strings())
    failed = 0
    for check in CHECKS:
        title, bad = check()
        if bad:
            failed += 1
            print(f"✗ {title}: {len(bad)}")
            for line in bad[:10]:
                print(f"    {line}")
            if len(bad) > 10:
                print(f"    … и ещё {len(bad) - 10}")
        else:
            print(f"✓ {title} — не найдено")
    print(f"\nивритских строк проверено: {total}")
    print("Формальные правила сошлись. Верность самих огласовок "
          "машина не проверяет — это к носителю.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
