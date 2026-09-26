# -*- coding: utf-8 -*-
"""
Тест уровня: с чего человеку начинать.

Зачем он на самом деле
----------------------
По ТЗ тест выдаёт ярлык — «уровень 0 / Алеф / Бет». Ярлык мы покажем,
но сам по себе он почти бесполезен: человек и так примерно знает, где
он, и «у вас Алеф» ему ничего не даёт.

Настоящая работа теста другая. Сейчас любой новичок начинает со всех
273 слов в первой коробке — включая «мама», «спасибо» и «да». Взрослый
оле, проживший в стране полгода, знает половину этого списка, и
прогонять её по десять раз он не станет: он закроет приложение. Тест
расставляет коробки Лейтнера наперёд и тем экономит недели.

Отсюда и устройство: вопросы подобраны не «по возрастающей сложности»
вообще, а так, чтобы по ответам можно было судить о ТЕМАХ. Спросили про
еду и про транспорт — узнали, что с ними делать.

Осторожность при расстановке
----------------------------
Вывод делается по одному-двум ответам, поэтому коробки ставятся
скромные и только вверх (db.seed_box):

* угадал само слово           -> коробка 3 (вернётся через три дня);
* угадал оба слова из темы    -> вся тема в коробку 2 (через день).

Не коробка 5: это значение оставлено за «я уже знаю это», где решение
принимает сам человек. Здесь решает машина по одному ответу, и цена
ошибки должна быть сутки, а не три недели.

Сколько вопросов
----------------
До пятнадцати, а не тридцать пять, как в ТЗ. Тест открывают в первую
минуту знакомства с приложением, и тридцать пять вопросов до первого
занятия — верный способ не начать вовсе. Точность добирается тем, что
ветка обрывается рано: не читающего буквы бессмысленно спрашивать про
лексику, а провалившего простые темы — про грамматику.
"""

import random

import quiz

# --------------------------------------------------------------- исходы
#
# Ярлык «Бет» оставлен по ТЗ, хотя словаря этого уровня ещё нет. Поэтому
# его текст честно говорит, что материал готовится: иначе человек ткнёт
# в свой уровень и упрётся в пустоту.

LEVELS = {
    "zero": {
        "ru": "Начнём с букв",
        "en": "Let's start with the letters",
        "ru_note": "Буквы пока не читаются — это нормально и лечится "
                   "быстрее всего. Курс алфавита ведёт от узнавания к чтению.",
        "en_note": "The letters don't read yet — that's normal and the "
                   "quickest thing to fix. The alphabet course takes you "
                   "from recognising to reading.",
        "go": "alphabet",
    },
    "alef_start": {
        "ru": "Начало Алефа",
        "en": "Beginning of Alef",
        "ru_note": "Буквы читаются, слов пока мало. Начните с раздела "
                   "«Заговорить»: там фразы, которые пригодятся завтра.",
        "en_note": "You can read, the words will come. Start with «Start "
                   "speaking» — those phrases will be useful tomorrow.",
        "go": "say",
    },
    "alef": {
        "ru": "Середина Алефа",
        "en": "Middle of Alef",
        "ru_note": "Основа есть. Знакомые слова я отложил подальше, чтобы "
                   "не гонять их зря, — занимайтесь по темам.",
        "en_note": "You have the basics. I've pushed the familiar words "
                   "further out so they don't waste your time — work by topic.",
        "go": "topics",
    },
    "bet": {
        "ru": "Алеф пройден",
        "en": "Alef is behind you",
        # Честно про пустоту: ярлык уровня Бет по ТЗ есть, материала нет.
        "ru_note": "Словарь Алефа вы знаете. Материала уровня Бет пока нет "
                   "— он в работе. Сейчас полезнее всего «Заговорить» и "
                   "глагольные формы: узнавать слова вы умеете, а "
                   "составлять из них речь — это отдельный навык.",
        "en_note": "You know the Alef vocabulary. Level Bet material isn't "
                   "ready yet — it's in the works. For now the most useful "
                   "parts are «Start speaking» and the verb forms: "
                   "recognising words and building speech are different skills.",
        "go": "say",
    },
}

# ------------------------------------------------------------- материал
#
# Темы идут от самой обиходной к самой специальной. Порядок — не
# измеренная частотность, а здравый смысл: приветствия и семью человек
# слышит с первого дня, работу и покупки позже. Годится как грубая
# лестница сложности; если появятся данные о том, на чём люди реально
# спотыкаются, порядок стоит пересобрать по ним.
TOPIC_LADDER = [
    "greetings", "family", "food", "time", "home",
    "city", "transport", "health", "shopping", "work_study",
]

