# -*- coding: utf-8 -*-
"""
Страницы грамматики — то, что не помещается в подсказку.

Почему страницы, а не раздел «Грамматика»
-----------------------------------------
Справочник, в который заходят по своей воле, почти не работает: человек
открывает его, только если сам догадался, что ему нужна теория, а
догадывается он редко. Семнадцать описаний похожих букв пролежали в
этом проекте без дела полгода ровно поэтому — они были, но входа к ним
не было.

Поэтому вход у каждой страницы один и естественный: из разбора карточки.
В подсказке к любой форме глагола стоит «Биньян пиэль» — это и есть
ссылка. Человек читает объяснение тогда, когда у него уже возник вопрос,
а не когда он решил «пойти поучить грамматику».

Следствие: страницы пишутся только под те подсказки, что уже есть. Если
у подсказки нет входа на страницу — страницы и не будет, и мёртвого
груза не появится.

Откуда взят материал
--------------------
Написано здесь, своими словами. У преподавателя проекта есть свои
разборы, но на них стоит «© 2023 Vadim Galimov», и в платный продукт они
попасть не могут без отдельной договорённости. Это и не требуется:
устройство биньянов — факт языка, а не чья-то собственность; защищён
текст, а не то, что пиэль удваивает вторую корневую.

Примеры берутся из наших же спряжений (CONJUGATIONS), а не набираются
руками. Так они не разойдутся с тем, что человек тренирует, и не
устареют при правке генератора.
"""

import collections

from conjugations import CONJUGATIONS

# Какая страница открывается для какой пометки биньяна. Вариантов
# пааля три, страница у них одна: различия у них внутри модели, и
# разносить их по трём страницам значило бы трижды пересказать общее.
PAGE_OF_BINYAN = {
    "пааль": "paal",
    "пааль (ל״ה)": "paal",
    "пааль (гортанная)": "paal",
    "пиэль": "piel",
    "ифиль": "hifil",
    "итпаэль": "hitpael",
    "исключения / полые": "irregular",
}


def _example(root):
    """Живой пример из наших спряжений: инфинитив и три времени."""
    d = CONJUGATIONS.get(root)
    if not d:
        return None
    return {
        "inf": d["inf"], "ru": d["ru"],
        "past": d["past"].get("הוא"),
        "present": d["present"].get("m_sg"),
        "future": d["future"].get("הוא"),
    }


def _count(page):
    return sum(1 for d in CONJUGATIONS.values()
               if PAGE_OF_BINYAN.get(d["binyan"]) == page)


