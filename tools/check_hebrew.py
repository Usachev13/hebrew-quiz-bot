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

import hebrew_rules                              # noqa: E402

# Сами правила живут в hebrew_rules.py, а не здесь. Причина простая: те
# же правила теперь применяются на лету к ивриту, который порождает
# языковая модель в разговоре, и второй копии быть не должно — копии
# расходятся, а расхождение здесь означает, что одна из двух проверок
# молча пропускает ошибку.
SHVA = hebrew_rules.SHVA
SOFIT_WITH_SHVA = hebrew_rules.SOFIT_WITH_SHVA
SOFIT_WITHOUT = hebrew_rules.SOFIT_WITHOUT


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


def by_rule(name):
    """Одна проверка на всех строках — правило берём из hebrew_rules."""
    def run():
        bad = []
        for where, label, he in hebrew_strings():
            for problem in hebrew_rules.problems(he):
                if problem.startswith(name):
                    bad.append(f"{where}: «{label}» -> {he}  ({problem})")
                    break
        return name, bad
    run.__name__ = name
    return run


check_final_kaf = by_rule("конечный каф без шва")
check_other_sofits = by_rule("лишний шва у конечной буквы")
check_sofit_position = by_rule("конечная буква в середине слова")
check_double_niqqud = by_rule("две огласовки подряд")


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
