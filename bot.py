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

import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify

from words import VOCAB, VERBS

load_dotenv()  # локально читает .env; на хостинге просто ничего не найдёт и пропустит

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "PASTE_YOUR_TOKEN_HERE")
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

ROUND_LEN = 10
LETTERS = ["А", "Б", "В", "Г"]

app = Flask(__name__)

# Состояние по каждому чату храним прямо в памяти процесса.
# Для одного пользователя (личный бот) этого достаточно.
sessions = {}


def flatten(bank):
    """Превращает {категория: [(ru, he), ...]} в плоский список (ru, he, категория)."""
    items = []
    for category, words in bank.items():
        for ru, he in words:
            items.append((ru, he, category))
    return items


VOCAB_FLAT = flatten(VOCAB)
VERBS_FLAT = flatten(VERBS)


# ---------- Telegram API helpers ----------

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{API_URL}/sendMessage", json=payload, timeout=10)


def answer_callback(callback_id, text=None):
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    requests.post(f"{API_URL}/answerCallbackQuery", json=payload, timeout=10)


def main_menu_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "📖 Слова", "callback_data": "start_vocab"}],
            [{"text": "🔤 Глаголы (инфинитивы)", "callback_data": "start_verbs"}],
        ]
    }


# ---------- Игровая логика ----------

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

    keyboard = {
        "inline_keyboard": [
            [{"text": f"{LETTERS[i]}) {opt}", "callback_data": f"ans|{i}"}]
            for i, opt in enumerate(q["options"])
        ]
    }
    idx = s["index"] + 1
    text = f"Вопрос {idx}/{s['total']}\nКак будет «<b>{q['ru']}</b>»?"
    send_message(chat_id, text, keyboard)


def start_round(chat_id, mode):
    pool = VOCAB_FLAT if mode == "vocab" else VERBS_FLAT
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
    label = "слова" if mode == "vocab" else "глаголы"
    send_message(chat_id, f"Начинаем! Раунд «{label}», {total} вопросов.")
    send_question(chat_id)


def handle_answer(chat_id, chosen_idx):
    s = sessions.get(chat_id)
    if not s or not s["current"]:
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
    update = request.get_json(force=True, silent=True) or {}

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        if text.startswith("/start") or text.startswith("/quiz"):
            send_message(chat_id, "Привет! Что тренируем сегодня?", main_menu_keyboard())

    elif "callback_query" in update:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        data = cq.get("data", "")
        answer_callback(cq["id"])

        if data == "start_vocab":
            start_round(chat_id, "vocab")
        elif data == "start_verbs":
            start_round(chat_id, "verbs")
        elif data.startswith("ans|"):
            idx = int(data.split("|")[1])
            handle_answer(chat_id, idx)

    return jsonify(ok=True)


@app.route("/")
def health():
    return "Hebrew quiz bot is running."


if __name__ == "__main__":
    app.run(debug=True)
