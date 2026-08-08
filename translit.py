# -*- coding: utf-8 -*-
"""
Произношение кириллицей — выводится из огласовок автоматически.

Руками транслитерацию для ~1900 карточек не набрать, но она и не нужна:
у нас всюду проставлены огласовки, а они однозначно задают чтение.
Поэтому произношение строится по тем же правилам, что и спряжения.

Точность: передаём звучание так, как его слышит русскоязычный. Ударение
не проставляем — в огласовках его нет, а угадывать (в иврите оно чаще
на последнем слоге, но у целого класса слов — на предпоследнем) значит
регулярно учить неправильно.
"""

import unicodedata

DAGESH = "ּ"
SHIN_DOT = "ׁ"
SIN_DOT = "ׂ"

# Огласовки -> звук. Патах и камац в современном иврите звучат одинаково.
VOWELS = {
    "ַ": "а",   # патах
    "ָ": "а",   # камац
    "ֶ": "е",   # сеголь
    "ֵ": "е",   # цере
    "ִ": "и",   # хирик
    "ֹ": "о",   # холам
    "ֻ": "у",   # кубуц
    "ֲ": "а",   # хатаф-патах
    "ֱ": "е",   # хатаф-сеголь
    "ֳ": "о",   # хатаф-камац
}
SHVA = "ְ"
KAMATS = "ָ"
HATAF_KAMATS = "ֳ"

# «Камац катан» — камац, который читается как «о», а не «а»
# (כָּל = коль, צָהֳרַיִם = цохорайим). Формально это камац в закрытом
# безударном слоге, но надёжно вывести это из одних огласовок нельзя:
# нужна информация об ударении, которой у нас нет. На весь наш банк
# таких слов ровно два, поэтому — одно правило и один список.
#
# Правило: камац перед буквой с хатаф-камацем — всегда катан.
# Список: слова, которые под правило не подпадают.
KAMATS_KATAN_WORDS = {"כָּל"}

# Согласные. Для ב, כ, פ звук зависит от дагеша, для ש — от точки сбоку.
CONSONANTS = {
    "א": "", "ב": "в", "ג": "г", "ד": "д", "ה": "х", "ו": "в", "ז": "з",
    "ח": "х", "ט": "т", "י": "й", "כ": "х", "ך": "х", "ל": "л", "מ": "м",
    "ם": "м", "נ": "н", "ן": "н", "ס": "с", "ע": "", "פ": "ф", "ף": "ф",
    "צ": "ц", "ץ": "ц", "ק": "к", "ר": "р", "ש": "ш", "ת": "т",
}
# С дагешем эти три читаются иначе
HARD = {"ב": "б", "כ": "к", "פ": "п"}


def _split(word):
    """Разбивает слово на пары (буква, значки при ней)."""
    out = []
    for ch in unicodedata.normalize("NFC", word or ""):
        if unicodedata.combining(ch):
            if out:
                out[-1][1].append(ch)
        elif ch == " ":
            out.append([" ", []])
        else:
            out.append([ch, []])
    return out


def to_ktiv_male(word):
    """Огласованная запись -> обычное израильское письмо (כתיב מלא).

    Нужно для синтеза речи: модели TTS обучены на живом тексте без
    огласовок, и диакритика их сбивает. Отличается от нормализации в
    matching.py тем, что здесь важно получить ПРАВИЛЬНЫЙ иврит:
    конечные формы букв сохраняются (שלום, а не שלומ), иначе синтезатор
    читает бессмыслицу.

    Правила, которые реально нужны нашему банку:
      кубуц ֻ           -> ו      (סֻכָּר -> סוכר)
      холам ֹ           -> ו      (חֹם -> חום), но не перед א: רֹאשׁ -> ראש
      окончание ַיִם     -> ַיִים   (מִכְנָסַיִם -> מכנסיים)
    """
    units = _split(word)
    out = []
    for i, (letter, marks) in enumerate(units):
        out.append(letter)
        if letter == " ":
            continue
        nxt = units[i + 1][0] if i + 1 < len(units) else None

        if "ֻ" in marks:                      # кубуц
            out.append("ו")
        elif "ֹ" in marks and letter != "ו":   # холам
            # перед א вав не пишут: רֹאשׁ -> ראש
            if nxt != "א":
                out.append("ו")
        elif "ִ" in marks and letter == "י" and i >= 1 and "ַ" in units[i - 1][1]:
            # Окончание -айим удваивает йод, но только если перед ним есть
            # полноценный слог: מכנסיים, שמיים — и при этом מים, בית, עין
            # с одним йодом (там до йода всего одна буква).
            letters_before = sum(1 for l, _ in units[:i] if l != " ")
            if letters_before >= 2:
                out.append("י")

    return "".join(out)


def translit(word):
    """Произношение слова кириллицей."""
    # Слова разбираем по отдельности: камац катан определяется в пределах
    # слова, а не всей фразы.
    if " " in (word or ""):
        return " ".join(translit(w) for w in word.split())

    units = _split(word)
    whole_word_katan = unicodedata.normalize("NFC", word or "") in KAMATS_KATAN_WORDS
    res = []

    for i, (letter, marks) in enumerate(units):
        if letter == " ":
            res.append(" ")
            continue
        if letter not in CONSONANTS:
            continue

        vowel = next((VOWELS[m] for m in marks if m in VOWELS), None)

        # Камац катан читается как «о»: перед хатаф-камацем (צָהֳרַיִם)
        # или в слове из списка (כָּל).
        if KAMATS in marks:
            next_marks = units[i + 1][1] if i + 1 < len(units) else []
            if whole_word_katan or HATAF_KAMATS in next_marks:
                vowel = "о"

        has_dagesh = DAGESH in marks
        prev_letter, prev_marks = units[i - 1] if i > 0 else (None, [])
        nxt = units[i + 1] if i + 1 < len(units) else None

        # ו и י часто не согласные, а часть гласной
        if letter == "ו":
            if has_dagesh and vowel is None:
                res.append("у")            # шурук וּ
                continue
            if vowel == "о":
                res.append("о")            # холам мале וֹ
                continue
        if letter == "י" and vowel is None and "ִ" in prev_marks:
            continue                        # хирик мале ִי — «и» уже выдана

        # согласный
        if letter in HARD and has_dagesh:
            snd = HARD[letter]
        elif letter == "ש":
            snd = "с" if SIN_DOT in marks else "ш"
        else:
            snd = CONSONANTS[letter]

        # немые в конце слова
        is_last = nxt is None or nxt[0] == " "
        if is_last and letter in ("ה", "א") and vowel is None:
            continue

        # «Патах гнува»: под конечными ע и ח патах читается ПЕРЕД буквой —
        # תַּפּוּחַ это «тапуах», а не «тапуха».
        if is_last and letter in ("ע", "ח") and "ַ" in marks:
            res.append("а")
            res.append(snd)
            continue

        res.append(snd)

        if vowel:
            res.append(vowel)
        elif SHVA in marks:
            # Шва в начале слова читается как «е», внутри чаще беззвучна
            at_start = i == 0 or units[i - 1][0] == " "
            if at_start:
                res.append("е")

    return "".join(res).strip()
