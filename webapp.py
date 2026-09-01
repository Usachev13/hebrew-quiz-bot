# -*- coding: utf-8 -*-
"""
API и страница Mini App.

Разделение обязанностей: правила игры лежат в quiz.py, отправка в чат —
в bot.py, а здесь только HTTP. Так чат и приложение работают по одним
правилам, а не по двум расходящимся копиям.

Состояние раунда сервер не хранит. Клиент получает весь раунд одним
запросом и ведёт его у себя, а на сервер шлёт ответы по одному. Это не
экономия, а осознанный выбор: состояние в памяти процесса уже однажды
заставило нас запускать gunicorn одним воркером, и повторять эту ошибку
на втором интерфейсе не стоит.
"""

import hashlib
import hmac
import json
import os
import random
import time
import urllib.parse
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

import audio
import db
import quiz
from matching import check_answer, scramble
from translit import translit

api = Blueprint("webapp", __name__)

HERE = Path(__file__).resolve().parent
PAGE = HERE / "static" / "app.html"

# Сколько живёт подпись. Telegram не переоткрывает initData, пока
# приложение открыто, поэтому запас должен покрывать долгую сессию, но не
# быть бесконечным: перехваченная строка не должна работать вечно.
MAX_AUTH_AGE = 24 * 3600


def verify_init_data(init_data, token, max_age=MAX_AUTH_AGE):
    """Проверяет подпись Telegram и возвращает пользователя или None.

    Без этой проверки Mini App беззащитен: initData приходит от клиента,
    и подделать «я пользователь X» может кто угодно. Алгоритм задан
    Telegram: секрет — HMAC-SHA256 от токена бота с ключом «WebAppData»,
    а подпись — HMAC-SHA256 от строки «ключ=значение», отсортированной по
    алфавиту и склеенной переводами строк.
    """
    if not init_data or not token:
        return None
    try:
        pairs = urllib.parse.parse_qsl(init_data, keep_blank_values=True,
                                       strict_parsing=True)
    except ValueError:
        return None

    data = dict(pairs)
    received = data.pop("hash", None)
    if not received:
        return None

    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()

    def signature(fields):
        check = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
        return hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()

    # Поле signature появилось позже и предназначено для сторонней
    # проверки. В документации не сказано прямо, входит ли оно в хеш,
    # поэтому пробуем оба варианта — так проверка не сломается от
    # изменения на стороне Telegram.
    variants = [data]
    if "signature" in data:
        variants.append({k: v for k, v in data.items() if k != "signature"})
    if not any(hmac.compare_digest(signature(v), received) for v in variants):
        return None

    # Подпись верна, но данные могли быть перехвачены давно.
    try:
        age = time.time() - int(data.get("auth_date", 0))
    except (TypeError, ValueError):
        return None
    if age > max_age or age < -300:      # запас на расхождение часов
        return None

    try:
        return json.loads(data["user"])
    except (KeyError, ValueError):
        return None


def _token():
    return os.environ.get("TELEGRAM_TOKEN", "")


def current_user():
    """Пользователь текущего запроса или None."""
    payload = request.get_json(silent=True) or {}
    init_data = payload.get("init_data") or request.headers.get("X-Init-Data", "")
    return verify_init_data(init_data, _token())


def guarded(fn):
    """Роут, доступный только с подписью Telegram."""
    def wrapper(*a, **kw):
        user = current_user()
        if not user:
            return jsonify({"error": "unauthorized"}), 401
        return fn(str(user["id"]), request.get_json(silent=True) or {}, *a, **kw)
    wrapper.__name__ = fn.__name__
    return wrapper


# ---------- страница ----------

@api.route("/app")
def page():
    if not PAGE.exists():
        return "Mini App не собран", 404
    return send_file(PAGE)


# ---------- данные для меню ----------

@api.route("/api/menu", methods=["POST"])
@guarded
def menu(chat_id, payload):
    """Разделы и темы. Отдаём с сервера, чтобы приложение не хранило
    вторую копию списка категорий."""
    try:
        db.touch_user(chat_id)
        due = db.due_count(chat_id)
        weak = len(db.weak_cards(chat_id, limit=100))
    except Exception as e:
        print(f"[menu] {e}")
        due, weak = 0, 0
    counts = {m: len(p) for m, p in quiz.POOLS.items()}
    by_cat = {}
    for _, _, cat in quiz.POOLS["vocab"]:
        by_cat[cat] = by_cat.get(cat, 0) + 1
    return jsonify({
        "topics": [{"key": k, "name": n, "count": by_cat.get(k, 0)}
                   for k, n in quiz.TOPIC_LABELS.items()],
        "grammar": [{"key": k, "name": n, "count": by_cat.get(k, 0)}
                    for k, n in quiz.GRAMMAR_LABELS.items()],
        "verbs": [{"key": m, "name": quiz.LABELS[m], "count": counts[m]}
                  for m in ("verbs", "past", "present", "future")],
        "alphabet": [{"key": m, "name": quiz.LABELS[m], "count": counts[m]}
                     for m in sorted(quiz.ALPHABET_MODES)],
        "due": due,
        "weak": weak,
        "anagram_modes": sorted(quiz.ANAGRAM_MODES),
    })


