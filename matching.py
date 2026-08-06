# -*- coding: utf-8 -*-
"""
Сверка ответа, набранного вручную.

Главная сложность: в наших данных слова записаны с огласовками
(חֻלְצָה), а пишут их без огласовок и по правилам «полного написания»
(כתיב מלא): חולצה — с буквой ו, которой в огласованной записи нет.
Поэтому наивное сравнение «сняли огласовки и сличили строки» браковало
бы правильные ответы.

Решение: из огласованной формы строим набор допустимых написаний
(и «скелет» без огласовок, и вариант полного написания), а сверх того
прощаем одну опечатку.
"""

import unicodedata

# Значки огласовок и дагеша: при наборе их не пишут.
NIQQUD = set(
    "ְֱֲֳִֵֶַָֹֺ"
    "ׇֻּֽׁׂ"
)

KUBUTS = "ֻ"      # ֻ  — в полном написании становится ו
HOLAM = "ֹ"       # ֹ  — тоже становится ו, если её ещё нет
PATAH = "ַ"
HIRIQ = "ִ"

# Конечные формы букв: пользователь может набрать любую.
FINALS = {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}


def _strip_niqqud(word):
    return "".join(c for c in word if c not in NIQQUD)


def _normalize(word):
    """Приводит строку к виду, пригодному для сравнения."""
    word = unicodedata.normalize("NFC", word or "")
    word = _strip_niqqud(word)
    word = "".join(FINALS.get(c, c) for c in word)
    # лишние пробелы и невидимые знаки направления письма
    word = word.replace("‎", "").replace("‏", "")
    return " ".join(word.split())


def _has_patah_before(word, idx):
    """Есть ли патах среди значков буквы, стоящей на позиции idx и левее.

    Просто посмотреть на word[idx] нельзя: при букве может быть несколько
    значков сразу (в אוֹפַנַּיִם между патахом и йодом стоит ещё дагеш),
    поэтому идём назад до самой буквы и проверяем все её значки.
    """
    i = idx
    while i >= 0 and unicodedata.combining(word[i]) != 0:
        if word[i] == PATAH:
            return True
        i -= 1
    return False


def _full_spelling(word):
    """Строит вариант «полного написания» (כתיב מלא) из огласованной формы.

    Правила, которые реально влияют на наш словарь:
      • кубуц   ֻ  -> ו   (סֻכָּר -> סוכר)
      • холам   ֹ  -> ו   (חֹם -> חום), если ו ещё нет
      • ...ַיִם     -> ...ַיִים  (двойственное число: מִכְנָסַיִם -> מכנסיים)
    """
    word = unicodedata.normalize("NFC", word or "")
    out = []
    for i, ch in enumerate(word):
        out.append(ch)
        if ch == KUBUTS:
            out.append("ו")
        elif ch == HOLAM:
            # холам уже написан через вав — второй не нужен
            if not (out and len(out) >= 2 and out[-2] == "ו"):
                out.append("ו")
        elif ch == HIRIQ and i >= 2 and word[i - 1] == "י" and _has_patah_before(word, i - 2):
            # окончание двойственного числа -аим пишут через два йода
            out.append("י")
    return _normalize("".join(out))


def accepted_forms(correct):
    """Все написания, которые считаем правильными."""
    return {_normalize(correct), _full_spelling(correct)} - {""}


def _levenshtein(a, b, limit=2):
    """Расстояние редактирования. Дальше limit не считаем — незачем."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > limit:
            return limit + 1
        prev = cur
    return prev[-1]


# Слова короче этого прощать не будем: в иврите куча трёхбуквенных слов,
# отличающихся одной буквой (רַע «плохой» и רָעֵב «голодный»), и поблажка
# на опечатку превратилась бы в приём чужого слова за верный ответ.
MIN_LEN_FOR_TYPO = 4


def check_answer(typed, correct, known_words=None):
    """Сравнивает набранный ответ с эталоном.

    known_words — множество нормализованных форм всех остальных карточек.
    Если пользователь набрал другое существующее слово, это ошибка, а не
    описка, даже когда отличие в одну букву.

    Возвращает "exact" — написано верно,
              "typo"  — описка в один символ (засчитываем, но показываем
                        правильное написание),
              "wrong" — не то слово.
    """
    typed_norm = _normalize(typed)
    if not typed_norm:
        return "wrong"

    forms = accepted_forms(correct)
    if typed_norm in forms:
        return "exact"

    # набрано другое реальное слово из банка — это не опечатка
    if known_words and typed_norm in known_words:
        return "wrong"

    if len(typed_norm) < MIN_LEN_FOR_TYPO:
        return "wrong"

    if any(_levenshtein(typed_norm, f) <= 1 for f in forms):
        return "typo"
    return "wrong"


def scramble(word, rng):
    """Буквы слова вразброс — для игры «Анаграмма».

    Перемешиваем «скелет» без огласовок: собирать слово по буквам с
    огласовками неудобно, да и набирает пользователь всё равно без них.
    Гарантируем, что порядок отличается от исходного, иначе загадка
    оказалась бы уже разгаданной.
    """
    letters = [c for c in _normalize(word) if c != " "]
    if len(letters) < 2:
        return letters
    original = list(letters)
    for _ in range(20):
        rng.shuffle(letters)
        if letters != original:
            return letters
    # слово из одинаковых букв — перемешать осмысленно нельзя
    return letters


def hint_for(correct, revealed=1):
    """Подсказка: первые буквы слова, остальное закрыто."""
    skeleton = _normalize(correct)
    if not skeleton:
        return ""
    shown = skeleton[:revealed]
    hidden = "".join("־" if c != " " else " " for c in skeleton[revealed:])
    return shown + hidden