PAGES = {

"paal": {
    "ru": {
        "title": "Пааль — простое действие",
        "lead": "Самый обычный биньян: в нём глаголы, которые просто "
                "называют действие. Писать, читать, есть, работать. "
                "Если не знаете, к какому биньяну отнести глагол, — "
                "скорее всего к этому.",
        "blocks": [
            ("Как узнать",
             "В инфинитиве после ל идёт первая корневая без приставок: "
             "לִכְתּוֹב, לִלְמוֹד. В настоящем времени между первой и "
             "второй корневой стоит «о»: כּוֹתֵב, לוֹמֵד — это самый "
             "заметный признак."),
            ("Три разновидности",
             "Ровный пааль — корень из трёх обычных согласных.\n\n"
             "Пааль с третьей «хей» (ל״ה): корень кончается на ה, и она "
             "исчезает почти во всех формах — לִקְנוֹת «покупать», "
             "קוֹנֶה «покупает». Таких глаголов много, и путаницу они "
             "вызывают чаще прочих.\n\n"
             "Пааль с гортанной: если в корне есть א, ה, ח, ע, огласовки "
             "вокруг неё меняются — гортанные не принимают шва и требуют "
             "хатаф. Само действие от этого не меняется, меняется только "
             "огранка."),
            ("Зачем это знать",
             "Пааль — половина всех глаголов, которые встретятся на "
             "первом году. Узнав его форму настоящего времени с «о» "
             "посередине, вы будете понимать незнакомые глаголы, даже не "
             "зная их перевода: по виду будет ясно, что это действие и "
             "кто его совершает."),
        ],
        "sample": "כתב",
    },
    "en": {
        "title": "Pa'al — the plain action",
        "lead": "The ordinary binyan: verbs that simply name an action. "
                "To write, to read, to eat, to work. If you don't know "
                "which binyan a verb belongs to, it's probably this one.",
        "blocks": [
            ("How to spot it",
             "In the infinitive the first root letter follows ל with no "
             "prefix: לִכְתּוֹב, לִלְמוֹד. In the present tense there's an "
             "«o» between the first and second root letters: כּוֹתֵב, "
             "לוֹמֵד — that's the clearest sign."),
            ("Three varieties",
             "Plain pa'al — three ordinary consonants in the root.\n\n"
             "Pa'al with final hey (ל״ה): the root ends in ה, which "
             "disappears in almost every form — לִקְנוֹת «to buy», "
             "קוֹנֶה «buys». There are many of these and they cause more "
             "confusion than the rest.\n\n"
             "Pa'al with a guttural: if the root contains א, ה, ח or ע, "
             "the vowels around it change — gutturals don't take a sheva "
             "and require a hataf instead. The meaning doesn't change, "
             "only the shape."),
            ("Why it matters",
             "Pa'al is half of all the verbs you'll meet in the first "
             "year. Once you recognise its present tense with the «o» in "
             "the middle, you'll understand unfamiliar verbs without "
             "knowing their meaning: the shape alone tells you it's an "
             "action and who is doing it."),
        ],
        "sample": "כתב",
    },
},

"piel": {
    "ru": {
        "title": "Пиэль — усиленное действие",
        "lead": "Второй по частоте биньян. Часто означает действие более "
                "напряжённое или направленное на кого-то: не «ломать», а "
                "«разбивать вдребезги»; не «говорить», а «разговаривать».",
        "blocks": [
            ("Как узнать",
             "Вторая корневая удваивается — в огласованном тексте это "
             "видно по точке внутри буквы (дагеш): לְדַבֵּר, מְדַבֵּר. "
             "В настоящем времени слово начинается с מְ, и это самый "
             "быстрый признак: увидели מְ в начале — почти наверняка "
             "пиэль."),
            ("Что заметить",
             "Инфинитив начинается с לְ, а не с לִ, как у пааля. "
             "Разница в одной огласовке, но она устойчива и помогает "
             "различать модели с первого взгляда."),
            ("Смысл",
             "Связь «пиэль = сильнее» работает не всегда: לְקַבֵּל "
             "«получать» ничем не напряжённее обычного действия. "
             "Полагаться стоит на форму, а не на смысл — форма надёжна, "
             "значение подсказывает лишь иногда."),
        ],
        "sample": "דבר",
    },
    "en": {
        "title": "Pi'el — the intensified action",
        "lead": "The second most common binyan. Often marks an action "
                "that is more intense or directed at someone: not «to "
                "break» but «to smash»; not «to say» but «to speak».",
        "blocks": [
            ("How to spot it",
             "The second root letter is doubled — in pointed text you see "
             "it as a dot inside the letter (dagesh): לְדַבֵּר, מְדַבֵּר. "
             "In the present tense the word starts with מְ, and that's the "
             "quickest sign: a מְ at the front almost always means pi'el."),
            ("Worth noticing",
             "The infinitive starts with לְ, not לִ as in pa'al. It's one "
             "vowel of difference, but a reliable one — it tells the two "
             "models apart at a glance."),
            ("About the meaning",
             "The «pi'el means stronger» rule doesn't always hold: "
             "לְקַבֵּל «to receive» is no more intense than an ordinary "
             "action. Trust the shape rather than the meaning — the shape "
             "is dependable, the meaning only hints."),
        ],
        "sample": "דבר",
    },
},

"hifil": {
    "ru": {
        "title": "Ифиль — заставить сделать",
        "lead": "Биньян причины. Если пааль — «войти», то ифиль — "
                "«ввести»; если «понять», то «объяснить», то есть "
                "сделать так, чтобы другой понял.",
        "blocks": [
            ("Как узнать",
             "Приставка ה в инфинитиве и в прошедшем: לְהַסְבִּיר, "
             "הִסְבִּיר. В настоящем времени вместо неё מַ: מַסְבִּיר. "
             "Между второй и третьей корневой почти всегда стоит «и» — "
             "מַרְגִּישׁ, מַזְמִין."),
            ("Зачем это знать",
             "Ифиль позволяет понять незнакомое слово через знакомое. "
             "Увидев מַתְחִיל и зная корень תחל, можно догадаться: "
             "«начинает» — то есть заставляет что-то начаться."),
            ("Осторожно",
             "Не всякий глагол с ה — ифиль: у итпаэля тоже есть ה, но "
             "перед ней стоит הִת. Смотрите на две буквы, а не на одну."),
        ],
        "sample": "סבר",
    },
    "en": {
        "title": "Hif'il — to make someone do",
        "lead": "The causative binyan. If pa'al is «to enter», hif'il is "
                "«to bring in»; if it's «to understand», hif'il is «to "
                "explain» — to make someone else understand.",
        "blocks": [
            ("How to spot it",
             "A ה prefix in the infinitive and the past: לְהַסְבִּיר, "
             "הִסְבִּיר. In the present it becomes מַ instead: מַסְבִּיר. "
             "There's almost always an «i» between the second and third "
             "root letters — מַרְגִּישׁ, מַזְמִין."),
            ("Why it matters",
             "Hif'il lets you work out an unfamiliar word from a familiar "
             "one. Seeing מַתְחִיל and knowing the root תחל, you can guess: "
             "«starts» — that is, makes something start."),
            ("A caution",
             "Not every verb with ה is hif'il: hitpa'el has one too, but "
             "preceded by הִת. Look at two letters, not one."),
        ],
        "sample": "סבר",
    },
},

"hitpael": {
    "ru": {
        "title": "Итпаэль — действие на себя",
        "lead": "Возвратный биньян: действие направлено на самого "
                "говорящего или происходит между людьми. Мыться, "
                "одеваться, переписываться, знакомиться.",
        "blocks": [
            ("Как узнать",
             "Приставка הִת во всех формах: לְהִתְרַחֵץ, הִתְרַחֵץ. "
             "В настоящем — מִת: מִתְרַחֵץ. Это самый узнаваемый биньян "
             "из всех: увидели מִת или הִת — можно не сомневаться."),
            ("Взаимное действие",
             "Итпаэль означает не только «сам с собой», но и «друг с "
             "другом»: לְהִתְכַּתֵּב — переписываться, то есть писать друг "
             "другу. Поэтому многие глаголы этого биньяна естественно "
             "стоят во множественном числе."),
            ("Перестановка букв",
             "Если корень начинается с ס, שׁ, שׂ или צ, буква ת приставки "
             "меняется с ней местами: не הִתְסַדֵּר, а הִסְתַּדֵּר. Это не "
             "исключение и не ошибка — так язык избегает неудобного "
             "сочетания звуков."),
        ],
        "sample": "רחץ",
    },
    "en": {
        "title": "Hitpa'el — action on oneself",
        "lead": "The reflexive binyan: the action is aimed at the speaker "
                "or happens between people. To wash, to get dressed, to "
                "correspond, to get acquainted.",
        "blocks": [
            ("How to spot it",
             "A הִת prefix in every form: לְהִתְרַחֵץ, הִתְרַחֵץ. "
             "In the present it's מִת: מִתְרַחֵץ. This is the most "
             "recognisable binyan of all — a מִת or הִת leaves no doubt."),
            ("Reciprocal action",
             "Hitpa'el means not only «to oneself» but also «to each "
             "other»: לְהִתְכַּתֵּב is to correspond, that is to write to "
             "one another. That's why many verbs in this binyan naturally "
             "appear in the plural."),
            ("Letters swapping places",
             "If the root starts with ס, שׁ, שׂ or צ, the ת of the prefix "
             "swaps places with it: not הִתְסַדֵּר but הִסְתַּדֵּר. This "
             "isn't an exception or a mistake — the language is avoiding "
             "an awkward cluster of sounds."),
        ],
        "sample": "רחץ",
    },
},

"irregular": {
    "ru": {
        "title": "Неправильные и полые глаголы",
        "lead": "Глаголы, формы которых не выводятся из общего правила. "
                "Их немного, но это самые частые слова языка: идти, "
                "прийти, знать, взять, сидеть.",
        "blocks": [
            ("Полые корни",
             "У них средняя корневая — ו или י, и в большинстве форм она "
             "пропадает: לָקוּם «вставать», קָם «встал». Корень как "
             "будто проваливается внутрь, отсюда и название."),
            ("Настоящие исключения",
             "לָלֶכֶת «идти», לָדַעַת «знать», לָקַחַת «брать» ведут себя "
             "каждый по-своему. Здесь правил нет — эти глаголы "
             "запоминают формами."),
            ("Почему стоит потратить время",
             "Их меньше двух десятков, но в речи они встречаются чаще "
             "любых правильных. Выучив их наизусть, вы закроете "
             "значительную часть обиходных разговоров."),
        ],
        "sample": "קום",
    },
    "en": {
        "title": "Irregular and hollow verbs",
        "lead": "Verbs whose forms don't follow the general rule. There "
                "aren't many, but they're the most common words in the "
                "language: to go, to come, to know, to take, to sit.",
        "blocks": [
            ("Hollow roots",
             "Their middle root letter is ו or י, and in most forms it "
             "disappears: לָקוּם «to get up», קָם «got up». The root seems "
             "to collapse inwards — hence the name."),
            ("Genuine exceptions",
             "לָלֶכֶת «to go», לָדַעַת «to know», לָקַחַת «to take» each "
             "behave in their own way. There are no rules here — these "
             "verbs are learned form by form."),
            ("Why they're worth the time",
             "There are fewer than twenty of them, but they come up in "
             "speech more often than any regular verb. Learn them by "
             "heart and you cover a large part of everyday conversation."),
        ],
        "sample": "קום",
    },
},
}


