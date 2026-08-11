# -*- coding: utf-8 -*-
"""
Telegram-бот для тренировки слов и глаголов иврита.
Работает в режиме webhook (подходит для бесплатного PythonAnywhere).

Настройка:
1. Впиши токен бота в переменную TELEGRAM_TOKEN ниже (или задай
   переменную окружения TELEGRAM_TOKEN на хостинге).
2. Задеплой этот файл как Flask web app (см. README.md).
3. Один раз запусти set_webhook.py, чтобы Telegram знал, куда слать апдейты.
"""

import os
import random
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify

import alphabet
import audio
import db
import reactions
from matching import check_answer, accepted_forms, hint_for, scramble
from translit import translit
from words import VOCAB, VERBS
from conjugations import (
    CONJUGATIONS,
    PAST_PERSONS, PAST_LABELS,
    PRESENT_SLOTS, PRESENT_LABELS,
    FUTURE_SLOTS, FUTURE_LABELS,
)

# Явно указываем путь к .env рядом с этим файлом. Обычный load_dotenv()
# без аргументов ищет .env через интроспекцию стека вызова — под WSGI
# (mod_wsgi/uwsgi на PythonAnywhere) это иногда не находит нужную папку,
# .env тихо не подхватывается, TELEGRAM_TOKEN остаётся плейсхолдером,
# и путь вебхука перестаёт совпадать с тем, что знает Telegram (404).
load_dotenv(Path(__file__).resolve().parent / ".env")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "PASTE_YOUR_TOKEN_HERE")
if TELEGRAM_TOKEN == "PASTE_YOUR_TOKEN_HERE":
    # Печать попадёт в Error log на PythonAnywhere — сразу видно причину,
    # если вебхук вдруг начнёт получать 404 вместо ответа бота.
    print("ВНИМАНИЕ: TELEGRAM_TOKEN не найден. Проверь файл .env рядом с bot.py.")
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

ROUND_LEN = 10

# Одна HTTP-сессия на процесс. Голый requests.post открывает новое
# соединение на каждый вызов и заново жмёт руки по TLS, а на один вопрос
# уходит три запроса подряд. Сессия держит соединение открытым.
SESSION = audio.SESSION

# Порог, после которого шаг считается медленным и попадает в журнал.
# Бот отвечает на один тап тремя запросами к Telegram подряд, и если
# один из них тормозит, со стороны это выглядит как «подвисает» — но по
# логам без замера не понять, какой именно. Смотреть:
#   journalctl -u hebrew-quiz-bot | grep медленно
SLOW_STEP_SECONDS = float(os.environ.get("BOT_SLOW_STEP", "1.0"))


def timed(step):
    """Замеряет шаг и пишет в журнал, если он вышел долгим."""
    class _T:
        def __enter__(self):
            self.t = time.monotonic()
            return self

        def __exit__(self, *exc):
            spent = time.monotonic() - self.t
            if spent >= SLOW_STEP_SECONDS:
                print(f"[медленно] {step}: {spent:.2f} с")
            return False
    return _T()

app = Flask(__name__)

# Прогресс (ответы, статистика, расписание повторений) лежит в SQLite и
# переживает перезапуск. В памяти остаётся только состояние текущего
# раунда — его потерять не страшно.
try:
    db.init_db()
except Exception as e:
    print(f"ВНИМАНИЕ: не удалось открыть базу прогресса: {e}")

# Состояние текущего раунда по каждому чату. Живёт в памяти процесса,
# поэтому gunicorn запускается с одним воркером и несколькими потоками
# (см. deploy/install_service.sh).
sessions = {}

# Защита от повторной обработки одного и того же апдейта: пока bot.py
# делает синхронные запросы к Telegram API (sendMessage), обработка
# вебхука может занять больше времени, чем ждёт Telegram, и он повторно
# пришлёт тот же update_id. Без дедупликации это приводило к тому, что
# один тап по кнопке засчитывался дважды — второй раз уже против
# следующего вопроса (баг: "Верно", а следом сразу "Неверно" с ответом
# от другого слова).
SEEN_UPDATE_IDS = set()
MAX_SEEN_UPDATE_IDS = 2000


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


