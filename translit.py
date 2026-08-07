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


def translit(word):
    """Произношение слова кириллицей."""
    units = _split(word)
    res = []

    for i, (letter, marks) in enumerate(units):
        if letter == " ":
            res.append(" ")
            continue
        if letter not in CONSONANTS:
            continue

        vowel = next((VOWELS[m] for m in marks if m in VOWELS), None)
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
