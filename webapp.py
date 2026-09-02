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
import re
import time
import urllib.parse
from pathlib import Path

from flask import Blueprint, g, jsonify, request, send_file

import audio
import db
import hebrew_name
import phrases
import phrases_en
import quiz
import word_art
from matching import check_answer, scramble
from translit import reading, translit

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
        # Язык берём из ПРОВЕРЕННЫХ данных Telegram, а не из тела
        # запроса. Разница не косметическая: подпись покрывает поле
        # language_code, а присланное клиентом можно написать любое.
        # Сам по себе выбор языка безобиден, но правило простое —
        # то, что влияет на ответ сервера, приходит только из
        # подписанного источника.
        g.lang = db.resolve_lang(user["id"], user.get("language_code"))
        return fn(str(user["id"]), request.get_json(silent=True) or {}, *a, **kw)
    wrapper.__name__ = fn.__name__
    return wrapper


def req_lang():
    """Язык текущего запроса. Вне запроса — русский."""
    return getattr(g, "lang", db.DEFAULT_LANG)


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
    lang = req_lang()
    counts = {m: len(p) for m, p in quiz.POOLS.items()}
    by_cat = {}
    for card in quiz.POOLS["vocab"]:
        by_cat[card.cat] = by_cat.get(card.cat, 0) + 1
    name = lambda m, cat=None: quiz.section_label(m, cat, lang)
    return jsonify({
        "topics": [{"key": k, "name": name("vocab", k), "count": by_cat.get(k, 0)}
                   for k in quiz.TOPIC_LABELS],
        "grammar": [{"key": k, "name": name("vocab", k), "count": by_cat.get(k, 0)}
                    for k in quiz.GRAMMAR_LABELS],
        "verbs": [{"key": m, "name": name(m), "count": counts[m]}
                  for m in ("verbs", "past", "present", "future")],
        "alphabet": [{"key": m, "name": name(m), "count": counts[m]}
                     for m in quiz.ALPHABET_ORDER],
        "due": due,
        "weak": weak,
        "anagram_modes": sorted(quiz.ANAGRAM_MODES),
        # Язык отдаём с первым же ответом: страница до этого показывает
        # заставку и ничего не подписывает, а свой список «каким странам
        # какой язык» ей заводить незачем — он один и лежит здесь.
        "lang": lang,
    })


def _heb_name():
    """Имя ивритскими буквами и признак того, что мы его угадали.

    Имя берём из подписанного initData, а не из тела запроса: тело
    клиент волен написать любое, а подпись Telegram подделать нельзя.
    Правка пользователя всегда перевешивает то, что вывели правила.
    """
    user = current_user() or {}
    ru = (user.get("first_name") or "").strip()
    auto = hebrew_name.to_hebrew(ru)
    try:
        saved = db.heb_name(str(user.get("id", "")))
    except Exception as e:
        print(f"[heb_name] {e}")
        saved = None
    return {
        "ru": ru,
        "heb": saved or auto,
        "auto": auto,
        # Подсказку «поправьте, если не так» показываем только там, где
        # действительно гадали: у имён из таблицы написание известное.
        "guess": bool(auto) and not saved and hebrew_name.is_guess(ru),
        "edited": bool(saved),
    }


# ---------- раунд ----------

# Ивритский текст внутри подсказки. Нужен, чтобы карточка знакомства
# всегда показывала крупно именно ивритское написание: у словаря оно
# лежит в ответе («хлеб» → לֶחֶם), а у курса алфавита — в вопросе
# («буква א» → «алеф»).
HEB_RUN = re.compile(r"[\u0590-\u05FF][\u0590-\u05FF]*")