# ---------- Telegram API helpers ----------

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        with timed("sendMessage"):
            SESSION.post(f"{API_URL}/sendMessage", json=payload, timeout=10)
    except requests.exceptions.RequestException as e:
        # Сбой сети/прокси не должен ронять весь webhook в 500 — иначе
        # Telegram решит, что апдейт не доставлен, и будет слать его
        # повторно, копя pending_update_count. Логируем и едем дальше.
        print(f"[send_message] сетевая ошибка: {e}")


def set_reaction(chat_id, message_id, emoji):
    """Ставит эмодзи-реакцию на сообщение ученика.

    Так реагирует живой человек в чате, и это единственный способ
    ответить, не добавляя ещё одно сообщение в ленту. Работает не во
    всех чатах и не со всеми эмодзи, поэтому неудача — не ошибка:
    молча едем дальше, урок от этого не зависит.
    """
    if not message_id or not emoji:
        return
    try:
        SESSION.post(
            f"{API_URL}/setMessageReaction",
            json={"chat_id": chat_id, "message_id": message_id,
                  "reaction": [{"type": "emoji", "emoji": emoji}]},
            timeout=10,
        )
    except requests.exceptions.RequestException as e:
        print(f"[set_reaction] {e}")


def answer_callback(callback_id, text=None):
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    try:
        SESSION.post(f"{API_URL}/answerCallbackQuery", json=payload, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"[answer_callback] сетевая ошибка: {e}")


def main_menu_keyboard():
    return {
        "inline_keyboard": [
            # По две кнопки в ряд, иначе меню растягивается на весь экран
            [{"text": "📖 Слова", "callback_data": "start_vocab"},
             {"text": "🔤 Инфинитивы", "callback_data": "start_verbs"}],
            [{"text": "⏪ Прошедшее", "callback_data": "start_past"},
             {"text": "▶️ Настоящее", "callback_data": "start_present"}],
            [{"text": "⏩ Будущее", "callback_data": "start_future"}],
            [{"text": "⌨️ Написать самому", "callback_data": "typing_menu"},
             {"text": "🔡 Анаграмма", "callback_data": "start_anagram"}],
            [{"text": "🔤 Алфавит (с нуля)", "callback_data": "alphabet_menu"}],
            [{"text": "🗓 Слово дня", "callback_data": "word_of_day"},
             {"text": "📊 Статистика", "callback_data": "show_stats"}],
        ]
    }


def alphabet_menu_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "📜 Показать весь алфавит", "callback_data": "alef_table"}],
            [{"text": "Названия букв", "callback_data": "start_alef_names"},
             {"text": "Звуки букв", "callback_data": "start_alef_sounds"}],
            [{"text": "Узнать по названию", "callback_data": "start_alef_by_name"},
             {"text": "Конечные формы", "callback_data": "start_alef_finals"}],
            [{"text": "Огласовки", "callback_data": "start_alef_niqqud"},
             {"text": "Чтение слогов", "callback_data": "start_alef_syllables"}],
            [{"text": "Точка меняет звук (בּ / ב)", "callback_data": "start_alef_dotted"}],
            [{"text": "‹ Назад", "callback_data": "main_menu"}],
        ]
    }


def send_alphabet_table(chat_id):
    """Справочник: все буквы с названием и звуком, потом огласовки."""
    lines = ["📜 <b>Алфавит</b> (читается справа налево)", ""]
    for letter, name, sound, final in alphabet.LETTERS:
        final_note = f"  (в конце слова: {final})" if final else ""
        lines.append(f"<b>{letter}</b> — {name}, {sound}{final_note}")

    lines += ["", "<b>Точка внутри буквы меняет звук</b>", ""]
    for shown, name, sound in alphabet.DOTTED:
        lines.append(f"<b>{shown}</b> — {name}, звук «{sound}»")

    lines += ["", "<b>Огласовки</b> (показаны на букве ב)", ""]
    for shown, _, sound in alphabet.NIQQUD:
        lines.append(f"<b>{shown}</b> — звук «{sound}»")

    lines += [
        "",
        "<i>Пять букв в конце слова пишутся иначе: כ→ך, מ→ם, נ→ן, פ→ף, צ→ץ.</i>",
    ]
    send_message(chat_id, "\n".join(lines), alphabet_menu_keyboard())


