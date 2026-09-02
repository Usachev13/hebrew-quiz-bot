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
import cards
import db
import words_en
from cards import Card
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


def flatten(bank, en=None):
    """Превращает {категория: [(ru, he), ...]} в плоский список карточек.

    `en` — словарь переводов подсказки, ключ `cid`. Отсутствующий перевод
    не ошибка на этом уровне: карточка просто останется с русской
    подсказкой, а недостачу поимённо назовёт tools/check_i18n.py. Падать
    здесь нельзя — импорт quiz.py поднимает и бота, и приложение.
    """
    en = en or {}
    items = []
    for category, words in bank.items():
        for ru, he in words:
            cid = cards.vocab_cid(category, he)
            items.append(Card(ru, he, category, cid=cid, en=en.get(cid, "")))
    return items


def flatten_tense(conj, tense, slots, labels, en_labels=None):
    """Одно время из CONJUGATIONS -> плоский список (подсказка, форма, группа).

    Группа = глагол+время: дистракторы берутся из форм ТОГО ЖЕ глагола в
    том же времени, поэтому тренируется именно лицо/род/число, а не
    угадывание по внешнему виду разных корней."""
    en_labels = en_labels or {}
    items = []
    for root, data in conj.items():
        for slot in slots:
            he = data[tense].get(slot)
            if not he:
                continue
            prompt = f"{data['ru']} ({data['inf']}) — {labels[slot]}"
            meaning = words_en.ROOT_MEANINGS.get(root)
            label_en = en_labels.get(slot)
            en = f"{meaning} ({data['inf']}) — {label_en}" if meaning and label_en else ""
            items.append(Card(prompt, he, f"{root}_{tense}",
                              cid=cards.form_cid(root, slot), en=en))
    return items


VOCAB_FLAT = flatten(VOCAB, words_en.WORDS)
VERBS_FLAT = flatten(VERBS, words_en.VERBS)
PAST_FLAT = flatten_tense(CONJUGATIONS, "past", PAST_PERSONS, PAST_LABELS,
                          words_en.PAST_LABELS)
PRESENT_FLAT = flatten_tense(CONJUGATIONS, "present", PRESENT_SLOTS, PRESENT_LABELS,
                             words_en.PRESENT_LABELS)
FUTURE_FLAT = flatten_tense(CONJUGATIONS, "future", FUTURE_SLOTS, FUTURE_LABELS,
                            words_en.FUTURE_LABELS)


def pick_card(remaining, priorities):
    """Выбирает следующую карточку с учётом интервальных повторений.

    Берём случайную из самой приоритетной группы (см. db.PRIORITY_*):
    сперва то, что пора повторить, затем новое, затем проблемное. Внутри
    группы порядок случайный — чтобы не заучивать последовательность.
    """
    if not priorities:
        return random.choice(remaining)
    rank = lambda w: priorities.get(w.key(), db.PRIORITY_NEW)
    best = max(rank(w) for w in remaining)
    return random.choice([w for w in remaining if rank(w) == best])


INTRO_LEN = 6      # сколько новых слов показываем перед викториной
MIN_ROUND = 5      # короче этого раунд не имеет смысла запускать


def intro_cards(chat_id, mode, pool):
    """Карточки из пула, которых пользователь ещё ни разу не видел.

    До этого приложение сразу спрашивало слово, которого человек не
    встречал: викторина превращалась в угадайку, а первая коробка
    интервального повторения наполнялась случайными промахами. Сначала
    знакомство, потом вопрос.
    """
    if mode == "weak":
        return []                      # слабые места по определению уже видели
    try:
        seen = db.seen_cards(chat_id, mode)
    except Exception as e:
        print(f"[intro_cards] БД недоступна: {e}")
        return []
    fresh = [w for w in pool if w.key() not in seen]
    random.shuffle(fresh)
    return fresh[:INTRO_LEN]