def _intro_card(card, mode, lang="ru"):
    """Карточка знакомства: что показать крупно, как это читается и что
    оно значит."""
    ru, he = card.prompt(lang), card.answer(lang)
    if HEB_RUN.search(he):
        main, gloss = he, ru
    else:
        m = HEB_RUN.search(ru)
        main, gloss = (m.group(0) if m else ru), he
    return {
        "id": card.key(),
        "ru": ru,
        "main": main,
        "gloss": gloss,
        "cat": card.cat,
        # Номер рисунка к слову. Отдаём с карточкой, а не ищем на
        # клиенте: карта соответствий не должна лежать в странице и не
        # должна зависеть от языка подсказки.
        "art": word_art.ART.get(card.key()),
        "reading": reading(main, lang) if mode not in quiz.ALPHABET_MODES else "",
        "audio": audio.audio_key(main) if audio.has_audio(main) else None,
    }

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

    lang = req_lang()
    pool, label, modes = quiz.round_pool(chat_id, mode, cat, lang)
    if len(pool) < 4:
        return jsonify({"error": "too_small", "label": label}), 409

    try:
        priorities = {} if mode == "weak" else db.card_priorities(chat_id, mode)
    except Exception as e:
        print(f"[round] приоритеты недоступны: {e}")
        priorities = {}

    # Знакомство: слова, которых человек ещё не видел. Если такие есть,
    # раунд спрашивает ровно их — сначала показали, потом проверили.
    intro = quiz.intro_cards(chat_id, mode, pool)
    # Когда новых слов в теме осталось два, раунд из двух вопросов —
    # огрызок. Спрашиваем сперва их, а до разумной длины добираем
    # повторением из той же темы.
    count = (max(len(intro), quiz.MIN_ROUND) if intro
             else min(quiz.ROUND_LEN, len(pool)))
    count = min(count, len(pool))

    used, questions = set(), []
    for i in range(count):
        pick = intro if (intro and i < len(intro)) else None
        q = quiz.build_question(pool, used, priorities, pick_from=pick, lang=lang)
        used.add(q["id"])
        card_mode = modes.get(q["id"], mode)
        # `id` — устойчивый ключ, по нему сервер и узнает карточку в
        # /api/answer. `ru` остаётся текстом вопроса: клиент его только
        # показывает. Раньше это было одно поле, и оно же служило ключом.
        item = {"id": q["id"], "ru": q["ru"], "mode": card_mode}
        if fmt == "choice":
            item["options"] = q["options"]
        elif fmt == "anagram":
            item["letters"] = scramble(q["correct"], random)
        questions.append(item)

    return jsonify({
        "label": label, "format": fmt, "questions": questions,
        "intro": [_intro_card(c, mode, lang) for c in intro],
    })