# ---------- раунд ----------

@api.route("/api/round", methods=["POST"])
@guarded
def round_(chat_id, payload):
    """Весь раунд одним запросом. Верный ответ клиенту не отдаём —
    его знает только сервер, иначе он лежал бы в отладчике браузера."""
    mode = payload.get("mode", "vocab")
    cat = payload.get("cat") or None
    fmt = payload.get("format", "choice")
    if mode not in quiz.POOLS and mode != "weak":
        return jsonify({"error": "unknown mode"}), 400

    pool, label, modes = quiz.round_pool(chat_id, mode, cat)
    if len(pool) < 4:
        return jsonify({"error": "too_small", "label": label}), 409

    try:
        priorities = {} if mode == "weak" else db.card_priorities(chat_id, mode)
    except Exception as e:
        print(f"[round] приоритеты недоступны: {e}")
        priorities = {}

    used, questions = set(), []
    for _ in range(min(quiz.ROUND_LEN, len(pool))):
        q = quiz.build_question(pool, used, priorities)
        used.add(q["ru"])
        card_mode = modes.get((q["ru"], q["correct"]), mode)
        item = {"ru": q["ru"], "mode": card_mode}
        if fmt == "choice":
            item["options"] = q["options"]
        elif fmt == "anagram":
            item["letters"] = scramble(q["correct"], random)
        questions.append(item)

    return jsonify({"label": label, "format": fmt, "questions": questions})


@api.route("/api/answer", methods=["POST"])
@guarded
def answer(chat_id, payload):
    """Судит сервер: клиент присылает то, что выбрал или набрал."""
    mode = payload.get("mode", "vocab")
    card_id = payload.get("ru", "")
    given = payload.get("answer", "")
    skipped = bool(payload.get("skip"))

    found = quiz.ANSWERS.get(mode, {}).get(card_id)
    if not found:
        return jsonify({"error": "unknown card"}), 400
    expected, _cat = found

    if skipped:
        verdict = "skip"
    elif payload.get("format") == "choice":
        verdict = "exact" if given == expected else "wrong"
    else:
        verdict = check_answer(given, expected, quiz.KNOWN_FORMS.get(mode))

    correct = verdict in ("exact", "typo")
    try:
        before = db.card_history(chat_id, card_id, mode)
        db.record_answer(chat_id, mode, card_id, correct)
    except Exception as e:
        print(f"[answer] {e}")
        before = None

    reading = "" if mode in quiz.ALPHABET_MODES else translit(expected)
    return jsonify({
        "verdict": verdict,
        "correct": correct,
        "expected": expected,
        "reading": reading,
        "audio": audio.audio_key(expected) if audio.has_audio(expected) else None,
        "memory": _memory_line(before, correct),
    })


def _memory_line(before, correct):
    import reactions
    return reactions.memory_line(before, correct)


# ---------- прогресс ----------

@api.route("/api/stats", methods=["POST"])
@guarded
def stats(chat_id, payload):
    try:
        overall = db.overall_stats(chat_id)
        by_mode = db.stats_by_mode(chat_id)
        weak = db.weak_cards(chat_id, limit=10)
        streak = db.streak_days(chat_id)
        due = db.due_count(chat_id)
    except Exception as e:
        print(f"[stats] {e}")
        return jsonify({"error": "db"}), 503

    rows = []
    for w in weak:
        found = quiz.ANSWERS.get(w["mode"], {}).get(w["card_id"])
        he = found[0] if found else None
        rows.append({
            "ru": w["card_id"], "he": he,
            "reading": translit(he) if he and w["mode"] not in quiz.ALPHABET_MODES else "",
            "wrong": w["n_wrong"], "mode": w["mode"],
        })
    return jsonify({
        "total": overall["total"], "correct": overall["correct"],
        "streak": streak, "due": due,
        "by_mode": [{"mode": m, "name": quiz.LABELS[m], **s}
                    for m, s in by_mode.items() if m in quiz.LABELS],
        "weak": rows,
    })


# ---------- озвучка ----------

@api.route("/api/audio/<key>")
def audio_file(key):
    """Готовый ogg по ключу. Ключ — хеш от слова, перебрать его нельзя,
    и ничего чувствительного в озвучке нет, поэтому без подписи."""
    if not key.isalnum():
        return "", 404
    path = os.path.join(audio.AUDIO_DIR, f"{key}.ogg")
    if not os.path.exists(path):
        return "", 404
    return send_file(path, mimetype="audio/ogg")
