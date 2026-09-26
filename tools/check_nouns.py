#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка рода и множественного числа.

Зачем именно такая
------------------
Формы в nouns.py написаны по памяти, и это самый большой массив
рукописного иврита в проекте. Ошибка здесь невидима: приложение покажет
несуществующее слово, человек его выучит, а ни одна строчка в журнал не
упадёт.

Опереться на генератор нельзя — правило даёт 30 % попаданий. Значит
проверять надо не «правильно ли», а «непротиворечиво ли»: данные
записаны дважды (род и окончание), и они обязаны сходиться. Там, где не
сходятся, должно стоять явное объяснение — иначе это описка.

Такая проверка не докажет, что שֻׁלְחָנוֹת верно. Но она поймает
опечатку в окончании, забытое слово, лишнюю пометку и рассинхрон со
словарём — то есть всё, что можно поймать без носителя.

Чего она не делает
------------------
Не подтверждает правильность самих форм. Это к Вадиму, и до его
проверки весь раздел считается черновым.

Запуск:  python3 tools/check_nouns.py
"""

import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import nouns                                  # noqa: E402
from words import VOCAB                       # noqa: E402

PLURAL_CATS = ("family", "food", "home", "city", "transport", "time",
               "weather", "health", "shopping", "work_study", "clothes",
               "emotions")

# Окончания сравниваются С ОГЛАСОВКАМИ, и это существенно: без них
# парное «־ַיִם» и множественное «־ִים» превращаются в одинаковое «ים»,
# и проверка объявляет парными все мужские формы подряд. Первый прогон
# так и сделал — 56 ложных тревог на ровном месте.
MASC_END = "ִים"
FEM_END = "וֹת"
DUAL_END = "ַיִם"

# Существительные словаря, которые существительными не являются:
# прилагательные и наречия попали в те же тематические группы.
# Списком, а не правилом: часть речи из написания не выводится.
NOT_NOUN = {
    "אֶתְמוֹל", "הַיּוֹם", "מָחָר", "עַכְשָׁיו", "לִפְעָמִים",
    "תָּמִיד", "בָּרִיא", "חוֹלֶה", "זוֹל", "יָקָר",
    "כּוֹעֵס", "מְאֻשָּׁר", "מְרֻצֶּה", "עָיֵף", "צָמֵא",
    "רָעֵב", "רָגוּעַ",
}


def bare(s):
    return "".join(c for c in s if not unicodedata.combining(c))


def dictionary_nouns():
    """Существительные словаря, кроме составных и прилагательных."""
    out = {}
    for cat in PLURAL_CATS:
        for ru, he in VOCAB[cat]:
            if " " in he or he in NOT_NOUN:
                continue          # смихут и не-существительные — мимо
            out[he] = ru
    return out


# Знаки, изменяющие СОГЛАСНУЮ, а не гласную: дагеш и точки шин/син.
# Их надо снять перед сверкой окончания, потому что они втискиваются
# между огласовкой и следующей буквой: в «נָשִׁים» порядок — хирик,
# точка шина, йод, мем, и поиск «ִים» не находит ничего. Огласовки при
# этом остаются: именно они отличают парное «־ַיִם» от «־ִים».
CONSONANT_DOTS = "\u05BC\u05C1\u05C2"


def ending_of(plural):
    """«m», «f», «dual» или None. Смотрит на огласовки, не на голые буквы."""
    clean = "".join(c for c in plural if c not in CONSONANT_DOTS)
    if clean.endswith(DUAL_END):
        return "dual"
    if clean.endswith(FEM_END):
        return "f"
    if clean.endswith(MASC_END):
        return "m"
    return None


def check_coverage():
    """Каждое существительное словаря должно быть размечено.

    Добавят слово — оно не должно молча остаться без рода: тогда
    упражнение просто не покажет его, и пропажу никто не заметит.
    """
    words = dictionary_nouns()
    missing = [f"{he} ({ru})" for he, ru in words.items() if he not in nouns.NOUNS]
    return "существительное словаря без разметки", sorted(missing)


def check_extra():
    """И наоборот: разметка не должна описывать то, чего в словаре нет."""
    words = dictionary_nouns()
    extra = [he for he in nouns.NOUNS if he not in words]
    return "размечено слово, которого нет в словаре", sorted(extra)


def check_ending_matches_gender():
    """Окончание множественного обязано сходиться с родом.

    Это главная проверка. Данные записаны дважды — род и форма — и
    расхождение между ними означает либо известное исключение (тогда оно
    названо в EXCEPTIONS), либо мою описку. Третьего не дано.
    """
    bad = []
    for he, (gender, plural) in nouns.NOUNS.items():
        if plural == nouns.COUNT_NONE:
            continue
        kind = ending_of(plural)
        if kind is None:
            bad.append(f"{he} -> {plural}: окончание не опознано")
            continue
        expected = "m" if gender == nouns.M else "f"
        if kind != expected and he not in nouns.EXCEPTIONS:
            bad.append(f"{he} -> {plural}: род {gender}, а окончание "
                       f"{'парное' if kind == 'dual' else kind} "
                       f"— или ошибка, или впишите в EXCEPTIONS")
    return "окончание не сходится с родом", bad


def check_stale_exceptions():
    """Пометки об исключениях должны относиться к делу.

    Пометка, оставшаяся от исправленной формы, хуже её отсутствия: она
    глушит проверку на слове, которое давно в порядке.
    """
    bad = []
    for he in nouns.EXCEPTIONS:
        item = nouns.NOUNS.get(he)
        if not item:
            bad.append(f"{he}: пометка есть, слова нет")
            continue
        gender, plural = item
        if plural == nouns.COUNT_NONE:
            bad.append(f"{he}: пометка есть, а множественного нет")
            continue
        kind = ending_of(plural)
        expected = "m" if gender == nouns.M else "f"
        if kind == expected:
            bad.append(f"{he}: пометка лишняя, окончание и так сходится")
    return "лишняя пометка об исключении", bad


def check_skeleton():
    """Согласный скелет множественного должен содержать скелет единственного.

    Ловит описку в самой основе: «סְפָרִים» от «סֵפֶר» проходит,
    «סְבָרִים» — нет. Слова, где основа меняется целиком, перечислены
    в SUPPLETIVE и сюда не попадают.
    """
    bad = []
    for he, (_g, plural) in nouns.NOUNS.items():
        if plural == nouns.COUNT_NONE or he in nouns.SUPPLETIVE:
            continue
        sg = bare(he)
        pl = bare(plural)
        # окончание отбрасываем, дальше сверяем согласные по порядку
        for end in ("יים", "ים", "ות"):
            if pl.endswith(end):
                pl = pl[:-len(end)]
                break
        # последняя буква единственного могла быть конечной формой
        FINAL = {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}
        sg = "".join(FINAL.get(c, c) for c in sg)
        # у женского ־ה перед окончанием пропадает
        sg_core = sg[:-1] if sg.endswith(("ה", "א")) else sg
        if not (pl.startswith(sg_core[:2]) and len(pl) >= len(sg_core) - 1):
            bad.append(f"{he} -> {plural}: основа не похожа на исходную")
    return "основа множественного не похожа на единственное", bad


def check_suppletive_listed():
    """Список «другая основа» не должен разойтись с данными."""
    bad = []
    for he, plural in nouns.SUPPLETIVE.items():
        item = nouns.NOUNS.get(he)
        if not item:
            bad.append(f"{he}: в списке есть, в данных нет")
        elif item[1] != plural:
            bad.append(f"{he}: в списке «{plural}», в данных «{item[1]}»")
    return "список особых основ разошёлся с данными", bad


def check_page_examples():
    """Примеры со страницы справочника должны существовать.

    Страница показывает отобранные слова. Если такое слово выкинут из
    словаря или из разметки, строка на странице просто окажется пустой —
    ни ошибки, ни следа в журнале. Так и вышло при первой сборке: два
    слова из шестнадцати в словаре отсутствовали.
    """
    import grammar
    bad = []
    for group, items in grammar._PLURAL_SHOW.items():
        for he in items:
            if he not in nouns.NOUNS:
                bad.append(f"{he} ({group}): на странице есть, в разметке нет")
            elif nouns.NOUNS[he][1] == nouns.COUNT_NONE:
                bad.append(f"{he} ({group}): на странице есть, множественного нет")
            elif he not in grammar._gloss():
                bad.append(f"{he} ({group}): нет в словаре, перевод будет пустой")
    return "пример со страницы «один и много» не находится", bad


CHECKS = [check_coverage, check_extra, check_ending_matches_gender,
          check_stale_exceptions, check_skeleton, check_suppletive_listed,
          check_page_examples]


def main():
    failed = 0
    for check in CHECKS:
        title, bad = check()
        if bad:
            failed += 1
            print(f"✗ {title}: {len(bad)}")
            for line in bad[:14]:
                print(f"    {line}")
            if len(bad) > 14:
                print(f"    … и ещё {len(bad) - 14}")
        else:
            print(f"✓ {title} — не найдено")

    total = len(nouns.NOUNS)
    counted = len(nouns.countable())
    print(f"\nразмечено существительных: {total}, "
          f"из них с множественным: {counted}")
    print("Непротиворечивость проверена. ПРАВИЛЬНОСТЬ форм — к носителю.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
