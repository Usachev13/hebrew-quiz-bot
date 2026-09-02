# -*- coding: utf-8 -*-
"""
Живые реакции бота: реплики, серии, память о прошлых ошибках.

Зачем отдельный модуль: тексты здесь правятся чаще всего остального,
и держать их вперемешку с логикой раунда — значит каждый раз лезть в
bot.py и рисковать сломать подсчёт очков. Здесь только чистые функции,
без Telegram — их можно прогнать тестами.

Главная идея — дозировка. Если бот выдаёт эмоцию на каждый ответ, через
день это шум, который хочется выключить. Поэтому:
  • на обычный ответ — короткая реплика из пула, без украшений;
  • отдельная строка появляется только когда есть что сказать:
    серия из 5, слово, на котором ученик уже спотыкался, идеальный раунд;
  • реакция-эмодзи на само сообщение — редко, на заметных вехах.

Про два языка
-------------
Реплики не переведены, а написаны заново. Дословный перевод здесь хуже
бесполезного: «Ага, оно самое» по-английски превращается в чужеродную
конструкцию, а интонация — единственное, ради чего этот модуль есть.
Английские пулы держат ту же меру: коротко, сухо, без восторга и без
восклицательных знаков там, где русский обходится точкой.

Число реплик в пулах намеренно одинаковым не делалось: пул нужен, чтобы
не повторяться, а не чтобы соответствовать другому языку.
"""

# Реплики. Пул нужен ровно затем, чтобы не повторяться: одна и та же
# фраза третий раз подряд — главное, из-за чего собеседник ощущается
# программой. Не повторяем последние RECENT_MEMORY штук.
RECENT_MEMORY = 6

CORRECT = {
    "ru": [
        "✅ Верно",
        "✅ Точно",
        "✅ Так и есть",
        "✅ Да, оно",
        "✅ Именно",
        "✅ Правильно",
        "✅ Есть",
        "✅ Ага, оно самое",
        "✅ В точку",
        "✅ Без запинки",
        "✅ Уверенно",
        "✅ Оно",
    ],
    "en": [
        "✅ Correct",
        "✅ That's it",
        "✅ Exactly",
        "✅ Yes, that one",
        "✅ Right",
        "✅ Spot on",
        "✅ Got it",
        "✅ That's the one",
        "✅ No hesitation",
        "✅ Confidently",
        "✅ Quite right",
        "✅ Yes",
    ],
}

WRONG = {
    "ru": [
        "❌ Не то. Правильно:",
        "❌ Мимо. Правильно:",
        "❌ Нет, тут",
        "❌ Не угадал. Верный ответ:",
        "❌ Почти мимо. Надо:",
        "❌ Нет. Запоминаем:",
        "❌ Не оно. Правильно:",
    ],
    "en": [
        "❌ Not that one. It's:",
        "❌ Missed. The answer:",
        "❌ No, it's:",
        "❌ Not quite. The right one:",
        "❌ Close, but it's:",
        "❌ No. Worth remembering:",
        "❌ Not it. Correct:",
    ],
}

# Описка — это не ошибка: слово вспомнил, промахнулся по буквам.
# Отдельный пул, чтобы тон отличался от настоящей ошибки.
TYPO = {
    "ru": [
        "⚠️ Почти! Пишется так:",
        "⚠️ Слово то, буква не та:",
        "⚠️ Считаю верным, но пишется:",
        "⚠️ Засчитано. Правильное написание:",
        "⚠️ Ага, только пишется:",
    ],
    "en": [
        "⚠️ Almost — the spelling is:",
        "⚠️ Right word, wrong letter:",
        "⚠️ Counting it, but it's spelled:",
        "⚠️ Accepted. Correct spelling:",
        "⚠️ Yes, only it's written:",
    ],
}

SKIPPED = {
    "ru": [
        "Пропускаем. Ответ:",
        "Ладно, вот ответ:",
        "Не беда. Ответ:",
        "Оставим на потом. Ответ:",
    ],
    "en": [
        "Skipping. The answer:",
        "Fair enough, here it is:",
        "No matter. The answer:",
        "Leave it for later. The answer:",
    ],
}


# --- Серии ---
#
# Ученик просил отмечать каждый пятый правильный подряд. Раунд из десяти
# вопросов, так что реально достижимы 5 и 10; остальные — задел под
# спринт на время, где серия может уйти дальше.
# Эмодзи берём только из набора, который Telegram разрешает ботам для
# реакций (👍 🔥 🎉 🏆 💯 🤯 …). Знаки вроде «⚡», которые в этом списке
# записаны с вариационным селектором, отдаём в текст, а не в реакцию:
# иначе setMessageReaction молча отвечает ошибкой.
#
# Эмодзи общие для обоих языков: они и есть то, что не требует перевода.
STREAK_LINES = {
    5: {"ru": "🔥 Пять подряд.",
        "en": "🔥 Five in a row.", "emoji": "🔥"},
    10: {"ru": "🔥 Десять подряд, ни одной осечки.",
         "en": "🔥 Ten in a row, not one slip.", "emoji": "🏆"},
    15: {"ru": "⚡ Пятнадцать подряд. Это уже не везение.",
         "en": "⚡ Fifteen in a row. That's not luck any more.", "emoji": "💯"},
    20: {"ru": "🏆 Двадцать подряд.",
         "en": "🏆 Twenty in a row.", "emoji": "🏆"},
    30: {"ru": "🏆 Тридцать подряд. Серьёзно?",
         "en": "🏆 Thirty in a row. Seriously?", "emoji": "🤯"},
}
# Дальше двадцати вехи каждые десять, чтобы длинная серия не молчала.
STREAK_STEP = 10
STREAK_FAR = {"ru": "🔥 {n} подряд.", "en": "🔥 {n} in a row.", "emoji": "🔥"}