def typing_menu_keyboard():
    """Тот же набор тем, но с ответом от руки вместо выбора из четырёх."""
    return {
        "inline_keyboard": [
            [{"text": "📖 Слова", "callback_data": "type_vocab"}],
            [{"text": "🔤 Глаголы (инфинитивы)", "callback_data": "type_verbs"}],
            [{"text": "⏪ Прошедшее время", "callback_data": "type_past"}],
            [{"text": "▶️ Настоящее время", "callback_data": "type_present"}],
            [{"text": "⏩ Будущее время", "callback_data": "type_future"}],
            [{"text": "‹ Назад", "callback_data": "main_menu"}],
        ]
    }


# ---------- Игровая логика ----------

def keyboard_rows(buttons, per_row=2):
    """Разбивает кнопки на ряды по per_row штук — сетка 2x2 вместо одного
    узкого столбца, площадь тапа на кнопку больше."""
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


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


def send_question(chat_id):
    s = sessions[chat_id]
    q = build_question(s["pool"], s["used"], s.get("priorities"))
    s["used"].add(q["ru"])
    s["current"] = q

    # Нативная (reply) клавиатура вместо inline — кнопки растягиваются на
    # всю ширину экрана и рендерятся крупнее, чем инлайн-кнопки в пузыре
    # сообщения. Сетка 2x2 вместо одного столбца — площадь тапа больше.
    # resize_keyboard НЕ ставим (по умолчанию false) — по документации
    # Telegram именно этот флаг "сжимает" клавиатуру; без него кнопки
    # занимают высоту стандартной системной клавиатуры, то есть выше.
    # one_time_keyboard прячет клавиатуру сразу после тапа.
    idx = s["index"] + 1
    is_form = s["mode"] in ("past", "present", "future")

    if s.get("anagram"):
        # Буквы вразброс — задача собрать из них слово.
        s["hints"] = 0
        letters = " ".join(scramble(q["correct"], random))
        text = (
            f"Вопрос {idx}/{s['total']}\n<b>{q['ru']}</b>\n"
            f"Буквы: <code>{letters}</code>\n\n"
            f"<i>Собери из них слово. «?» — подсказка, /skip — пропустить.</i>"
        )
        send_message(chat_id, text, {"remove_keyboard": True})
        return

    if s.get("typing"):
        # Вариантов не показываем — ответ нужно вспомнить и написать.
        # Клавиатуру с прошлого раунда убираем, чтобы не мешала набору.
        s["hints"] = 0
        task = "Напиши эту форму на иврите" if is_form else "Напиши это слово на иврите"
        text = (
            f"Вопрос {idx}/{s['total']}\n<b>{q['ru']}</b>\n{task}.\n\n"
            f"<i>Огласовки писать не нужно. «?» — подсказка, /skip — пропустить.</i>"
        )
        send_message(chat_id, text, {"remove_keyboard": True})
        return

    # Нативная (reply) клавиатура вместо inline — кнопки растягиваются на
    # всю ширину экрана и рендерятся крупнее, чем инлайн-кнопки в пузыре
    # сообщения. Сетка 2x2 вместо одного столбца — площадь тапа больше.
    # resize_keyboard НЕ ставим (по умолчанию false) — по документации
    # Telegram именно этот флаг "сжимает" клавиатуру; без него кнопки
    # занимают высоту стандартной системной клавиатуры, то есть выше.
    # one_time_keyboard прячет клавиатуру сразу после тапа.
    keyboard = {
        "keyboard": keyboard_rows(q["options"], per_row=2),
        "one_time_keyboard": True,
    }
    if s["mode"] in ALPHABET_MODES:
        # Подсказка уже сформулирована как вопрос («буква א», «прочитай מָ»)
        text = f"Вопрос {idx}/{s['total']}\n<b>{q['ru']}</b>?"
    elif is_form:
        text = f"Вопрос {idx}/{s['total']}\n<b>{q['ru']}</b>\nКакая это форма?"
    else:
        text = f"Вопрос {idx}/{s['total']}\nКак будет «<b>{q['ru']}</b>»?"
    send_message(chat_id, text, keyboard)


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

