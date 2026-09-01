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
import mimetypes
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

# В некоторых сборках Python webp не значится в таблице типов, и Flask
# отдаёт картинки как application/octet-stream. Браузеры их всё равно
# показывают, угадывая по содержимому, но полагаться на угадывание не
# стоит: часть окружений при таком заголовке предложит скачать файл.
mimetypes.add_type("image/webp", ".webp")

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


@api.route("/preview")
def preview():
    """Та же страница, но с подставными данными вместо Telegram и API.

    Нужен, чтобы вёрстку можно было посмотреть в обычном браузере, не
    заходя с телефона и ничего не выкатывая на прод. Реальных данных
    здесь нет по построению: подменяется сам fetch, и до API дело не
    доходит — значит и подпись не нужна, и утечь нечему.
    """
    stub = HERE / "tools" / "preview_stub.js"
    if not PAGE.exists() or not stub.exists():
        return "Предпросмотр недоступен", 404
    html = PAGE.read_text(encoding="utf-8").replace(
        '<script src="https://telegram.org/js/telegram-web-app.js"></script>',
        "<script>\n" + stub.read_text(encoding="utf-8") + "\n</script>")
    return html, 200, {"Content-Type": "text/html; charset=utf-8",
                       "Cache-Control": "no-store"}


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
                     for m in quiz.ALPHABET_ORDER],
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
        db.award_for_answer(chat_id, correct)
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


# ---------- главный экран ----------

@api.route("/api/home", methods=["POST"])
@guarded
def home(chat_id, payload):
    """Всё для главного экрана одним запросом: профиль, «продолжить»,
    прогресс по темам."""
    try:
        db.touch_user(chat_id)
        xp = db.total_xp(chat_id)
        level, at_level, need = db.level_for(xp)
        streak = db.streak_days(chat_id)
        due = db.due_count(chat_id)
        weak = len(db.weak_cards(chat_id, limit=100))
        boxes = db.learned_by_card(chat_id)
        last = db.last_activity(chat_id)
        overall = db.overall_stats(chat_id)
    except Exception as e:
        print(f"[home] {e}")
        return jsonify({"error": "db"}), 503

    # Прогресс по темам. «Выучено» — коробка 4 и выше: слово пережило
    # три верных ответа с растущими промежутками. Считать пройденным по
    # одному верному ответу было бы приятнее и неправдой.
    topics = []
    for key, name in quiz.TOPIC_LABELS.items():
        cards = [ru for ru, _, cat in quiz.POOLS["vocab"] if cat == key]
        learned = sum(1 for ru in cards if boxes.get(ru, 0) >= 4)
        seen = sum(1 for ru in cards if ru in boxes)
        topics.append({"key": key, "name": name, "total": len(cards),
                       "learned": learned, "seen": seen})

    resume = None
    if last:
        mode = last["mode"]
        found = quiz.ANSWERS.get(mode, {}).get(last["card_id"])
        cat = found[1] if found and mode == "vocab" else None
        label = (quiz.TOPIC_LABELS.get(cat) or quiz.GRAMMAR_LABELS.get(cat)
                 or quiz.LABELS.get(mode))
        if label:
            resume = {"mode": mode, "cat": cat, "label": label}
            # Показываем то самое слово, которое выпадет первым: ярлык
            # темы не говорит, ради чего нажимать.
            try:
                pool, _, _ = quiz.round_pool(chat_id, mode, cat)
                prio = db.card_priorities(chat_id, mode)
                if pool:
                    ru, he, _c = quiz.pick_card(pool, prio)
                    resume.update({
                        "ru": ru, "he": he,
                        "reading": "" if mode in quiz.ALPHABET_MODES else translit(he),
                        "audio": audio.audio_key(he) if audio.has_audio(he) else None,
                    })
            except Exception as e:
                print(f"[home] превью не собралось: {e}")

    # Полоска недели: видно, в какие дни занимался. Данные уже есть в
    # ответах, отдельно ничего не пишем.
    from datetime import date, timedelta
    active = db.active_days(chat_id, 7)
    today = date.today()
    LETTERS = "ПВСЧПСВ"
    week = [{"l": LETTERS[(today - timedelta(days=6 - i)).weekday()],
             "on": (today - timedelta(days=6 - i)).isoformat() in active,
             "today": i == 6}
            for i in range(7)]

    # Слово дня — то же, что присылает бот по утрам, теми же правилами.
    try:
        wru, whe, _wc = quiz.pick_daily_word(chat_id)
        word = {"ru": wru, "he": whe, "reading": translit(whe),
                "audio": audio.audio_key(whe) if audio.has_audio(whe) else None}
    except Exception as e:
        print(f"[home] слово дня не собралось: {e}")
        word = None

    return jsonify({
        "xp": xp, "level": level, "at_level": at_level, "need": need,
        "streak": streak, "due": due, "weak": weak,
        "week": week, "word": word,
        "answers": overall["total"], "correct": overall["correct"],
        "learned": sum(1 for b in boxes.values() if b >= 4),
        "topics": topics, "resume": resume,
    })