@api.route("/api/answer", methods=["POST"])
@guarded
def answer(chat_id, payload):
    """Судит сервер: клиент присылает то, что выбрал или набрал."""
    mode = payload.get("mode", "vocab")
    # `id` — устойчивый ключ. `ru` принимаем как запасной вариант: у
    # человека, открывшего приложение до выкладки, в памяти телефона
    # остался старый раунд, и его последние ответы не должны пропасть.
    card_id = payload.get("id") or payload.get("ru", "")
    given = payload.get("answer", "")
    skipped = bool(payload.get("skip"))
    lang = req_lang()

    card = quiz.find_card(mode, card_id)
    if not card:
        return jsonify({"error": "unknown card"}), 400
    card_id = card.key()
    expected = card.answer(lang)

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

    # Чтение — на языке интерфейса: «лехем» или «lekhem».
    read = "" if mode in quiz.ALPHABET_MODES else reading(expected, lang)
    # Озвучка привязана к ивриту, а не к языку интерфейса: у карточек
    # алфавита ответ переводится («далет» / «dalet»), и искать запись по
    # переведённому тексту значило бы терять её при смене языка.
    voice = card.he
    return jsonify({
        "verdict": verdict,
        "correct": correct,
        "expected": expected,
        "reading": read,
        "audio": audio.audio_key(voice) if audio.has_audio(voice) else None,
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
    lang = req_lang()
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
    for key in quiz.TOPIC_LABELS:
        ids = [c.key() for c in quiz.POOLS["vocab"] if c.cat == key]
        learned = sum(1 for i in ids if boxes.get(i, 0) >= 4)
        seen = sum(1 for i in ids if i in boxes)
        topics.append({"key": key, "name": quiz.section_label("vocab", key, lang),
                       "total": len(ids), "learned": learned, "seen": seen})

    resume = None
    if last:
        mode = last["mode"]
        found = quiz.find_card(mode, last["card_id"])
        cat = found.cat if found and mode == "vocab" else None
        label = quiz.section_label(mode, cat, lang)
        if label:
            resume = {"mode": mode, "cat": cat, "label": label}
            # Показываем то самое слово, которое выпадет первым: ярлык
            # темы не говорит, ради чего нажимать.
            try:
                pool, _, _ = quiz.round_pool(chat_id, mode, cat, lang)
                prio = db.card_priorities(chat_id, mode)
                if pool:
                    card = quiz.pick_card(pool, prio)
                    he = card.answer(lang)
                    resume.update({
                        "ru": card.prompt(lang), "he": he,
                        "reading": "" if mode in quiz.ALPHABET_MODES else reading(he, lang),
                        "audio": (audio.audio_key(card.he)
                                  if audio.has_audio(card.he) else None),
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
        c = quiz.pick_daily_word(chat_id)
        word = {"ru": c.prompt(lang), "he": c.he, "reading": reading(c.he, lang),
                "audio": audio.audio_key(c.he) if audio.has_audio(c.he) else None}
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
        "name": _heb_name(),
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

    lang = req_lang()
    items = []
    for c in quiz.POOLS["vocab"]:
        box = boxes.get(c.key(), 0)
        items.append({
            "id": c.key(),
            "ru": c.prompt(lang), "he": c.he, "reading": reading(c.he, lang),
            "cat": c.cat,
            "topic": quiz.section_label("vocab", c.cat, lang),
            # Саму коробку клиенту не отдаём: ему нужно состояние, а не
            # внутренняя механика Лейтнера. На 273 словах экономия
            # заметна, а показывать «коробка 3» человеку незачем.
            "state": "learned" if box >= LEARNED_BOX else "learning" if box else "new",
            "fav": c.key() in favs,
            "audio": audio.audio_key(c.he) if audio.has_audio(c.he) else None,
        })
    return jsonify({"words": items, "learned_box": LEARNED_BOX})


@api.route("/api/favourite", methods=["POST"])
@guarded
def favourite(chat_id, payload):
    card = quiz.find_card("vocab", payload.get("id") or payload.get("ru", ""))
    if not card:
        return jsonify({"error": "unknown card"}), 400
    on = bool(payload.get("on"))
    try:
        db.set_favourite(chat_id, card.key(), on)
    except Exception as e:
        print(f"[favourite] {e}")
        return jsonify({"error": "db"}), 503
    return jsonify({"id": card.key(), "fav": on})


@api.route("/api/know", methods=["POST"])
@guarded
def know(chat_id, payload):
    """«Я уже знаю это»: карточка уходит в последнюю коробку."""
    mode = payload.get("mode", "vocab")
    lang = req_lang()
    card = quiz.find_card(mode, payload.get("id") or payload.get("ru", ""))
    if not card:
        return jsonify({"error": "unknown card"}), 400
    try:
        db.mark_known(chat_id, card.key(), mode)
    except Exception as e:
        print(f"[know] {e}")
        return jsonify({"error": "db"}), 503
    expected = card.answer(lang)
    return jsonify({
        "id": card.key(), "expected": expected,
        "reading": "" if mode in quiz.ALPHABET_MODES else reading(expected, lang),
    })


# ---------- разговорные модели ----------

SAY_MODE = "say"        # отдельный режим для интервальных повторений
SAY_LEN = 8             # длина подхода: больше — и голос устаёт


def _say_card(cid, ph, female, lang="ru", where=None):
    """Одна модель для показа. Слот не заполняем: подставлять слово —
    отдельное упражнение, а здесь задача произнести каркас.

    `where` — пара (ситуация, номер): по ней берётся английская подпись.
    """
    he = phrases.text(ph, female, lang)
    # Показываем со слотом-многоточием, а озвучиваем и ищем звук по той
    # же строке, что записал генератор, — иначе ключи разойдутся.
    shown = he.replace(phrases.SLOT, "…")
    voice = phrases.spoken(ph, female, lang=lang)
    if lang == "en" and where:
        label = phrases_en.phrase_text(where[0], where[1], ph["ru"]) or ph["ru"]
        note = phrases_en.note(*where) or None
    else:
        label, note = ph["ru"], ph.get("note")
    card = {
        "id": cid,
        "ru": label.replace(phrases.SLOT, "…"),
        "he": shown,
        "reading": reading(voice, lang),
        "audio": audio.audio_key(voice) if audio.has_audio(voice) else None,
        "note": note,
        "slot": ph.get("slot"),
    }
    # Фразы, зависящие от пола собеседника, отдаём обеими формами.
    # Выбрать за человека нельзя: приложение не знает, к мужчине он
    # обратится или к женщине, а подстановка наугад учит неверной форме.
    pair = phrases.listener_forms(ph)
    if pair:
        def side(to_female):
            # Ключ звука — только через spoken(). Раньше здесь стояла
            # сырая строка, и совпадало это по случайности.
            v = phrases.spoken(ph, listener_female=to_female, lang=lang)
            raw = pair["to_f"] if to_female else pair["to_m"]
            return {"he": raw.replace(phrases.SLOT, "…"),
                    "reading": reading(v, lang),
                    "audio": audio.audio_key(v) if audio.has_audio(v) else None}
        card["to"] = {"m": side(False), "f": side(True)}

    # Пример с заполненным слотом: человеку — образец целого предложения,
    # диктору — то, что он произносит вместо «אֲנִי גָּר בְּ».
    ex = ph.get("example")
    if ex:
        card["example"] = {
            "he": (ex["he_f"] if (female and ex.get("he_f")) else ex["he"]),
            "ru": ex["ru"],
        }
    return card


@api.route("/api/say", methods=["POST"])
@guarded
def say(chat_id, payload):
    """Подход разговорных моделей.

    Порядок задают те же коробки Лейтнера, что и у слов: интервальные
    повторения — это расписание, а не метод, и в них ложится что угодно,
    в том числе произнесённая вслух фраза.
    """
    situation = payload.get("situation")
    if situation and situation not in phrases.SITUATIONS:
        return jsonify({"error": "unknown situation"}), 400

    female = False
    try:
        female = db.gender(chat_id) == "f"
        priorities = db.card_priorities(chat_id, SAY_MODE)
    except Exception as e:
        print(f"[say] {e}")
        priorities = {}

    pool = [(phrases.card_id(s, i), p, (s, i))
            for s, items in phrases.PHRASES.items()
            for i, p in enumerate(items)
            if not situation or s == situation]
    if not pool:
        return jsonify({"error": "empty"}), 409

    # Сначала то, что пора повторить, затем невиданное, затем остальное.
    rank = lambda c: priorities.get(c[0], db.PRIORITY_NEW)
    pool.sort(key=lambda c: (-rank(c), random.random()))
    take = pool[:SAY_LEN]
    random.shuffle(take)

    lang = req_lang()
    names = phrases_en.SITUATIONS_EN if lang == "en" else phrases.SITUATIONS
    fallback = "conversation" if lang == "en" else "разговор"
    return jsonify({
        "label": names.get(situation, fallback),
        "female": female,
        "gender_set": bool(db.gender(chat_id)) if priorities is not None else False,
        "cards": [_say_card(cid, ph, female, lang, where)
                  for cid, ph, where in take],
    })


@api.route("/api/say_answer", methods=["POST"])
@guarded
def say_answer(chat_id, payload):
    """Самооценка: сказал или не смог.

    Машина здесь не судья — она и не может им быть, пока нет распознавания
    речи. Но произнесённая вслух фраза с честной отметкой полезнее, чем
    выбор из четырёх вариантов с точной проверкой.
    """
    cid = payload.get("id", "")
    if not phrases.by_id(cid):
        return jsonify({"error": "unknown card"}), 400
    said = bool(payload.get("said"))
    try:
        db.record_answer(chat_id, SAY_MODE, cid, said)
        db.award_for_answer(chat_id, said)
    except Exception as e:
        print(f"[say_answer] {e}")
    return jsonify({"ok": True})


@api.route("/api/situations", methods=["POST"])
@guarded
def situations(chat_id, payload):
    """Список ситуаций с тем, сколько в каждой уже отработано."""
    try:
        boxes = db.card_boxes(chat_id, SAY_MODE)
    except Exception as e:
        print(f"[situations] {e}")
        boxes = {}
    lang = req_lang()
    names = phrases_en.SITUATIONS_EN if lang == "en" else phrases.SITUATIONS
    out = []
    for key in phrases.SITUATIONS:
        ids = [phrases.card_id(key, i) for i in range(len(phrases.PHRASES[key]))]
        out.append({
            "key": key, "name": names.get(key, ""), "total": len(ids),
            "seen": sum(1 for c in ids if c in boxes),
            "learned": sum(1 for c in ids if boxes.get(c, 0) >= LEARNED_BOX),
        })
    return jsonify({"situations": out, "gender": db.gender(chat_id)})


# ---------- профиль ----------

@api.route("/api/profile", methods=["POST"])
@guarded
def profile(chat_id, payload):
    """Настройки и итоги. Настройки те же, что командами в чате, — иначе
    человек будет искать, где переключается озвучка, в двух местах."""
    # Правка имени. Пустая строка стирает её и возвращает автоматическое
    # написание — иначе опечатку было бы нечем откатить.
    if "name" in payload:
        try:
            db.set_heb_name(chat_id, str(payload["name"])[:40])
        except Exception as e:
            print(f"[profile] имя: {e}")
            return jsonify({"error": "db"}), 503

    # Пол говорящего — не переключатель «да/нет», поэтому отдельно.
    if "gender" in payload:
        try:
            db.set_gender(chat_id, payload["gender"])
        except Exception as e:
            print(f"[profile] пол: {e}")
            return jsonify({"error": "db"}), 503

    # Язык интерфейса. Выбранный руками сильнее того, что стоит в
    # Telegram: человек мог держать телефон на английском и всё равно
    # хотеть учиться по-русски.
    if "lang" in payload:
        try:
            g.lang = db.set_lang(chat_id, payload["lang"]) or req_lang()
        except Exception as e:
            print(f"[profile] язык: {e}")
            return jsonify({"error": "db"}), 503

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
            "name": _heb_name(),
            "gender": db.gender(chat_id),
            "lang": req_lang(),
            "langs": list(db.LANGS),
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
    lang = req_lang()
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
        card = quiz.find_card(w["mode"], w["card_id"])
        # Ключ карточки больше не человеческий текст: показывать его
        # нельзя, иначе в списке слабых мест окажется «food:לחם».
        # Карточки может не быть — слово могли убрать из словаря.
        if not card:
            continue
        he = card.answer(lang)
        rows.append({
            "ru": card.prompt(lang), "he": he,
            "reading": "" if w["mode"] in quiz.ALPHABET_MODES else reading(he, lang),
            "wrong": w["n_wrong"], "mode": w["mode"],
        })
    return jsonify({
        "total": overall["total"], "correct": overall["correct"],
        "streak": streak, "due": due,
        "by_mode": [{"mode": m, "name": quiz.section_label(m, lang=lang), **s}
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
