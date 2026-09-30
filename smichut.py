# -*- coding: utf-8 -*-
"""
Смихут: как два существительных складываются в одно понятие.

Что тренируется
---------------
Два правила, и оба в программе ульпана отдельными занятиями
(«סמיכות» и «סמיכות–ה»):

1. Меняется ПЕРВОЕ слово, второе остаётся как было:
       בַּיִת + סֵפֶר  →  בֵּית סֵפֶר      школа
       קֻפָּה + חוֹלִים →  קֻפַּת חוֹלִים   больничная касса
   Русскоязычный по привычке оставляет первое слово целым — «בַּיִת
   סֵפֶר», — и это самая частая ошибка.

2. Артикль ставится на ВТОРОЕ слово:
       בֵּית הַסֵּפֶר      та самая школа
   а не «הַבֵּית סֵפֶר» и не на оба сразу. Логика русскому уху чужая:
   определяется всё сочетание, а знак стоит в его конце.

Откуда данные
-------------
Пары смихута размечены в hebrew_meta.SMICHUT, по словарю проекта.
Формы с артиклем собраны нашим же правилом (syntax.definite), а
затем сверены с огласовщиком Dicta: из восьми сошлись шесть, два
расхождения — его промахи на омографах: «אֲרוּחַת הַבֹּקֶר» он прочитал
как «трапеза скота» (הַבָּקָר), а «חֲדַר הַשֵּׁנָה» — как «комната года»
(הַשָּׁנָה).

Чего здесь нет
--------------
Пар, где первое слово в смихуте не меняется (כַּרְטִיס אַשְׁרַאי, מֶזֶג
אֲוִיר), нет в первом каркасе: там нечего выбирать, верный и неверный
варианты совпали бы.

Слов на гортанную (אֲרוּחַת, חֲדַר, חוֹלִים) нет там, где нужен артикль:
перед гортанной он меняет огласовку, а выводить её правилом мы не
стали — см. syntax.py.
"""

import hebrew_meta
import syntax

RULES = {
    "construct": "В смихуте меняется ПЕРВОЕ слово, второе остаётся как "
                 "было: בַּיִת → בֵּית סֵפֶר. Первое слово как бы "
                 "«прилипает» ко второму и теряет ударение.",
    "article": "Артикль в смихуте ставится на ВТОРОЕ слово: בֵּית "
               "הַסֵּפֶר — «та самая школа». На первое его не ставят "
               "никогда, даже если определённым становится всё сочетание.",
}

RULES_EN = {
    "construct": "In a smichut the FIRST word changes and the second "
                 "stays as it is: בַּיִת → בֵּית סֵפֶר. The first word "
                 "leans on the second and loses its stress.",
    "article": "The article goes on the SECOND word: בֵּית הַסֵּפֶר — "
               "«the school». Never on the first, even though the whole "
               "phrase becomes definite.",
}


def _meaning(phrase):
    """Перевод сочетания из словаря проекта."""
    import quiz
    for card in quiz.VOCAB_FLAT:
        if card.he == phrase:
            return card.ru, card.en or card.ru
    return "", ""


def build():
    """Фразы упражнения: (ru, en, верно, [(неверно, правило)], каркас)."""
    out = []
    for phrase, (base, _bru, _ben) in hebrew_meta.SMICHUT.items():
        first, second = phrase.split(" ", 1)
        ru, en = _meaning(phrase)
        if not ru:
            continue

        # 1. Собрать смихут из двух слов. Только если первое слово
        #    действительно меняется — иначе выбирать не из чего.
        if first != base:
            wrongs = [(f"{base} {second}", "construct")]
            # Второй неверный вариант — артикль на первом слове. Это не
            # выдуманная ошибка «для числа вариантов», а вторая частая:
            # русскоязычный ставит определённость туда, где главное
            # слово. С одним неверным вариантом вопрос был бы угадайкой
            # пятьдесят на пятьдесят.
            #
            # Только там, где первое слово принимает обычный артикль:
            # у гортанных (אֲרוּחַת, חֲדַר) его огласовка другая, и
            # «ошибка ученика» вышла бы ошибкой нашей записи.
            if syntax.simple_article(first):
                wrongs.append((f"{syntax.definite(first)} {second}", "article"))
            out.append((
                f"{base} + {second} — {ru}",
                f"{base} + {second} — {en}",
                phrase,
                wrongs,
                "construct",
            ))

        # 2. Артикль. Оба слова должны принимать обычный артикль (הַ с
        #    дагешем): у гортанных огласовка артикля другая, и неверный
        #    вариант вышел бы не «ошибкой ученика», а ошибкой записи.
        if syntax.simple_article(first) and syntax.simple_article(second):
            out.append((
                f"{phrase} — {ru}: сделать определённым",
                f"{phrase} — {en}: make it definite",
                f"{first} {syntax.definite(second)}",
                [(f"{syntax.definite(first)} {second}", "article"),
                 (f"{syntax.definite(first)} {syntax.definite(second)}",
                  "article")],
                "article",
            ))
    return out


SENTENCES = build()


def rule_of(right, given, lang="ru"):
    """Какое правило нарушил именно этот ответ."""
    table = RULES_EN if lang == "en" else RULES
    for _ru, _en, correct, wrongs, _frame in SENTENCES:
        if correct != right:
            continue
        for wrong, rule in wrongs:
            if wrong == given:
                return table[rule]
    return None