# Режимы курса алфавита: вопрос формулируется иначе, чем «как будет…»
ALPHABET_MODES = {m for m in LABELS if m.startswith("alef_")}

# Все допустимые написания каждого пула. Нужны, чтобы отличить описку от
# случая «набрал другое существующее слово» (см. matching.check_answer).
KNOWN_FORMS = {
    mode: set().union(*(accepted_forms(he) for _, he, _ in pool)) if pool else set()
    for mode, pool in POOLS.items()
}


def start_round(chat_id, mode, typing=False, anagram=False):
    pool = POOLS[mode]
    total = min(ROUND_LEN, len(pool))
    # Приоритеты читаем один раз на раунд, а не на каждый вопрос —
    # лишние обращения к БД внутри раунда не нужны.
    try:
        db.touch_user(chat_id)
        priorities = db.card_priorities(chat_id, mode)
    except Exception as e:
        print(f"[start_round] БД недоступна, играем без повторений: {e}")
        priorities = {}

    sessions[chat_id] = {
        "mode": mode,
        "pool": pool,
        "used": set(),
        "index": 0,
        "score": 0,
        "total": total,
        "current": None,
        "priorities": priorities,
        "typing": typing or anagram,   # ответ в обоих случаях набирается руками
        "anagram": anagram,
        "hints": 0,
        "streak": 0,          # верных подряд прямо сейчас
        "best_streak": 0,     # лучшая серия за раунд
        "recent": [],         # недавние реплики, чтобы не повторяться
        "last_memory": -9,    # на каком вопросе бот последний раз вспоминал
        "reacted_msg": None,  # на какое сообщение уже повесили реакцию
    }
    due = sum(1 for v in priorities.values() if v >= 2)
    hint = f" Из них на повторение: {min(due, total)}." if due else ""
    if anagram:
        how = " Собираешь слово из букв."
    elif typing:
        how = " Пишешь ответ сам."
    else:
        how = ""
    send_message(
        chat_id,
        f"Начинаем! Раунд «{LABELS[mode]}», {total} вопросов.{hint}{how}",
    )
    send_question(chat_id)


# Как склеивается реплика с самим ответом. У «верно» ответ идёт через
# тире («✅ Точно — מִטְבָּח»), у остальных реплика уже кончается
# двоеточием («❌ Мимо. Правильно: מִטְבָּח»).
VERDICT_POOLS = {
    "correct": (reactions.CORRECT, " — "),
    "typo": (reactions.TYPO, " "),
    "wrong": (reactions.WRONG, " "),
    "skip": (reactions.SKIPPED, " "),
}

# Как часто бот может вспоминать историю слова. Без паузы он делал бы
# это почти каждый вопрос — а замечание, которое звучит всегда, перестаёт
# быть замечанием.
MEMORY_COOLDOWN = 3


def lively(chat_id):
    """Включены ли живые реплики. Сбой БД не должен глушить бота."""
    try:
        return db.reactions_enabled(chat_id)
    except Exception:
        return True


def say_verdict(chat_id, s, outcome, answer, message_id=None, before=None,
                extra=None):
    """Ответ на попытку: реплика, память о слове, отметка серии.

    Собрано в одном месте, потому что выбор с кнопок, набор руками и
    анаграмма отвечают по-разному, а звучать должны одинаково.
    """
    pool, sep = VERDICT_POOLS[outcome]
    alive = lively(chat_id)
    # С выключенными реакциями поведение прежнее: одна и та же формулировка.
    phrase = reactions.pick(pool, s["recent"], random) if alive else pool[0]

    lines = [f"{phrase}{sep}{with_reading(answer, s['mode'])}"]
    if extra:
        lines.append(extra)

    # Серия. Описку засчитываем как верный ответ: слово вспомнил,
    # промахнулся по буквам — серию за это обрывать несправедливо.
    scored = outcome in ("correct", "typo")
    s["streak"] = s["streak"] + 1 if scored else 0
    s["best_streak"] = max(s["best_streak"], s["streak"])

    emoji = None
    if alive:
        memory = reactions.memory_line(before, scored)
        if memory and s["index"] - s["last_memory"] >= MEMORY_COOLDOWN:
            lines.append(f"<i>{memory}</i>")
            s["last_memory"] = s["index"]

        event = reactions.streak_event(s["streak"]) if scored else None
        if event:
            line, emoji = event
            lines.append(line)

    send_message(chat_id, "\n".join(lines))
    if emoji:
        set_reaction(chat_id, message_id, emoji)
        # Telegram хранит одну реакцию бота на сообщение: вторая молча
        # затирает первую. Десятая подряд и идеальный раунд приходят на
        # один и тот же тап, поэтому запоминаем, что уже отметили.
        s["reacted_msg"] = message_id