@api.route("/api/round_done", methods=["POST"])
@guarded
def round_done(chat_id, payload):
    """Клиент сообщает, что раунд закончен — только ради надбавки за
    идеальный результат. Счёт сервер знает и сам, но границы раунда —
    нет: он их не хранит."""
    try:
        score = int(payload.get("score", 0))
        total = int(payload.get("total", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "bad"}), 400
    db.award_for_round(chat_id, min(score, total), total)
    xp = db.total_xp(chat_id)
    level, at_level, need = db.level_for(xp)
    return jsonify({"xp": xp, "level": level, "at_level": at_level, "need": need})


# ---------- словарь ----------

# «Изучаю» — коробки 1–3, «изучено» — 4 и выше. Порог тот же, что у
# колец на главной: одно определение выученного на всё приложение.
LEARNED_BOX = 4


@api.route("/api/words", methods=["POST"])
@guarded
def words(chat_id, payload):
    """Весь словарь со состоянием каждого слова.

    Отдаём разом, а не страницами: 273 слова весят пару десятков
    килобайт, зато поиск и фильтры работают мгновенно на клиенте, без
    запроса на каждую букву.
    """
    try:
        boxes = db.word_boxes(chat_id)
        favs = db.favourites(chat_id)
    except Exception as e:
        print(f"[words] {e}")
        boxes, favs = {}, set()

    items = []
    for ru, he, cat in quiz.POOLS["vocab"]:
        box = boxes.get(ru, 0)
        items.append({
            "ru": ru, "he": he, "reading": translit(he), "cat": cat,
            "topic": quiz.TOPIC_LABELS.get(cat) or quiz.GRAMMAR_LABELS.get(cat, ""),
            # Саму коробку клиенту не отдаём: ему нужно состояние, а не
            # внутренняя механика Лейтнера. На 273 словах экономия
            # заметна, а показывать «коробка 3» человеку незачем.
            "state": "learned" if box >= LEARNED_BOX else "learning" if box else "new",
            "fav": ru in favs,
            "audio": audio.audio_key(he) if audio.has_audio(he) else None,
        })
    return jsonify({"words": items, "learned_box": LEARNED_BOX})


@api.route("/api/favourite", methods=["POST"])
@guarded
def favourite(chat_id, payload):
    ru = payload.get("ru", "")
    if ru not in quiz.ANSWERS.get("vocab", {}):
        return jsonify({"error": "unknown card"}), 400
    on = bool(payload.get("on"))
    try:
        db.set_favourite(chat_id, ru, on)
    except Exception as e:
        print(f"[favourite] {e}")
        return jsonify({"error": "db"}), 503
    return jsonify({"ru": ru, "fav": on})


@api.route("/api/know", methods=["POST"])
@guarded
def know(chat_id, payload):
    """«Я уже знаю это»: карточка уходит в последнюю коробку."""
    mode = payload.get("mode", "vocab")
    ru = payload.get("ru", "")
    found = quiz.ANSWERS.get(mode, {}).get(ru)
    if not found:
        return jsonify({"error": "unknown card"}), 400
    try:
        db.mark_known(chat_id, ru, mode)
    except Exception as e:
        print(f"[know] {e}")
        return jsonify({"error": "db"}), 503
    return jsonify({"ru": ru, "expected": found[0],
                    "reading": translit(found[0]) if mode not in quiz.ALPHABET_MODES else ""})


# ---------- профиль ----------

@api.route("/api/profile", methods=["POST"])
@guarded
def profile(chat_id, payload):
    """Настройки и итоги. Настройки те же, что командами в чате, — иначе
    человек будет искать, где переключается озвучка, в двух местах."""
    if "set" in payload:
        what, value = payload["set"], bool(payload.get("value"))
        try:
            {"voice": db.set_voice, "slow": db.set_slow_voice,
             "daily": db.set_daily_word, "reactions": db.set_reactions}[what](chat_id, value)
        except KeyError:
            return jsonify({"error": "unknown setting"}), 400
        except Exception as e:
            print(f"[profile] {e}")
            return jsonify({"error": "db"}), 503

    try:
        overall = db.overall_stats(chat_id)
        xp = db.total_xp(chat_id)
        level, at_level, need = db.level_for(xp)
        return jsonify({
            "xp": xp, "level": level, "at_level": at_level, "need": need,
            "streak": db.streak_days(chat_id),
            "answers": overall["total"], "correct": overall["correct"],
            "learned": sum(1 for b in db.word_boxes(chat_id).values() if b >= LEARNED_BOX),
            "favourites": len(db.favourites(chat_id)),
            "voice": db.voice_enabled(chat_id), "slow": db.slow_voice(chat_id),
            "daily": db.is_subscribed(chat_id), "reactions": db.reactions_enabled(chat_id),
        })
    except Exception as e:
        print(f"[profile] {e}")
        return jsonify({"error": "db"}), 503


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
