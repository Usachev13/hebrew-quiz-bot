# -*- coding: utf-8 -*-
"""
Одноразовый генератор спряжений: по корню и классу биньяна строит
9 форм прошедшего времени и 4 формы настоящего с огласовками.

Результат — статический conjugations.py (см. решение ТЗ: данные готовим
один раз, в рантайме ничего не генерируем).

Валидация: генератор обязан байт-в-байт воспроизвести 13 глаголов пааль,
которые ранее были выписаны вручную и проверены.
"""

import unicodedata

# --- огласовки ---
SHVA = "ְ"
HATAF_PATAH = "ֲ"
HIRIQ = "ִ"
TSERE = "ֵ"
SEGOL = "ֶ"
PATAH = "ַ"
QAMATS = "ָ"
DAGESH = "ּ"

GUTTURAL = set("אהחע")          # берут хатаф вместо шва
NO_DAGESH = set("אהחער")        # не принимают дагеш (гортанные + реш)
BEGADKEFAT = set("בגדכפת")      # получают дагеш в начале слова / после шва-нах

SOFIT = {"כ": "ך", "מ": "ם", "נ": "ן", "פ": "ף", "צ": "ץ"}

# гласные, после которых у конечной ע/ח появляется «патах гнува»
NEEDS_FURTIVE = {TSERE, HIRIQ, "ֹ", "ֻ"}


def base(letter):
    """Голая буква без шин/син-точки — для проверок."""
    return letter[0]


def d(letter):
    """Дагеш для бегадкефат (начало слова или позиция после шва-нах)."""
    return letter + DAGESH if base(letter) in BEGADKEFAT else letter


def dg(letter):
    """Удвоение (дагеш хазак) — невозможно под гортанной и реш."""
    return letter if base(letter) in NO_DAGESH else letter + DAGESH


def shva_or_hataf(letter):
    """Под гортанной вместо простого шва пишется хатаф-патах."""
    return HATAF_PATAH if base(letter) in GUTTURAL else SHVA


# Перед א и ר удвоение невозможно и предыдущая гласная удлиняется
# (компенсаторное удлинение): הִתְקָרֵב, а не הִתְקַרֵב.
# Перед ח, ה, ע удвоение тоже невозможно, но гласная НЕ удлиняется
# («виртуальное удвоение»): שִׂחֵק, הִתְנַהֵג.
LENGTHEN = set("אר")
LENGTHENED = {PATAH: QAMATS, HIRIQ: TSERE}


def doubled(vowel, letter):
    """Возвращает (гласная перед второй корневой, вторая корневая)."""
    if base(letter) in LENGTHEN:
        return LENGTHENED.get(vowel, vowel), letter
    return vowel, dg(letter)


def fem_sg(stem, c3):
    """Форма ж.р. ед.ч. настоящего времени: ...ֶ C3 ֶת,
    но под конечной гортанной ע/ח сеголь переходит в патах:
    מִתְפַּתַּחַת, שׁוֹלַחַת."""
    v = PATAH if base(c3) in "עח" else SEGOL
    return stem + v + c3 + v + "ת"


def finalize(word):
    """Приводит форму к правильному виду в конце слова:
    конечная буква -> софит, патах гнува под конечными ע/ח."""
    chars = list(word)
    # индекс последней «настоящей» буквы (не значка огласовки)
    last = None
    for i in range(len(chars) - 1, -1, -1):
        if unicodedata.combining(chars[i]) == 0:
            last = i
            break
    if last is None:
        return unicodedata.normalize("NFC", word)

    letter = chars[last]
    tail = chars[last + 1:]          # значки после последней буквы

    # патах гнува: ...ֵחַ, ...ִיעַ и т.п.
    if letter in "עח" and not tail:
        prev_marks = []
        for j in range(last - 1, -1, -1):
            if unicodedata.combining(chars[j]) != 0:
                prev_marks.append(chars[j])
            else:
                break
        # у "и" перед ע/ח между ними стоит йод: הִצְלִיחַ
        if any(m in NEEDS_FURTIVE for m in prev_marks) or (
            chars[last - 1] == "י" if last > 0 else False
        ):
            chars.append(PATAH)

    # софит
    if letter in SOFIT and not tail:
        chars[last] = SOFIT[letter]

    return unicodedata.normalize("NFC", "".join(chars))


def build(past, present):
    """Прогоняет все формы через finalize()."""
    return (
        {k: finalize(v) for k, v in past.items()},
        {k: finalize(v) for k, v in present.items()},
    )