def card_history(chat_id, card_id):
    """История карточки до текущего ответа (для «я это помню»)."""
    try:
        return db.card_history(chat_id, card_id)
    except Exception as e:
        print(f"[card_history] {e}")
        return None


def handle_answer(chat_id, question_idx, chosen_idx, message_id=None):
    s = sessions.get(chat_id)
    if not s or not s["current"]:
        return
    if question_idx != s["index"]:
        # Ответ пришёл на уже неактуальный вопрос (повтор апдейта от
        # Telegram или гонка двух тапов) — просто игнорируем.
        return
    q = s["current"]
    chosen = q["options"][chosen_idx]
    is_correct = chosen == q["correct"]

    # Историю читаем ДО записи ответа: record_answer обновит счётчики, и
    # «сколько раз ты на этом спотыкался» уже включит текущий раз.
    before = card_history(chat_id, q["ru"])

    # Записываем ответ в БД: отсюда берутся и статистика, и расписание
    # повторений. Сбой БД не должен ломать игру, поэтому не роняем раунд.
    try:
        db.record_answer(chat_id, s["mode"], q["ru"], is_correct)
    except Exception as e:
        print(f"[handle_answer] не удалось записать ответ: {e}")

    if is_correct:
        s["score"] += 1
    say_verdict(chat_id, s, "correct" if is_correct else "wrong",
                q["correct"], message_id, before)
    maybe_send_voice(chat_id, q["correct"], s["mode"])

    finish_question(chat_id)


def maybe_send_voice(chat_id, answer, mode):
    """Присылает произношение голосом, если оно записано и не отключено.

    Отсутствие файла — не ошибка: озвучка добавляется постепенно, и урок
    не должен от неё зависеть.
    """
    if mode in ALPHABET_MODES:
        return
    if not audio.has_audio(answer):
        return
    try:
        if not db.voice_enabled(chat_id):
            return
        slow = db.slow_voice(chat_id)
        if slow and not audio.has_audio(answer, slow=True):
            slow = False

        # Первая отправка грузит файл, все следующие идут по file_id —
        # мгновенно. Без этого каждое голосовое заливалось заново, и
        # перед ним была заметная пауза.
        path = audio.audio_path(answer, slow=slow)
        key = audio.file_key(path)
        file_id = db.voice_file_id(key)
        with timed("загрузка голосового" if not file_id else "отправка по file_id"):
            got = audio.send_voice(API_URL, chat_id, answer, slow=slow,
                                   file_id=file_id)
        if got and got != file_id:
            db.save_voice_file_id(key, got)
    except Exception as e:
        print(f"[maybe_send_voice] {e}")


SPEED_LABELS = {"normal": "обычная скорость", "slow": "помедленнее"}


def ask_sample_speed(chat_id):
    """Спрашивает скорость: образцов много, слать все сразу — каша."""
    if not audio.voice_samples():
        send_message(
            chat_id,
            "Образцы голосов ещё не сгенерированы.\n\n"
            "На сервере: <code>venv/bin/python3 tools/voice_samples.py</code>",
        )
        return

    speeds = audio.sample_speeds()
    if not speeds:
        # старые образцы без пометки скорости — просто отправляем всё
        send_voice_samples(chat_id)
        return

    send_message(
        chat_id,
        "🎧 <b>Сравнение озвучки</b>\n\n"
        f"{audio.SAMPLE_TEXT}\n\n"
        f"<i>{audio.SAMPLE_TRANSLATION}</i>\n\n"
        "На какой скорости прислать образцы?",
        {"inline_keyboard": [[
            {"text": f"🚶 {SPEED_LABELS[s]}" if s == "normal" else f"🐢 {SPEED_LABELS[s]}",
             "callback_data": f"voices_{s}"}
            for s in speeds
        ]]},
    )