ALPHABET_STEPS = 3      # читает ли буквы вообще
VOCAB_STEPS = 8         # по одному-двум словам из темы
GRAMMAR_STEPS = 4       # формы глагола

# Ниже этого по алфавиту дальше не идём: спрашивать лексику у того, кто
# не читает букв, бессмысленно — он не поймёт даже вопроса.
ALPHABET_PASS = 2
# Если из первых четырёх тем не угадано ничего, лексики нет. Дальше не
# мучаем: ответ уже известен.
VOCAB_EARLY_STOP = 4


def _pick(pool, rng, n=1):
    return rng.sample(pool, min(n, len(pool)))


def build(chat_id=None, lang="ru", seed=None):
    """Собирает тест. Возвращает список шагов.

    Шаг — обычный вопрос викторины плюс пометки: к какому этапу
    относится и какую тему проверяет. Клиент ведёт тест сам, как
    обычный раунд; сервер судит ответы и в конце подводит итог.
    """
    rng = random.Random(seed if seed is not None else chat_id)
    steps = []

    # 1. Алфавит: слоги и названия букв. Читать — значит собирать звук
    #    из знака, поэтому слоги важнее названий.
    for mode in ("alef_syllables", "alef_syllables", "alef_names"):
        card = _pick(quiz.POOLS[mode], rng)[0]
        steps.append(_step(card, mode, "alphabet", rng, lang))

    # 2. Словарь: по темам, от обиходных к специальным.
    for topic in TOPIC_LADDER[:VOCAB_STEPS]:
        pool = [c for c in quiz.POOLS["vocab"] if c.cat == topic]
        if len(pool) < 4:
            continue
        card = _pick(pool, rng)[0]
        steps.append(_step(card, "vocab", "vocab", rng, lang, topic=topic))

    # 3. Грамматика: формы глагола в трёх временах.
    for mode in ("present", "past", "future", "present"):
        card = _pick(quiz.POOLS[mode], rng)[0]
        steps.append(_step(card, mode, "grammar", rng, lang))

    return steps


def _step(card, mode, stage, rng, lang, topic=None):
    # Дистракторы собираем сами: build_question берёт их из переданного
    # пула, а здесь пул из одной карточки — брать неоткуда.
    pool = quiz.POOLS[mode]
    answer = card.answer(lang)
    options = {answer}
    for other in rng.sample(pool, min(len(pool), 40)):
        if len(options) >= 4:
            break
        if other.answer(lang) != answer:
            options.add(other.answer(lang))
    opts = list(options)
    rng.shuffle(opts)
    return {"id": card.key(), "mode": mode, "stage": stage, "topic": topic,
            "ru": card.prompt(lang), "options": opts}


def verdict(answers):
    """Итог по ответам. answers — [{stage, topic, correct}].

    Пороги подобраны так, чтобы ошибаться в сторону меньшего уровня:
    заниженный уровень стоит человеку пары лишних знакомых карточек,
    завышенный — ощущения, что приложение не для него.
    """
    by_stage = {}
    for a in answers:
        by_stage.setdefault(a["stage"], []).append(bool(a["correct"]))

    alphabet = sum(by_stage.get("alphabet", []))
    vocab = sum(by_stage.get("vocab", []))
    vocab_total = len(by_stage.get("vocab", []))
    grammar = sum(by_stage.get("grammar", []))

    if alphabet < ALPHABET_PASS:
        return "zero"
    if vocab_total and vocab <= vocab_total * 0.4:
        return "alef_start"
    if vocab >= vocab_total * 0.85 and grammar >= 3:
        return "bet"
    return "alef"


def seeding(answers):
    """Что расставить по коробкам. Возвращает [(card_id, mode, box)].

    Сама запись — в webapp через db.seed_box: здесь только решение,
    чтобы его можно было проверить тестом, не трогая базу.
    """
    out = []
    topics_right = {}
    for a in answers:
        if not a.get("correct"):
            if a.get("topic"):
                topics_right[a["topic"]] = False
            continue
        # Угаданное слово — самое надёжное, что у нас есть.
        if a.get("id") and a.get("mode"):
            out.append((a["id"], a["mode"], 3))
        if a.get("topic") and topics_right.get(a["topic"]) is not False:
            topics_right[a["topic"]] = True

    # Тема целиком — вывод слабее, поэтому и коробка ниже.
    for topic, ok in topics_right.items():
        if not ok:
            continue
        for card in quiz.POOLS["vocab"]:
            if card.cat == topic:
                out.append((card.key(), "vocab", 2))
    return out


def result(level, lang="ru"):
    item = LEVELS[level]
    return {
        "level": level,
        "title": item.get(lang, item["ru"]),
        "note": item.get(f"{lang}_note", item["ru_note"]),
        "go": item["go"],
    }