def build_question(pool, used, priorities=None, pick_from=None, lang="ru"):
    """Выбирает карточку (ещё не заданную в этом раунде) и 3 дистрактора
    из той же категории/группы биньяна — так угадать наугад сложнее.

    pick_from сужает выбор самой карточки, не трогая дистракторы: после
    знакомства спрашиваем ровно те слова, которые только что показали, а
    неверные варианты по-прежнему берём из всей темы — иначе они были бы
    только из шести новых и ответ вычислялся бы по исключению.
    """
    source = pick_from if pick_from else pool
    remaining = [w for w in source if w.key() not in used]
    if not remaining:
        remaining = source
    correct = pick_card(remaining, priorities or {})
    answer = correct.answer(lang)

    # Дистракторы обязаны отличаться не только от верного ответа, но и
    # друг от друга: в некоторых пулах разные карточки дают одинаковый
    # ответ (патах и камац оба читаются как «а»), и без этой проверки в
    # вопросе появлялись два одинаковых варианта.
    seen = {answer}

    def take(candidates, need):
        random.shuffle(candidates)
        for w in candidates:
            if len(seen) > need:
                break
            if w.answer(lang) not in seen:
                seen.add(w.answer(lang))

    take([w for w in pool if w.cat == correct.cat], 3)   # сначала из той же темы
    take([w for w in pool if w.cat != correct.cat], 3)   # не хватило — из любой

    options = list(seen)
    random.shuffle(options)
    return {"id": correct.key(), "ru": correct.prompt(lang),
            "correct": answer, "options": options}


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

# Те же подписи по-английски. Держим рядом с русскими, а не в общем
# словаре интерфейса: это названия разделов учебного материала, они
# меняются вместе с самим материалом, а не с оформлением приложения.
LABELS_EN = {
    "vocab": "words",
    "verbs": "verbs",
    "past": "past tense",
    "present": "present tense",
    "future": "future tense",
    "alef_names": "letter names",
    "alef_sounds": "letter sounds",
    "alef_by_name": "find the letter by name",
    "alef_finals": "final forms",
    "alef_niqqud": "vowel signs",
    "alef_syllables": "reading syllables",
    "alef_dotted": "the dot changes the sound",
}
TOPIC_LABELS_EN = {
    "greetings": "Greetings", "family": "Family", "food": "Food",
    "home": "Home", "city": "City", "transport": "Transport",
    "time": "Time", "weather": "Weather", "health": "Health",
    "shopping": "Shopping", "work_study": "Work and study",
    "clothes": "Clothes", "emotions": "Emotions",
}
GRAMMAR_LABELS_EN = {
    "adjectives": "Adjectives", "adverbs": "Adverbs",
    "personal_pronouns": "Pronouns (I, you…)",
    "object_pronouns": "Pronouns (me, him…)",
    "cardinals": "Numbers", "ordinals": "Ordinal numbers",
    "question_words": "Question words", "particles": "Particles",
    "place_prepositions": "Prepositions of place",
}

WEAK_LABEL = {"ru": "мои слабые места", "en": "my weak spots"}


def section_label(mode, cat=None, lang="ru"):
    """Название раздела: тема, если она задана, иначе сам режим.

    Возвращает None, когда режим неизвестен: вызывающий по этому
    отличает «нечего продолжать» от пустой строки.
    """
    if lang == "en":
        topics, grammar, modes = TOPIC_LABELS_EN, GRAMMAR_LABELS_EN, LABELS_EN
    else:
        topics, grammar, modes = TOPIC_LABELS, GRAMMAR_LABELS, LABELS
    if mode == "weak":
        return WEAK_LABEL.get(lang, WEAK_LABEL["ru"])
    if cat:
        return topics.get(cat) or grammar.get(cat) or modes.get(mode)
    return modes.get(mode)

# Режимы курса алфавита: вопрос формулируется иначе, чем «как будет…»
ALPHABET_MODES = {m for m in LABELS if m.startswith("alef_")}

# Порядок прохождения — от узнавания к чтению. Раньше разделы шли по
# алфавиту внутреннего ключа: «узнать букву по названию» оказывалось
# первым, а «названия букв» четвёртым, хотя без вторых первое
# бессмысленно. Теперь разделы ещё и нумеруются буквами в приложении,
# и случайный порядок стал бы прямой дезинформацией.
ALPHABET_ORDER = (
    "alef_names",      # как называется буква
    "alef_sounds",     # какой звук она даёт
    "alef_by_name",    # обратный ход: узнать букву по названию
    "alef_finals",     # конечные формы
    "alef_dotted",     # дагеш меняет звук
    "alef_niqqud",     # огласовки
    "alef_syllables",  # и только теперь — чтение слогов
)
assert set(ALPHABET_ORDER) == ALPHABET_MODES, "порядок разошёлся с режимами"

