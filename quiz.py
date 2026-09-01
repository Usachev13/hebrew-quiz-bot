# -*- coding: utf-8 -*-
"""
Игровая логика: банки карточек, выбор вопроса, интервальные повторения.

Вынесено из bot.py, когда появился Mini App. Причина простая: у чата и
приложения должны быть одни правила. Если оставить подбор дистракторов и
приоритеты повторений внутри бота, приложению придётся их повторить — и
две копии начнут расходиться на первой же правке.

Здесь нет ничего от Telegram: только данные и чистые функции. Отправкой
сообщений занимается bot.py, HTTP-ответами — webapp.py.
"""

import random

import alphabet
import db
from matching import accepted_forms
from words import VOCAB, VERBS
from conjugations import (
    CONJUGATIONS,
    PAST_PERSONS, PAST_LABELS,
    PRESENT_SLOTS, PRESENT_LABELS,
    FUTURE_SLOTS, FUTURE_LABELS,
)

ROUND_LEN = 10

# Анаграмму предлагаем только там, где собирать слово из букв осмысленно:
# длинная глагольная форма разбирается на пятнадцать букв и учит терпению,
# а не языку.
ANAGRAM_MODES = {"vocab", "weak"}


def flatten(bank):
    """Превращает {категория: [(ru, he), ...]} в плоский список (ru, he, категория)."""
    items = []
    for category, words in bank.items():
        for ru, he in words:
            items.append((ru, he, category))
    return items


def flatten_tense(conj, tense, slots, labels):
    """Одно время из CONJUGATIONS -> плоский список (подсказка, форма, группа).

    Группа = глагол+время: дистракторы берутся из форм ТОГО ЖЕ глагола в
    том же времени, поэтому тренируется именно лицо/род/число, а не
    угадывание по внешнему виду разных корней."""
    items = []
    for root, data in conj.items():
        for slot in slots:
            he = data[tense].get(slot)
            if not he:
                continue
            prompt = f"{data['ru']} ({data['inf']}) — {labels[slot]}"
            items.append((prompt, he, f"{root}_{tense}"))
    return items


VOCAB_FLAT = flatten(VOCAB)
VERBS_FLAT = flatten(VERBS)
PAST_FLAT = flatten_tense(CONJUGATIONS, "past", PAST_PERSONS, PAST_LABELS)
PRESENT_FLAT = flatten_tense(CONJUGATIONS, "present", PRESENT_SLOTS, PRESENT_LABELS)
FUTURE_FLAT = flatten_tense(CONJUGATIONS, "future", FUTURE_SLOTS, FUTURE_LABELS)


def pick_card(remaining, priorities):
    """Выбирает следующую карточку с учётом интервальных повторений.

    Берём случайную из самой приоритетной группы (см. db.PRIORITY_*):
    сперва то, что пора повторить, затем новое, затем проблемное. Внутри
    группы порядок случайный — чтобы не заучивать последовательность.
    """
    if not priorities:
        return random.choice(remaining)
    rank = lambda w: priorities.get(w[0], db.PRIORITY_NEW)
    best = max(rank(w) for w in remaining)
    return random.choice([w for w in remaining if rank(w) == best])


def build_question(pool, used, priorities=None):
    """Выбирает карточку (ещё не заданную в этом раунде) и 3 дистрактора
    из той же категории/группы биньяна — так угадать наугад сложнее."""
    remaining = [w for w in pool if w[0] not in used]
    if not remaining:
        remaining = pool
    correct = pick_card(remaining, priorities or {})
    ru, he, cat = correct

    # Дистракторы обязаны отличаться не только от верного ответа, но и
    # друг от друга: в некоторых пулах разные карточки дают одинаковый
    # ответ (патах и камац оба читаются как «а»), и без этой проверки в
    # вопросе появлялись два одинаковых варианта.
    seen = {he}

    def take(candidates, need):
        random.shuffle(candidates)
        for w in candidates:
            if len(seen) > need:
                break
            if w[1] not in seen:
                seen.add(w[1])

    take([w for w in pool if w[2] == cat], 3)      # сначала из той же темы
    take([w for w in pool if w[2] != cat], 3)      # если не хватило — из любой

    options = list(seen)
    random.shuffle(options)
    return {"ru": ru, "correct": he, "options": options}