def send_voice_samples(chat_id, speed=None):
    """Один и тот же текст в разных вариантах озвучки."""
    samples = audio.voice_samples(speed=speed)
    if not samples:
        send_message(
            chat_id,
            "Образцы голосов ещё не сгенерированы.\n\n"
            "На сервере: <code>venv/bin/python3 tools/voice_samples.py</code>",
        )
        return

    if speed:
        send_message(
            chat_id,
            f"Вариант: <b>{SPEED_LABELS.get(speed, speed)}</b>. "
            "Выбранный голос вписывается в .env как <code>TTS_VOICE</code>.",
        )
    for name, path in samples:
        audio.send_voice_file(API_URL, chat_id, path, caption=name)




def with_reading(answer, mode):
    """Добавляет произношение кириллицей: «מִטְבָּח (митбах)».

    В курсе алфавита не показываем — там ответ и так уже либо звук, либо
    название буквы, произношение было бы шумом.
    """
    if mode in ALPHABET_MODES:
        return answer
    reading = translit(answer)
    return f"{answer} ({reading})" if reading else answer


def finish_question(chat_id):
    """Переходит к следующему вопросу или закрывает раунд."""
    s = sessions[chat_id]
    s["index"] += 1
    if s["index"] >= s["total"]:
        pct = round(100 * s["score"] / s["total"])
        if lively(chat_id):
            head, emoji = reactions.round_summary(
                s["score"], s["total"], s["best_streak"])
        else:
            head, emoji = f"Итог раунда: {s['score']}/{s['total']} ({pct}%)", None
        send_message(
            chat_id,
            f"{head}\n\nЖми /start, чтобы начать новый раунд.",
            main_menu_keyboard(),
        )
        if emoji and s.get("last_msg") != s.get("reacted_msg"):
            set_reaction(chat_id, s.get("last_msg"), emoji)
        s["current"] = None
    else:
        send_question(chat_id)


def handle_typed_answer(chat_id, typed, message_id=None):
    """Ответ, набранный вручную (режим «Написать самому»)."""
    s = sessions.get(chat_id)
    if not s or not s["current"]:
        return
    q = s["current"]

    # «?» — подсказка: показываем первые буквы, вопрос остаётся открытым
    if typed.strip() == "?":
        s["hints"] = s.get("hints", 0) + 1
        send_message(chat_id, f"Подсказка: <code>{hint_for(q['correct'], s['hints'])}</code>")
        return

    if typed.strip().lower() in ("/skip", "пропустить"):
        before = card_history(chat_id, q["ru"])
        try:
            db.record_answer(chat_id, s["mode"], q["ru"], False)
        except Exception as e:
            print(f"[handle_typed_answer] не удалось записать пропуск: {e}")
        say_verdict(chat_id, s, "skip", q["correct"], message_id, before)
        finish_question(chat_id)
        return

    verdict = check_answer(typed, q["correct"], KNOWN_FORMS.get(s["mode"]))
    # Подсказками пользовался — засчитываем, но в повторениях как неуверенный
    is_correct = verdict in ("exact", "typo") and not s.get("hints")

    before = card_history(chat_id, q["ru"])
    try:
        db.record_answer(chat_id, s["mode"], q["ru"], is_correct)
    except Exception as e:
        print(f"[handle_typed_answer] не удалось записать ответ: {e}")

    outcome = {"exact": "correct", "typo": "typo"}.get(verdict, "wrong")
    if verdict in ("exact", "typo"):
        s["score"] += 1
    # Подсказка — это не провал, но и не чистое попадание: честнее сказать
    # вслух, что слово вернётся, чем молча подсунуть его снова.
    extra = ("<i>(с подсказкой — повторим ещё раз)</i>"
             if verdict == "exact" and s.get("hints") else None)
    say_verdict(chat_id, s, outcome, q["correct"], message_id, before, extra)
    maybe_send_voice(chat_id, q["correct"], s["mode"])

    finish_question(chat_id)


# ---------- Слово дня ----------