def nun_nu(stem_consonant, stem):
    """Окончание «мы»: если основа кончается на נ, נ сливается с נוּ."""
    if base(stem_consonant) == "נ":
        return stem + DAGESH + "וּ"
    return stem + SHVA + "נ" + "וּ"


# ---------------------------------------------------------------- пааль

def paal(c1, c2, c3):
    """Пааль, правильный трёхбуквенный корень (шлемим)."""
    heavy = d(c1) + QAMATS + c2 + PATAH + c3
    light = d(c1) + shva_or_hataf(c1) + c2 + PATAH + c3
    third = d(c1) + QAMATS + c2 + shva_or_hataf(c2)

    past = {
        "אני": heavy + SHVA + "ת" + DAGESH + HIRIQ + "י",
        "אתה": heavy + SHVA + "ת" + DAGESH + QAMATS,
        "את": heavy + SHVA + "ת" + DAGESH + SHVA,
        "הוא": heavy,
        "היא": third + c3 + QAMATS + "ה",
        "אנחנו": nun_nu(c3, heavy),
        "אתם": light + SHVA + "ת" + DAGESH + SEGOL + "ם",
        "אתן": light + SHVA + "ת" + DAGESH + SEGOL + "ן",
        "הם/הן": third + c3 + "וּ",
    }

    stem = d(c1) + "וֹ"
    present = {
        "m_sg": stem + c2 + TSERE + c3,
        "f_sg": fem_sg(stem + c2, c3),
        "m_pl": stem + c2 + shva_or_hataf(c2) + c3 + HIRIQ + "ים",
        "f_pl": stem + c2 + shva_or_hataf(c2) + c3 + "וֹת",
    }
    return build(past, present)


def paal_lh(c1, c2):
    """Пааль с третьей корневой ה (ל״ה): קנה, בנה, רצה..."""
    heavy = d(c1) + QAMATS + c2 + HIRIQ + "י"
    light = d(c1) + shva_or_hataf(c1) + c2 + HIRIQ + "י"

    past = {
        "אני": heavy + "ת" + HIRIQ + "י",
        "אתה": heavy + "ת" + QAMATS,
        "את": heavy + "ת",
        "הוא": d(c1) + QAMATS + c2 + QAMATS + "ה",
        "היא": d(c1) + QAMATS + c2 + shva_or_hataf(c2) + "ת" + QAMATS + "ה",
        "אנחנו": heavy + "נ" + "וּ",
        "אתם": light + "ת" + SEGOL + "ם",
        "אתן": light + "ת" + SEGOL + "ן",
        "הם/הן": d(c1) + QAMATS + c2 + "וּ",
    }
    stem = d(c1) + "וֹ"
    present = {
        "m_sg": stem + c2 + SEGOL + "ה",
        "f_sg": stem + c2 + QAMATS + "ה",
        "m_pl": stem + c2 + HIRIQ + "ים",
        "f_pl": stem + c2 + "וֹת",
    }
    return build(past, present)


def hollow(c1, c3, short_vowel=PATAH):
    """Полые двухбуквенные (ע״ו/ע״י): קום, גור, רוץ, שים..."""
    short = d(c1) + short_vowel + c3
    long_ = d(c1) + QAMATS + c3

    past = {
        "אני": short + SHVA + "ת" + DAGESH + HIRIQ + "י",
        "אתה": short + SHVA + "ת" + DAGESH + QAMATS,
        "את": short + SHVA + "ת" + DAGESH + SHVA,
        "הוא": long_,
        "היא": long_ + QAMATS + "ה",
        "אנחנו": nun_nu(c3, short),
        "אתם": short + SHVA + "ת" + DAGESH + SEGOL + "ם",
        "אתן": short + SHVA + "ת" + DAGESH + SEGOL + "ן",
        "הם/הן": long_ + "וּ",
    }
    present = {
        "m_sg": long_,
        "f_sg": long_ + QAMATS + "ה",
        "m_pl": long_ + HIRIQ + "ים",
        "f_pl": long_ + "וֹת",
    }
    return build(past, present)


def hollow_alef(c1, c3):
    """Полые с корневым א (בוא) — без дагеша в окончаниях."""
    stem = d(c1) + QAMATS + c3
    past = {
        "אני": stem + "ת" + HIRIQ + "י",
        "אתה": stem + "ת" + QAMATS,
        "את": stem + "ת",
        "הוא": stem,
        "היא": stem + QAMATS + "ה",
        "אנחנו": stem + "נ" + "וּ",
        "אתם": stem + "ת" + SEGOL + "ם",
        "אתן": stem + "ת" + SEGOL + "ן",
        "הם/הן": stem + "וּ",
    }
    present = {
        "m_sg": stem,
        "f_sg": stem + QAMATS + "ה",
        "m_pl": stem + HIRIQ + "ים",
        "f_pl": stem + "וֹת",
    }
    return build(past, present)


