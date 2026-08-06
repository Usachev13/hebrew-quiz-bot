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
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify

import db
from matching import check_answer, accepted_forms, hint_for, scramble
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
        requests.post(f"{API_URL}/sendMessage", json=payload, timeout=10)
    except requests.exceptions.RequestException as e:
        # Сбой сети/прокси не должен ронять весь webhook в 500 — иначе
        # Telegram решит, что апдейт не доставлен, и будет слать его
        # повторно, копя pending_update_count. Логируем и едем дальше.
        print(f"[send_message] сетевая ошибка: {e}")


def answer_callback(callback_id, text=None):
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    try:
        requests.post(f"{API_URL}/answerCallbackQuery", json=payload, timeout=10)
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
            [{"text": "🗓 Слово дня", "callback_data": "word_of_day"},
             {"text": "📊 Статистика", "callback_data": "show_stats"}],
        ]
    }


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

    same_cat = [w for w in pool if w[2] == cat and w[1] != he]
    distractors = random.sample(same_cat, min(3, len(same_cat)))
    pool_others = [w for w in pool if w[1] != he and w not in distractors]
    while len(distractors) < 3 and pool_others:
        extra = random.choice(pool_others)
        distractors.append(extra)
        pool_others.remove(extra)

    options = [he] + [d[1] for d in distractors]
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
    if is_form:
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
}
LABELS = {
    "vocab": "слова",
    "verbs": "глаголы",
    "past": "прошедшее время",
    "present": "настоящее время",
    "future": "будущее время",
}

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


def handle_answer(chat_id, question_idx, chosen_idx):
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

    # Записываем ответ в БД: отсюда берутся и статистика, и расписание
    # повторений. Сбой БД не должен ломать игру, поэтому не роняем раунд.
    try:
        db.record_answer(chat_id, s["mode"], q["ru"], is_correct)
    except Exception as e:
        print(f"[handle_answer] не удалось записать ответ: {e}")

    if is_correct:
        s["score"] += 1
        text = f"✅ Верно — {q['correct']}"
    else:
        text = f"❌ Неверно. Правильный ответ: {q['correct']}"
    send_message(chat_id, text)

    finish_question(chat_id)


def finish_question(chat_id):
    """Переходит к следующему вопросу или закрывает раунд."""
    s = sessions[chat_id]
    s["index"] += 1
    if s["index"] >= s["total"]:
        pct = round(100 * s["score"] / s["total"])
        send_message(
            chat_id,
            f"Итог раунда: {s['score']}/{s['total']} ({pct}%)\n\n"
            f"Жми /start, чтобы начать новый раунд.",
            main_menu_keyboard(),
        )
        s["current"] = None
    else:
        send_question(chat_id)


def handle_typed_answer(chat_id, typed):
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
        try:
            db.record_answer(chat_id, s["mode"], q["ru"], False)
        except Exception as e:
            print(f"[handle_typed_answer] не удалось записать пропуск: {e}")
        send_message(chat_id, f"Пропускаем. Правильный ответ: {q['correct']}")
        finish_question(chat_id)
        return

    verdict = check_answer(typed, q["correct"], KNOWN_FORMS.get(s["mode"]))
    # Подсказками пользовался — засчитываем, но в повторениях как неуверенный
    is_correct = verdict in ("exact", "typo") and not s.get("hints")

    try:
        db.record_answer(chat_id, s["mode"], q["ru"], is_correct)
    except Exception as e:
        print(f"[handle_typed_answer] не удалось записать ответ: {e}")

    if verdict == "exact":
        s["score"] += 1
        text = f"✅ Верно — {q['correct']}"
        if s.get("hints"):
            text += "\n<i>(с подсказкой — повторим ещё раз)</i>"
    elif verdict == "typo":
        s["score"] += 1
        text = f"⚠️ Почти! Правильно пишется так: {q['correct']}"
    else:
        text = f"❌ Неверно. Правильный ответ: {q['correct']}"
    send_message(chat_id, text)

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

        s = sessions.get(chat_id)
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
        elif in_typing_round:
            # В режиме набора принимаем любой текст: это и есть ответ
            # (плюс «?» для подсказки и /skip для пропуска).
            handle_typed_answer(chat_id, text)
        elif s and s.get("current"):
            # Ответ с выбором приходит как обычное сообщение с нативной
            # (reply) клавиатуры, а не callback_query.
            options = s["current"]["options"]
            if text in options:
                handle_answer(chat_id, s["index"], options.index(text))

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
        elif data == "show_stats":
            send_stats(chat_id)


@app.route("/")
def health():
    return "Hebrew quiz bot is running."


if __name__ == "__main__":
    app.run(debug=True)