def check_samples():
    """Все примеры на страницах должны существовать в спряжениях.

    Первый заход этого не проверял, и страница итпаэля ссылалась на
    корень לבש, которого в наших данных нет: пример собирался пустым,
    а страница выглядела недоделанной. Ошибка тихая — падения нет,
    просто у одной страницы пропадает половина.
    """
    return sorted({text["sample"]
                   for item in PAGES.values()
                   for text in item.values()
                   if text["sample"] not in CONJUGATIONS})


def page(page_id, lang="ru"):
    """Страница целиком, с живым примером из наших спряжений."""
    item = PAGES.get(page_id)
    if not item:
        return None
    text = item.get(lang) or item["ru"]
    return {
        "id": page_id,
        "title": text["title"],
        "lead": text["lead"],
        "blocks": [{"head": h, "body": b} for h, b in text["blocks"]],
        "example": _example(text["sample"]),
        "count": _count(page_id),
    }


def page_for_binyan(binyan):
    """К какой странице ведёт пометка биньяна."""
    return PAGE_OF_BINYAN.get(binyan)


def verbs_of(page_id):
    """Корни глаголов этой модели — чтобы можно было сразу потренировать."""
    return [root for root, d in CONJUGATIONS.items()
            if PAGE_OF_BINYAN.get(d["binyan"]) == page_id]