# ---------------------------------------------------------------- пиэль

def piel(c1, c2, c3):
    """Пиэль: דיבר, קיבל, שילם... (удвоение второй корневой)."""
    v1, cc2 = doubled(HIRIQ, c2)
    stem = d(c1) + v1 + cc2 + PATAH + c3
    third = d(c1) + v1 + cc2 + shva_or_hataf(c2) + c3

    past = {
        "אני": stem + SHVA + "ת" + DAGESH + HIRIQ + "י",
        "אתה": stem + SHVA + "ת" + DAGESH + QAMATS,
        "את": stem + SHVA + "ת" + DAGESH + SHVA,
        "הוא": d(c1) + v1 + cc2 + TSERE + c3,
        "היא": third + QAMATS + "ה",
        "אנחנו": nun_nu(c3, stem),
        "אתם": stem + SHVA + "ת" + DAGESH + SEGOL + "ם",
        "אתן": stem + SHVA + "ת" + DAGESH + SEGOL + "ן",
        "הם/הן": third + "וּ",
    }
    pv, pc2 = doubled(PATAH, c2)
    p = "מ" + SHVA + c1 + pv + pc2
    present = {
        "m_sg": p + TSERE + c3,
        "f_sg": fem_sg(p, c3),
        "m_pl": p + shva_or_hataf(c2) + c3 + HIRIQ + "ים",
        "f_pl": p + shva_or_hataf(c2) + c3 + "וֹת",
    }
    return build(past, present)


# ---------------------------------------------------------------- ифиль

def hifil(c1, c2, c3):
    """Ифиль: הרגיש, הזמין, הסביר..."""
    short = "ה" + HIRIQ + c1 + SHVA + d(c2) + PATAH + c3
    long_ = "ה" + HIRIQ + c1 + SHVA + d(c2) + HIRIQ + "י" + c3

    past = {
        "אני": short + SHVA + "ת" + DAGESH + HIRIQ + "י",
        "אתה": short + SHVA + "ת" + DAGESH + QAMATS,
        "את": short + SHVA + "ת" + DAGESH + SHVA,
        "הוא": long_,
        "היא": long_ + QAMATS + "ה",
        "אנחנו": nun_nu(c3, short),
        "אתם": short + SHVA + "ת" + DAGESH + SEGOL + "ם",
        "אתן": short + SHVA + "ת" + DAGESH + SEGOL + "ן",
        "הם/הן": long_ + "וּ",
    }
    p = "מ" + PATAH + c1 + SHVA + d(c2) + HIRIQ + "י" + c3
    present = {
        "m_sg": p,
        "f_sg": p + QAMATS + "ה",
        "m_pl": p + HIRIQ + "ים",
        "f_pl": p + "וֹת",
    }
    return build(past, present)


# ---------------------------------------------------------------- итпаэль

def hitpael(c1, c2, c3):
    """Итпаэль: התקשר, התחתן, התרגל..."""
    pre = "ה" + HIRIQ + "ת" + SHVA
    v1, cc2 = doubled(PATAH, c2)
    stem = pre + d(c1) + v1 + cc2 + PATAH + c3
    third = pre + d(c1) + v1 + cc2 + shva_or_hataf(c2) + c3

    past = {
        "אני": stem + SHVA + "ת" + DAGESH + HIRIQ + "י",
        "אתה": stem + SHVA + "ת" + DAGESH + QAMATS,
        "את": stem + SHVA + "ת" + DAGESH + SHVA,
        "הוא": pre + d(c1) + v1 + cc2 + TSERE + c3,
        "היא": third + QAMATS + "ה",
        "אנחנו": nun_nu(c3, stem),
        "אתם": stem + SHVA + "ת" + DAGESH + SEGOL + "ם",
        "אתן": stem + SHVA + "ת" + DAGESH + SEGOL + "ן",
        "הם/הן": third + "וּ",
    }
    p = "מ" + HIRIQ + "ת" + SHVA + d(c1) + v1 + cc2
    present = {
        "m_sg": p + TSERE + c3,
        "f_sg": fem_sg(p, c3),
        "m_pl": p + shva_or_hataf(c2) + c3 + HIRIQ + "ים",
        "f_pl": p + shva_or_hataf(c2) + c3 + "וֹת",
    }
    return build(past, present)