def pick_daily_word(chat_id):
    """Слово, которого пользователь ещё не видел (иначе — любое)."""
    try:
        seen = db.seen_cards(chat_id, "vocab")
    except Exception:
        seen = set()
    fresh = [w for w in VOCAB_FLAT if w[0] not in seen]
    return random.choice(fresh or VOCAB_FLAT)


def send_word_of_day(chat_id, subscribe_hint=True):
    """Слово дня: перевод, написание и кнопка потренироваться."""
    ru, he, _ = pick_daily_word(chat_id)

    try:
        subscribed = db.is_subscribed(chat_id)
    except Exception:
        subscribed = False

    lines = [
        "🗓 <b>Слово дня</b>",
        "",
        f"<b>{he}</b> — {ru}",
        f"<i>читается: {translit(he)}</i>",
    ]
    if subscribe_hint:
        lines += [
            "",
            "<i>Присылать такое каждое утро — /daily_on, отключить — /daily_off.</i>"
            if not subscribed
            else "<i>Отключить ежедневную отправку — /daily_off.</i>",
        ]

    keyboard = {
        "inline_keyboard": [
            [{"text": "📖 Потренировать слова", "callback_data": "start_vocab"}],
            [{"text": "‹ Меню", "callback_data": "main_menu"}],
        ]
    }
    send_message(chat_id, "\n".join(lines), keyboard)
    maybe_send_voice(chat_id, he, "vocab")


# ---------- Статистика ----------

def send_stats(chat_id):
    """Сводка прогресса: точность, streak, что пора повторить, слабые места."""
    try:
        overall = db.overall_stats(chat_id)
        by_mode = db.stats_by_mode(chat_id)
        weak = db.weak_cards(chat_id, limit=5)
        streak = db.streak_days(chat_id)
        due = db.due_count(chat_id)
    except Exception as e:
        print(f"[send_stats] БД недоступна: {e}")
        send_message(chat_id, "Статистика пока недоступна, попробуй позже.")
        return

    if not overall["total"]:
        send_message(chat_id, "Ты ещё не отвечал ни на один вопрос. Жми /start!")
        return

    pct = round(100 * overall["correct"] / overall["total"])
    lines = [
        "📊 <b>Твоя статистика</b>",
        "",
        f"Всего ответов: {overall['total']}",
        f"Правильных: {overall['correct']} ({pct}%)",
    ]
    if streak:
        lines.append(f"Занимаешься подряд: {streak} дн.")
    if due:
        lines.append(f"Ждут повторения: {due}")

    if by_mode:
        lines += ["", "<b>По режимам:</b>"]
        for mode, label in LABELS.items():
            st = by_mode.get(mode)
            if not st:
                continue
            p = round(100 * st["correct"] / st["total"])
            lines.append(f"• {label}: {st['correct']}/{st['total']} ({p}%)")

    if weak:
        lines += ["", "<b>Чаще всего ошибаешься:</b>"]
        for w in weak:
            lines.append(f"• {w['card_id']} — ошибок {w['n_wrong']}")
        lines.append("")
        lines.append("<i>Эти карточки бот будет показывать чаще.</i>")

    send_message(chat_id, "\n".join(lines), main_menu_keyboard())


# ---------- Webhook ----------

@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    # Любая неожиданная ошибка внутри обработки всё равно должна вернуть
    # Telegram-у 200 — иначе он решит, что апдейт не доставлен, и будет
    # слать его снова и снова (что как раз копило pending_update_count).
    try:
        _handle_webhook_update()
    except Exception as e:
        print(f"[webhook] необработанная ошибка: {e}")
    return jsonify(ok=True)