# Обратный поиск: по ключу карточки найти её саму. Нужен и проверке
# ответа, и статистике: список слабых мест без ивритского слова только
# перечисляет промахи, а с карточкой — повторяет материал.
#
# Раньше здесь лежала пара (ответ, категория), а ключом была русская
# подсказка. Теперь ключ устойчивый, а значение — вся карточка: ответ у
# алфавита зависит от языка («алеф» или «alef»), и обрезанное значение
# пришлось бы доставать заново.
ANSWERS = {mode: {c.key(): c for c in pool} for mode, pool in POOLS.items()}

# Тот же поиск по ПОДСКАЗКЕ, а не по ключу. Нужен на время перехода:
# старая версия приложения присылает обратно текст вопроса, потому что
# раньше он и был ключом. Пока у людей в телефонах живёт та версия,
# ответы должны доходить.
#
# Английские подсказки здесь обязательны, и это не запас на будущее.
# Язык определяется из настроек Telegram сразу после выкладки: человек с
# английским телефоном получит вопрос «bread» ещё старым приложением и
# пришлёт обратно именно «bread». Без этой строки его ответ вернулся бы
# ошибкой «unknown card», и раунд встал бы намертво.
LEGACY_ANSWERS = {
    mode: {p: c for c in pool for p in (c.ru, c.en) if p}
    for mode, pool in POOLS.items()
}


def find_card(mode, card_id):
    """Карточка по ключу — новому или старому."""
    by_mode = ANSWERS.get(mode, {})
    return by_mode.get(card_id) or LEGACY_ANSWERS.get(mode, {}).get(card_id)


def id_migration_map():
    """{режим: {старая русская подсказка: новый ключ}} для db.migrate_card_ids.

    Старый ключ — ровно то, что раньше клалось в базу: `Card.ru`. Новый
    лежит в `cid`. Пары строятся из тех же карточек, что показываются
    сейчас, поэтому карта не может разойтись с данными: слово, которого
    в словаре больше нет, и переносить некуда.
    """
    return {mode: {c.ru: c.cid for c in pool if c.cid and c.cid != c.ru}
            for mode, pool in POOLS.items()}


# Все допустимые написания каждого пула. Нужны, чтобы отличить описку от
# случая «набрал другое существующее слово» (см. matching.check_answer).
# Берём ивритское поле, а не язык интерфейса: набором проверяются только
# словарь и глаголы, где ответ на иврите при любом языке.
KNOWN_FORMS = {
    mode: set().union(*(accepted_forms(c.he) for c in pool)) if pool else set()
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
        card = ANSWERS.get(w["mode"], {}).get(w["card_id"])
        if not card:
            continue          # карточка из старой версии словаря
        pool.append(card)
        modes[card.key()] = w["mode"]
    return pool, modes


def round_pool(chat_id, mode, cat, lang="ru"):
    """Пул раунда, подпись к нему и карта режимов по карточкам."""
    if mode == "weak":
        pool, modes = weak_pool(chat_id)
        return pool, section_label("weak", lang=lang), modes

    pool = POOLS[mode]
    if cat:
        pool = [w for w in pool if w.cat == cat]
        return pool, section_label(mode, cat, lang).lower(), {}
    return pool, section_label(mode, lang=lang), {}


# ---------- слово дня ----------

def pick_daily_word(chat_id):
    """Слово дня. По очереди, от самого желанного к запасному варианту:

    1. не приходило как слово дня и ещё не встречалось в раундах — новое;
    2. не приходило как слово дня, хоть и встречалось — напоминание;
    3. приходило дольше всех остальных — круг пошёл заново.

    Важен первый фильтр. Отбор только по «не встречалось в раундах» не
    годится: этот запас тает по мере учёбы, и на 272 отвеченных словах из
    273 выбор сужается до одного — оно и приходит каждый день.
    """
    try:
        seen = db.seen_cards(chat_id, "vocab")
        sent = db.daily_sent_words(chat_id)
    except Exception as e:
        print(f"[pick_daily_word] БД недоступна: {e}")
        return random.choice(VOCAB_FLAT)

    never_sent = [w for w in VOCAB_FLAT if w.key() not in sent]
    unseen = [w for w in never_sent if w.key() not in seen]
    if unseen:
        return random.choice(unseen)
    if never_sent:
        return random.choice(never_sent)

    oldest = min(sent.values())
    return random.choice([w for w in VOCAB_FLAT if sent.get(w.key()) == oldest])
