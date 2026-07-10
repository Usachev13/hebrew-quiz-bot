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

from words import VOCAB, VERBS
from conjugations import CONJUGATIONS, PAST_PERSONS, PAST_LABELS, PRESENT_SLOTS, PRESENT_LABELS

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
LETTERS = ["А", "Б", "В", "Г"]

app = Flask(__name__)

# Состояние по каждому чату храним прямо в памяти процесса.
# Для одного пользователя (личный бот) этого достаточно.
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


def flatten_conjugations(conj):
    """Превращает CONJUGATIONS в плоский список (подсказка, форма, группа).
    Группа = глагол+время, чтобы дистракторы брались из форм ТОГО ЖЕ
    глагола в том же времени (тренируем именно лицо/род/число)."""
    items = []
    for root, data in conj.items():
        verb_ru = data["ru"]
        for person in PAST_PERSONS:
            he = data["past"][person]
            prompt = f"{verb_ru} — прошедшее время, {PAST_LABELS[person]}"
            items.append((prompt, he, f"{root}_past"))
        for slot in PRESENT_SLOTS:
            he = data["present"][slot]
            prompt = f"{verb_ru} — настоящее время, {PRESENT_LABELS[slot]}"
            items.append((prompt, he, f"{root}_present"))
    return items


VOCAB_FLAT = flatten(VOCAB)
VERBS_FLAT = flatten(VERBS)
CONJ_FLAT = flatten_conjugations(CONJUGATIONS)


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
            [{"text": "📖 Слова", "callback_data": "start_vocab"}],
            [{"text": "🔤 Глаголы (инфинитивы)", "callback_data": "start_verbs"}],
            [{"text": "🧩 Спряжения (прош./наст.)", "callback_data": "start_conj"}],
        ]
    }


# ---------- Игровая логика ----------

def option_buttons(options):
    """Подписи кнопок-вариантов ответа — переиспользуется и при построении
    клавиатуры, и при разборе входящего текстового ответа пользователя."""
    return [f"{LETTERS[i]}) {opt}" for i, opt in enumerate(options)]


def keyboard_rows(buttons, per_row=2):
    """Разбивает кнопки на ряды по per_row штук — сетка 2x2 вместо одного
    узкого столбца, площадь тапа на кнопку больше."""
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def build_question(pool, used):
    """Выбирает случайное слово (ещё не заданное в этом раунде) и 3 дистрактора
    из той же категории/группы биньяна — так угадать наугад сложнее."""
    remaining = [w for w in pool if w[0] not in used]
    if not remaining:
        remaining = pool
    correct = random.choice(remaining)
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
    q = build_question(s["pool"], s["used"])
    s["used"].add(q["ru"])
    s["current"] = q

    # Нативная (reply) клавиатура вместо inline — кнопки растягиваются на
    # всю ширину экрана и рендерятся крупнее, чем инлайн-кнопки в пузыре
    # сообщения. Сетка 2x2 вместо одного столбца — площадь тапа больше.
    # resize_keyboard НЕ ставим (по умолчанию false) — по документации
    # Telegram именно этот флаг "сжимает" клавиатуру; без него кнопки
    # занимают высоту стандартной системной клавиатуры, то есть выше.
    # one_time_keyboard прячет клавиатуру сразу после тапа.
    keyboard = {
        "keyboard": keyboard_rows(option_buttons(q["options"]), per_row=2),
        "one_time_keyboard": True,
    }
    idx = s["index"] + 1
    if s["mode"] == "conj":
        text = f"Вопрос {idx}/{s['total']}\n<b>{q['ru']}</b>\nКакая это форма?"
    else:
        text = f"Вопрос {idx}/{s['total']}\nКак будет «<b>{q['ru']}</b>»?"
    send_message(chat_id, text, keyboard)


POOLS = {"vocab": VOCAB_FLAT, "verbs": VERBS_FLAT, "conj": CONJ_FLAT}
LABELS = {"vocab": "слова", "verbs": "глаголы", "conj": "спряжения"}


def start_round(chat_id, mode):
    pool = POOLS[mode]
    total = min(ROUND_LEN, len(pool))
    sessions[chat_id] = {
        "mode": mode,
        "pool": pool,
        "used": set(),
        "index": 0,
        "score": 0,
        "total": total,
        "current": None,
    }
    send_message(chat_id, f"Начинаем! Раунд «{LABELS[mode]}», {total} вопросов.")
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

    if is_correct:
        s["score"] += 1
        text = f"✅ Верно — {q['correct']}"
    else:
        text = f"❌ Неверно. Правильный ответ: {q['correct']}"
    send_message(chat_id, text)

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

        if text.startswith("/start") or text.startswith("/quiz"):
            send_message(chat_id, "Привет! Что тренируем сегодня?", main_menu_keyboard())
        else:
            # Ответ на вопрос теперь приходит как обычное сообщение с
            # нативной (reply) клавиатуры, а не callback_query.
            s = sessions.get(chat_id)
            if s and s.get("current"):
                buttons = option_buttons(s["current"]["options"])
                if text in buttons:
                    handle_answer(chat_id, s["index"], buttons.index(text))

    elif "callback_query" in update:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        data = cq.get("data", "")
        answer_callback(cq["id"])

        if data == "start_vocab":
            start_round(chat_id, "vocab")
        elif data == "start_verbs":
            start_round(chat_id, "verbs")
        elif data == "start_conj":
            start_round(chat_id, "conj")


@app.route("/")
def health():
    return "Hebrew quiz bot is running."


if __name__ == "__main__":
    app.run(debug=True)