POOLS = {
    "vocab": VOCAB_FLAT,
    "verbs": VERBS_FLAT,
    "past": PAST_FLAT,
    "present": PRESENT_FLAT,
    "future": FUTURE_FLAT,
    # Курс алфавита (уровень 0)
    "alef_names": alphabet.pool_names(),
    "alef_sounds": alphabet.pool_sounds(),
    "alef_by_name": alphabet.pool_by_name(),
    "alef_finals": alphabet.pool_finals(),
    "alef_niqqud": alphabet.pool_niqqud(),
    "alef_syllables": alphabet.pool_syllables(),
    "alef_dotted": alphabet.pool_dotted(),
}
LABELS = {
    "vocab": "слова",
    "verbs": "глаголы",
    "past": "прошедшее время",
    "present": "настоящее время",
    "future": "будущее время",
    "alef_names": "названия букв",
    "alef_sounds": "звуки букв",
    "alef_by_name": "узнать букву по названию",
    "alef_finals": "конечные формы",
    "alef_niqqud": "огласовки",
    "alef_syllables": "чтение слогов",
    "alef_dotted": "точка меняет звук",
}

# Словарь разложен по двум разрезам. Бытовые темы — как в ульпане:
# человек учит слова кусками жизни, а не списком существительных.
# Грамматические группы вынесены отдельно, потому что тренируются иначе:
# там важна не тема, а форма.
TOPIC_LABELS = {
    "greetings": "Приветствия", "family": "Семья", "food": "Еда",
    "home": "Дом", "city": "Город", "transport": "Транспорт",
    "time": "Время", "weather": "Погода", "health": "Здоровье",
    "shopping": "Покупки", "work_study": "Работа и учёба",
    "clothes": "Одежда", "emotions": "Эмоции",
}
GRAMMAR_LABELS = {
    "adjectives": "Прилагательные", "adverbs": "Наречия",
    "personal_pronouns": "Местоимения (я, ты…)",
    "object_pronouns": "Местоимения (меня, его…)",
    "cardinals": "Числительные", "ordinals": "Порядковые",
    "question_words": "Вопросительные слова", "particles": "Частицы",
    "place_prepositions": "Предлоги места",
}

# Режимы курса алфавита: вопрос формулируется иначе, чем «как будет…»
ALPHABET_MODES = {m for m in LABELS if m.startswith("alef_")}

# Обратный поиск: по card_id (подсказке, с которой карточка легла в базу)
# найти сам ответ. Нужен статистике: список слабых мест без ивритского
# слова только перечисляет промахи, а с ним — повторяет материал.
ANSWERS = {mode: {ru: (he, cat) for ru, he, cat in pool}
           for mode, pool in POOLS.items()}

# Все допустимые написания каждого пула. Нужны, чтобы отличить описку от
# случая «набрал другое существующее слово» (см. matching.check_answer).
KNOWN_FORMS = {
    mode: set().union(*(accepted_forms(he) for _, he, _ in pool)) if pool else set()
    for mode, pool in POOLS.items()
}
# Раунд «слабые места» смешанный, поэтому описку в нём сверяем по всему
# банку сразу: иначе набранное слово из другого режима сойдёт за опечатку.
KNOWN_FORMS["weak"] = set().union(*KNOWN_FORMS.values())


def weak_pool(chat_id, limit=30):
    """Карточки, где больше всего ошибок — со всех режимов сразу.

    Возвращает (пул, {(подсказка, ответ): режим}). Режим на карточку
    нужен потому, что раунд смешанный: ответ должен лечь в статистику
    того режима, откуда карточка пришла, иначе повторения разъедутся.
    """
    try:
        weak = db.weak_cards(chat_id, limit=limit)
    except Exception as e:
        print(f"[weak_pool] {e}")
        return [], {}

    pool, modes = [], {}
    for w in weak:
        found = ANSWERS.get(w["mode"], {}).get(w["card_id"])
        if not found:
            continue          # карточка из старой версии словаря
        he, cat = found
        pool.append((w["card_id"], he, cat))
        modes[(w["card_id"], he)] = w["mode"]
    return pool, modes


def round_pool(chat_id, mode, cat):
    """Пул раунда, подпись к нему и карта режимов по карточкам."""
    if mode == "weak":
        pool, modes = weak_pool(chat_id)
        return pool, "мои слабые места", modes

    pool = POOLS[mode]
    if cat:
        pool = [w for w in pool if w[2] == cat]
        label = TOPIC_LABELS.get(cat) or GRAMMAR_LABELS.get(cat) or LABELS[mode]
        return pool, label.lower(), {}
    return pool, LABELS[mode], {}