def _handle_webhook_update():
    update = request.get_json(force=True, silent=True) or {}

    update_id = update.get("update_id")
    if update_id is not None:
        if update_id in SEEN_UPDATE_IDS:
            return  # Telegram уже присылал этот апдейт — игнорируем
        SEEN_UPDATE_IDS.add(update_id)
        if len(SEEN_UPDATE_IDS) > MAX_SEEN_UPDATE_IDS:
            SEEN_UPDATE_IDS.clear()

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        message_id = msg.get("message_id")

        s = sessions.get(chat_id)
        if s is not None:
            # На это сообщение вешается реакция за серию, а в конце
            # раунда — за итог.
            s["last_msg"] = message_id
        in_typing_round = bool(s and s.get("current") and s.get("typing"))

        if text.startswith("/start") or text.startswith("/quiz"):
            send_message(chat_id, "Привет! Что тренируем сегодня?", main_menu_keyboard())
        elif text.startswith("/stats"):
            send_stats(chat_id)
        elif text.startswith("/word"):
            send_word_of_day(chat_id)
        elif text.startswith("/daily_on"):
            db.set_daily_word(chat_id, True)
            send_message(chat_id, "Готово, буду присылать слово дня каждое утро.")
        elif text.startswith("/daily_off"):
            db.set_daily_word(chat_id, False)
            send_message(chat_id, "Больше не присылаю слово дня. Вернуть — /daily_on.")
        elif text.startswith("/voices"):
            ask_sample_speed(chat_id)
        elif text.startswith("/voice_on"):
            db.set_voice(chat_id, True)
            send_message(chat_id, "Буду присылать произношение голосом.")
        elif text.startswith("/voice_off"):
            db.set_voice(chat_id, False)
            send_message(chat_id, "Голосовые отключены. Вернуть — /voice_on.")
        elif text.startswith("/reactions_on"):
            db.set_reactions(chat_id, True)
            send_message(chat_id, "Живые реплики и отметки серий включены.")
        elif text.startswith("/reactions_off"):
            db.set_reactions(chat_id, False)
            send_message(
                chat_id,
                "Оставляю только сухие «верно / неверно». Вернуть — /reactions_on.",
            )
        elif text.startswith("/speed"):
            slow = not db.slow_voice(chat_id)
            db.set_slow_voice(chat_id, slow)
            send_message(
                chat_id,
                "🐢 Озвучка помедленнее — легче разобрать по звукам."
                if slow else
                "🚶 Обычная скорость озвучки.",
            )
        elif in_typing_round:
            # В режиме набора принимаем любой текст: это и есть ответ
            # (плюс «?» для подсказки и /skip для пропуска).
            handle_typed_answer(chat_id, text, message_id)
        elif s and s.get("current"):
            # Ответ с выбором приходит как обычное сообщение с нативной
            # (reply) клавиатуры, а не callback_query.
            options = s["current"]["options"]
            if text in options:
                handle_answer(chat_id, s["index"], options.index(text), message_id)

    elif "callback_query" in update:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        data = cq.get("data", "")
        answer_callback(cq["id"])

        if data == "start_vocab":
            start_round(chat_id, "vocab")
        elif data == "start_verbs":
            start_round(chat_id, "verbs")
        elif data == "start_past":
            start_round(chat_id, "past")
        elif data == "start_present":
            start_round(chat_id, "present")
        elif data == "start_future":
            start_round(chat_id, "future")
        elif data == "typing_menu":
            send_message(
                chat_id,
                "Что тренируем? Ответ нужно будет написать самому.",
                typing_menu_keyboard(),
            )
        elif data == "main_menu":
            send_message(chat_id, "Что тренируем сегодня?", main_menu_keyboard())
        elif data.startswith("type_"):
            start_round(chat_id, data[len("type_"):], typing=True)
        elif data == "start_anagram":
            # Анаграмма только по словам: собирать из букв длинную
            # глагольную форму мучительно и мало чему учит.
            start_round(chat_id, "vocab", anagram=True)
        elif data == "word_of_day":
            send_word_of_day(chat_id)
        elif data == "alphabet_menu":
            send_message(
                chat_id,
                "Курс алфавита. Начни с таблицы, если видишь буквы впервые.",
                alphabet_menu_keyboard(),
            )
        elif data == "alef_table":
            send_alphabet_table(chat_id)
        elif data.startswith("start_alef_"):
            start_round(chat_id, data[len("start_"):])
        elif data.startswith("voices_"):
            send_voice_samples(chat_id, speed=data[len("voices_"):])
        elif data == "show_stats":
            send_stats(chat_id)


@app.route("/")
def health():
    return "Hebrew quiz bot is running."


if __name__ == "__main__":
    app.run(debug=True)