def streak_event(n, lang="ru"):
    """Что сказать на серию длиной n. None — веху не проходим, молчим."""
    if n in STREAK_LINES:
        item = STREAK_LINES[n]
        return item.get(lang, item["ru"]), item["emoji"]
    if n > max(STREAK_LINES) and n % STREAK_STEP == 0:
        line = STREAK_FAR.get(lang, STREAK_FAR["ru"])
        return line.format(n=n), STREAK_FAR["emoji"]
    return None


# --- Память о слове ---
#
# Самое ценное, что у нас есть и чего нет у обычной викторины: история
# по каждой карточке уже лежит в базе. Бот, который помнит, что это
# слово тебя ловило в прошлый раз, ощущается собеседником, а не тестом.

MEMORY = {
    "caught_again": {
        "ru": "Это слово ловит тебя уже в {n}-й раз — возьми на карандаш.",
        "en": "That word has caught you {n} times now — worth a note.",
    },
    "caught_twice": {
        "ru": "Второй раз на нём спотыкаешься.",
        "en": "Second time it's tripped you.",
    },
    "beaten_many": {
        "ru": "А ведь оно тебя {n} раза подлавливало. Теперь с ходу.",
        "en": "And it caught you {n} times before. Straight through now.",
    },
    "beaten_once": {
        "ru": "В прошлый раз это слово тебя подловило — теперь взял.",
        "en": "This one caught you last time — you have it now.",
    },
    "solid": {
        "ru": "Это уже прочно сидит, вернётся нескоро.",
        "en": "That one sits firmly now, it won't be back soon.",
    },
}


def memory_line(before, is_correct, lang="ru"):
    """Что бот помнит про эту карточку. None — сказать нечего.

    before — состояние карточки ДО текущего ответа: {n_correct, n_wrong,
    box} или None, если слово встретилось впервые. При первом знакомстве
    молчим: «вижу тебя впервые» — это не наблюдение, а шум.
    """
    if not before:
        return None

    wrong = before.get("n_wrong", 0)
    box = before.get("box", 1)
    say = lambda key, **kw: MEMORY[key].get(lang, MEMORY[key]["ru"]).format(**kw)

    if not is_correct:
        if wrong >= 2:
            return say("caught_again", n=wrong + 1)
        if wrong == 1:
            return say("caught_twice")
        return None

    # Верно ответил на то, что раньше не давалось — это стоит отметить,
    # иначе прогресс не виден: ошибки помнятся, а победы нет.
    if wrong >= 2 and box <= 2:
        return say("beaten_many", n=wrong)
    if wrong == 1 and box <= 2:
        return say("beaten_once")
    if box >= 4:
        return say("solid")
    return None


# --- Итог раунда ---

SUMMARY = {
    "perfect": {
        "ru": "🎯 Идеально — весь раунд без единой ошибки.",
        "en": "🎯 Perfect — the whole round without a single mistake.",
    },
    "good": {
        "ru": "Хорошо: {score} из {total}.",
        "en": "Good: {score} of {total}.",
    },
    "half": {
        "ru": "{score} из {total}. Половина взята, есть куда расти.",
        "en": "{score} of {total}. Half of it is yours, room to grow.",
    },
    "raw": {
        "ru": "{score} из {total}. Тема ещё сырая — прогоним ещё раз.",
        "en": "{score} of {total}. This topic is still raw — let's run it again.",
    },
    "zero": {
        "ru": ("Ноль из десяти бывает у всех, кто взялся за новую тему. "
               "Прогоним ещё раз — эти же слова вернутся первыми."),
        "en": ("Nought out of ten happens to everyone starting a new topic. "
               "Let's run it again — these same words come back first."),
    },
    "best_streak": {
        "ru": "Лучшая серия: {n} подряд.",
        "en": "Best streak: {n} in a row.",
    },
}


def round_summary(score, total, best_streak, lang="ru"):
    """Итог раунда: оценка по проценту плюс лучшая серия."""
    pct = round(100 * score / total) if total else 0
    say = lambda key, **kw: SUMMARY[key].get(lang, SUMMARY[key]["ru"]).format(**kw)

    if score == total:
        head, emoji = say("perfect"), "🎉"
    elif pct >= 80:
        head, emoji = say("good", score=score, total=total), "👍"
    elif pct >= 50:
        head, emoji = say("half", score=score, total=total), None
    elif score > 0:
        head, emoji = say("raw", score=score, total=total), None
    else:
        head, emoji = say("zero"), None

    # Лучшую серию показываем, только если она о чём-то говорит:
    # «лучшая серия 2» — это не достижение, а издёвка.
    tail = ""
    if best_streak >= 3 and score != total:
        tail = "\n" + say("best_streak", n=best_streak)
    return f"{head}{tail}", emoji


# --- Выбор реплики без повторов ---

def pick(pool, recent, rng, lang="ru"):
    """Реплика из пула, но не из недавних. recent меняется на месте.

    Пул приходит либо словарём по языкам, либо готовым списком: второе
    оставлено ради тестов, которые передают свой набор строк.
    """
    if isinstance(pool, dict):
        pool = pool.get(lang) or pool["ru"]
    fresh = [p for p in pool if p not in recent] or list(pool)
    choice = rng.choice(fresh)
    recent.append(choice)
    del recent[:-RECENT_MEMORY]
    return choice
