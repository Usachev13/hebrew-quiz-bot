# -*- coding: utf-8 -*-
"""
כָּל: одно слово, три значения, и различает их артикль.

    כָּל יוֹם        каждый день      без артикля, единственное
    כָּל הַיּוֹם      весь день        с артиклем, единственное
    כָּל הַיָּמִים    все дни          с артиклем, множественное

В ульпане это два занятия («Коль конкретное» и «Коль неконкретное»), и
понятно почему: по-русски это три разных слова, а в иврите одно, и
смысл меняет крошечный הַ. Человек, не знающий правила, говорит «כָּל
הַיּוֹם», имея в виду «каждый день», — и его понимают как «весь день».

Читается «коль», а не «каль»: это камац катан, и в нашем чтении он уже
учтён (см. translit.KAMATS_KATAN_WORDS).

Откуда формы
------------
Существительные и их множественное — из выверенного словаря
(nouns.py). Артикль — нашим правилом syntax.definite, только к словам,
где он обычный (הַ с дагешем). Готовые сочетания сверены с огласовщиком
Dicta: с «כָּל» впереди у него есть контекст, и омографы вроде
«שָׁנָה / שֵׁנָה» он различает.
"""

import nouns
import syntax

KOL = "כָּל"

# (иврит ед., русское «каждый …», «весь …», «все …»). Русские формы
# вписаны руками: без них выходит «каждый книга» и «весь ночь». Там,
# где сочетание по-русски бессмысленно («весь ребёнок»), стоит None, и
# такого вопроса не будет.
NOUNS = [
    ("יוֹם", "каждый день", "весь день", "все дни"),
    ("שָׁבוּעַ", "каждая неделя", "вся неделя", "все недели"),
    ("לַיְלָה", "каждая ночь", "вся ночь", "все ночи"),
    ("שָׁנָה", "каждый год", "весь год", "все годы"),
    ("בַּיִת", "каждый дом", "весь дом", "все дома"),
    ("סֵפֶר", "каждая книга", "вся книга", "все книги"),
    ("דִּירָה", "каждая квартира", "вся квартира", "все квартиры"),
    ("יֶלֶד", "каждый ребёнок", None, "все дети"),
]

NOUNS_EN = {
    "יוֹם": ("every day", "the whole day", "all the days"),
    "שָׁבוּעַ": ("every week", "the whole week", "all the weeks"),
    "לַיְלָה": ("every night", "the whole night", "all the nights"),
    "שָׁנָה": ("every year", "the whole year", "all the years"),
    "בַּיִת": ("every house", "the whole house", "all the houses"),
    "סֵפֶר": ("every book", "the whole book", "all the books"),
    "דִּירָה": ("every flat", "the whole flat", "all the flats"),
    "יֶלֶד": ("every child", None, "all the children"),
}

RULES = {
    "every": "כָּל без артикля перед единственным числом — «каждый»: "
             "כָּל יוֹם — каждый день.",
    "whole": "כָּל с артиклем перед единственным числом — «весь, целый»: "
             "כָּל הַיּוֹם — весь день.",
    "all": "כָּל с артиклем перед множественным числом — «все»: "
           "כָּל הַיָּמִים — все дни.",
}

RULES_EN = {
    "every": "כָּל with no article before a singular noun means «every»: "
             "כָּל יוֹם — every day.",
    "whole": "כָּל with the article before a singular noun means «the "
             "whole»: כָּל הַיּוֹם — the whole day.",
    "all": "כָּל with the article before a plural noun means «all»: "
           "כָּל הַיָּמִים — all the days.",
}


def forms(noun):
    """Три сочетания для слова: {значение: иврит}."""
    plural = nouns.plural_of(noun)
    out = {"every": f"{KOL} {noun}"}
    if syntax.simple_article(noun):
        out["whole"] = f"{KOL} {syntax.definite(noun)}"
    if plural and syntax.simple_article(plural):
        out["all"] = f"{KOL} {syntax.definite(plural)}"
    return out


def build():
    """(ru, en, верно, [(неверно, значение_неверного)], значение_верного)."""
    out = []
    for noun, every, whole, all_ in NOUNS:
        variants = forms(noun)
        ru_by = {"every": every, "whole": whole, "all": all_}
        en_by = dict(zip(("every", "whole", "all"), NOUNS_EN.get(noun, ())))
        for meaning, right in variants.items():
            ru = ru_by.get(meaning)
            if not ru:
                continue
            # Неверные варианты — те же сочетания с другим значением.
            # «Весь ребёнок» по-русски бессмыслица, но как НЕВЕРНЫЙ
            # вариант «כָּל הַיֶּלֶד» годится: это настоящая ошибка — артикль
            # не к месту.
            wrongs = [(text, m) for m, text in variants.items() if m != meaning]
            if not wrongs:
                continue
            out.append((ru, en_by.get(meaning) or ru, right, wrongs, meaning))
    return out


SENTENCES = build()


def explain(right, given, lang="ru"):
    """Разбор: что значит выбранное и что значит верное."""
    table = RULES_EN if lang == "en" else RULES
    lines = []
    for _ru, _en, correct, wrongs, meaning in SENTENCES:
        if correct != right:
            continue
        for wrong, m in wrongs:
            if wrong == given:
                lines.append(table[m])
        lines.append(table[meaning])
        break
    return lines
