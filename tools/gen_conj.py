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
HATAF_SEGOL = "ֱ"
HATAF_PATAH = "ֲ"
HIRIQ = "ִ"
TSERE = "ֵ"
SEGOL = "ֶ"
PATAH = "ַ"
QAMATS = "ָ"
HOLAM = "ֹ"
DAGESH = "ּ"

# Будущее время. В современном иврите ряд форм совпадает, поэтому для
# викторины они объединены в одну ячейку — иначе у двух разных вопросов
# был бы один и тот же правильный ответ:
#   אתה  и  היא     -> תִּכְתּוֹב
#   אתם  и  אתן     -> תִּכְתְּבוּ
FUTURE_SLOTS = ["אני", "אתה/היא", "את", "הוא", "אנחנו", "אתם/אתן", "הם/הן"]

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


# ================================================================
#                        БУДУЩЕЕ ВРЕМЯ
# ================================================================
# Приставки будущего времени. У 1-го лица ед.ч. — א, у 2-го и 3-го ж.р. — ת,
# у 3-го м.р. — י, у 1-го мн.ч. — נ. Гласная приставки зависит от биньяна.

def _future(prefix_vowel, first_person_vowel, body_base, body_suffixed):
    """Собирает 7 форм будущего из готовых «тел» слова.

    body_base      — тело для форм без окончания (אני, אתה/היא, הוא, אנחנו)
    body_suffixed  — тело для форм с окончанием (את, אתם/אתן, הם/הן)
    """
    p = prefix_vowel
    return {
        "אני": "א" + first_person_vowel + body_base,
        "אתה/היא": "ת" + DAGESH + p + body_base,
        "את": "ת" + DAGESH + p + body_suffixed + HIRIQ + "י",
        "הוא": "י" + p + body_base,
        "אנחנו": "נ" + p + body_base,
        "אתם/אתן": "ת" + DAGESH + p + body_suffixed + "וּ",
        "הם/הן": "י" + p + body_suffixed + "וּ",
    }


def paal_future(c1, c2, c3, vowel=None):
    """Пааль. Тематическая гласная: холам (יִכְתּוֹב) или патах (יִשְׁלַח).
    Патах — если 2-я или 3-я корневая гортанная; иначе холам."""
    if vowel is None:
        vowel = PATAH if (base(c2) in GUTTURAL or base(c3) in GUTTURAL) else "וֹ"

    if base(c1) in GUTTURAL:
        # Гортанная 1-я корневая: приставка с патахом. Под ע и ה — хатаф
        # (יַעֲבֹד), под ח — простой шва (יַחְשֹׁב).
        hataf = base(c1) in "עה"
        if hataf:
            # после хатафа стоит гласная, поэтому дагеша во 2-й корневой нет
            base_body = c1 + HATAF_PATAH + c2 + vowel + c3
            first_body = c1 + HATAF_SEGOL + c2 + vowel + c3
            # тут шва под 2-й корневой закрывает слог (תַּעַבְ-דִּי),
            # поэтому 3-я корневая из бегадкефат получает дагеш
            suf_body = c1 + PATAH + c2 + SHVA + d(c3)
        else:
            # шва-нах закрывает слог -> 2-я корневая получает дагеш
            base_body = c1 + SHVA + d(c2) + vowel + c3
            first_body = base_body
            suf_body = c1 + SHVA + d(c2) + shva_or_hataf(c2) + c3
        forms = _future(PATAH, SEGOL, base_body, suf_body)
        forms["אני"] = "א" + SEGOL + first_body
        return {k: finalize(v) for k, v in forms.items()}

    base_body = c1 + SHVA + d(c2) + vowel + c3
    suf_body = c1 + SHVA + d(c2) + shva_or_hataf(c2) + c3
    return {k: finalize(v) for k, v in _future(HIRIQ, SEGOL, base_body, suf_body).items()}


def paal_lh_future(c1, c2):
    """Пааль ל״ה: יִקְנֶה, תִּקְנִי, יִקְנוּ."""
    if base(c1) in GUTTURAL:
        pv, fpv = PATAH, SEGOL
        under = HATAF_PATAH if base(c1) in "עה" else SHVA
        base_body = c1 + under + c2 + SEGOL + "ה"
        suf_body = c1 + under + c2
        forms = _future(pv, fpv, base_body, suf_body)
        forms["אני"] = "א" + SEGOL + c1 + (HATAF_SEGOL if base(c1) in "עה" else SHVA) + c2 + SEGOL + "ה"
        return {k: finalize(v) for k, v in forms.items()}

    base_body = c1 + SHVA + c2 + SEGOL + "ה"
    suf_body = c1 + SHVA + c2
    return {k: finalize(v) for k, v in _future(HIRIQ, SEGOL, base_body, suf_body).items()}


def hollow_future(c1, c3, mid="וּ"):
    """Полые: יָקוּם, יָבוֹא, יָשִׂים. Приставка с камацем."""
    body = c1 + mid + c3
    return {k: finalize(v) for k, v in _future(QAMATS, QAMATS, body, body).items()}


def piel_future(c1, c2, c3):
    """Пиэль: יְדַבֵּר, תְּדַבְּרִי, יְדַבְּרוּ. Приставка со шва (у אני — хатаф-патах)."""
    v1, cc2 = doubled(PATAH, c2)
    base_body = c1 + v1 + cc2 + TSERE + c3
    suf_body = c1 + v1 + cc2 + shva_or_hataf(c2) + c3
    return {k: finalize(v) for k, v in
            _future(SHVA, HATAF_PATAH, base_body, suf_body).items()}


def hifil_future(c1, c2, c3):
    """Ифиль: יַרְגִּישׁ, תַּרְגִּישִׁי, יַרְגִּישׁוּ. Хирик-йод сохраняется везде."""
    body = c1 + SHVA + d(c2) + HIRIQ + "י" + c3
    return {k: finalize(v) for k, v in _future(PATAH, PATAH, body, body).items()}


def hitpael_future(c1, c2, c3):
    """Итпаэль: יִתְקַשֵּׁר, תִּתְקַשְּׁרִי, יִתְקַשְּׁרוּ."""
    v1, cc2 = doubled(PATAH, c2)
    pre = "ת" + SHVA
    base_body = pre + d(c1) + v1 + cc2 + TSERE + c3
    suf_body = pre + d(c1) + v1 + cc2 + shva_or_hataf(c2) + c3
    return {k: finalize(v) for k, v in _future(HIRIQ, SEGOL, base_body, suf_body).items()}
