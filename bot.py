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
import hebrew_name
import phrases
import quiz
import reactions
from messages import t, plural
from quiz import (
    POOLS, LABELS, TOPIC_LABELS, GRAMMAR_LABELS, ALPHABET_MODES,
    ANSWERS, KNOWN_FORMS, ANAGRAM_MODES, ROUND_LEN, VOCAB_FLAT,
    build_question, round_pool,
)
from matching import check_answer, accepted_forms, hint_for, scramble
from translit import reading, translit
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

# Кому доступен /admin. Пусто — команда не работает ни у кого, кроме
# подсказки «вот твой chat_id, впиши его в .env»: иначе на свежей
# установке сводку увидел бы первый, кто наберёт команду.
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "").strip()

# Адрес Mini App. Пока домен не задан, кнопки приложения просто нет —
# бот от этого не ломается и работает как раньше.
BOT_DOMAIN = os.environ.get("BOT_DOMAIN", "").strip()
WEBAPP_URL = f"https://{BOT_DOMAIN}/app" if BOT_DOMAIN else ""

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

# Mini App: страница и API живут на том же домене и том же процессе.
# Отдельный сервис под статику не нужен — Caddy уже держит HTTPS на нашем
# домене, а Telegram другого и не примет.
from webapp import api as webapp_api      # noqa: E402  (после создания app)
app.register_blueprint(webapp_api)

# Прогресс (ответы, статистика, расписание повторений) лежит в SQLite и
# переживает перезапуск. В памяти остаётся только состояние текущего
# раунда — его потерять не страшно.
try:
    db.init_db()
    # Разовый перевод прогресса со старых ключей (русская подсказка) на
    # устойчивые. Должен идти сразу после init_db и ДО первого ответа
    # пользователя, иначе часть строк ляжет в новом формате, а часть
    # останется в старом, и человек увидит обнулённую коробку.
    db.migrate_card_ids(quiz.id_migration_map())
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


# Меню разложено в дерево, а не списком. Причина не в красоте: главный
# экран — это место под разговорные темы (ТЗ, раздел 7), и если весь
# словарь с временами лежит на нём плашмя, ставить туда будет некуда.
# Формат ответа (выбор / написать / анаграмма) вынесен в последний шаг:
# раньше он был отдельной веткой меню и дублировал весь список тем.

# Склонение переехало в messages.plural: формы принадлежат языку, а не
# месту вызова. Прежняя брала три русские формы прямо в аргументах —
# для английского, где их две, такая подпись не годится.

def _counts():
    """Считаем по фактическим пулам, а не пишем цифры руками: словарь
    пополняется, и захардкоженное число разойдётся с правдой молча."""
    cats = {}
    for card in POOLS["vocab"]:
        cats[card.cat] = cats.get(card.cat, 0) + 1
    ph = phrases.stats()
    return {
        "say": ph["total"], "situations": ph["situations"],
        "words": len(POOLS["vocab"]),
        "topic_words": sum(cats.get(k, 0) for k in TOPIC_LABELS),
        "topics": len(TOPIC_LABELS),
        "gram_words": sum(cats.get(k, 0) for k in GRAMMAR_LABELS),
        "gram": len(GRAMMAR_LABELS),
        "verbs": len(POOLS["verbs"]),
        "forms": sum(len(POOLS[m]) for m in ("past", "present", "future")),
        "alef": sum(len(POOLS[m]) for m in ALPHABET_MODES),
        "alef_modes": len(ALPHABET_MODES),
    }


def user_lang(chat_id, tg_user=None):
    """Язык, на котором говорим с этим человеком.

    Правило одно на бота и приложение и живёт в db.resolve_lang: сперва
    выбор в профиле, потом настройки Telegram. Держать вторую копию
    здесь нельзя — разъедутся, и человек, переключивший язык в
    приложении, продолжил бы получать чат на прежнем.
    """
    code = (tg_user or {}).get("language_code")
    try:
        if code:
            # Запоминаем подсказку системы: утренняя рассылка идёт без
            # входящего сообщения, и там спросить будет не у кого.
            db.remember_tg_lang(chat_id, code)
        return db.resolve_lang(chat_id, code)
    except Exception as e:
        print(f"[user_lang] {e}")
        return "ru"


def welcome_text(name="", lang="ru"):
    """Первое сообщение. Коротко: что это, с чего начать, куда нажать."""
    hi = f", {name}" if name else ""
    return f"<b>שלום{hi}!</b>\n" + t("welcome", lang)


def about_text(lang="ru"):
    """«Что умеет бот». Без обещаний того, чего нет.

    Числа считаются по фактическим пулам (см. _counts), а склонение
    берётся из языка: «77 инфинитивов» и «77 infinitives» устроены
    по-разному, и подставить одно в другое нельзя.
    """
    c = _counts()
    n = lambda v, key: plural(v, key, lang)
    return "\n\n".join([
        t("about.head", lang),
        t("about.say", lang, say=c["say"], situations=c["situations"]),
        t("about.alef", lang, modes=c["alef_modes"],
          modes_w=n(c["alef_modes"], "n.section"),
          cards=c["alef"], cards_w=n(c["alef"], "n.card")),
        t("about.words", lang, topic_words=c["topic_words"],
          words_w=n(c["topic_words"], "n.word"), topics=c["topics"],
          gram_words=c["gram_words"], gram=c["gram"]),
        t("about.verbs", lang, verbs=c["verbs"],
          verbs_w=n(c["verbs"], "n.infinitive"),
          forms=c["forms"], forms_w=n(c["forms"], "n.form")),
        t("about.voice", lang),
        t("about.leitner", lang),
        t("about.formats", lang),
        t("about.app", lang),
        t("about.daily", lang),
        t("about.missing", lang),
        t("about.commands", lang),
    ])


def main_menu_keyboard(lang="ru"):
    rows = []
    if WEBAPP_URL:
        rows.append([{"text": t("menu.app", lang),
                      "web_app": {"url": WEBAPP_URL}}])
    return {
        "inline_keyboard": rows + [
            [{"text": t("menu.words", lang), "callback_data": "menu|words"}],
            [{"text": t("menu.alphabet", lang), "callback_data": "alphabet_menu"}],
            [{"text": t("menu.wordOfDay", lang), "callback_data": "word_of_day"},
             {"text": t("menu.stats", lang), "callback_data": "show_stats"}],
        ]
    }


def words_menu_keyboard(lang="ru"):
    return {
        "inline_keyboard": [
            [{"text": t("menu.topics", lang), "callback_data": "menu|topics"}],
            [{"text": t("menu.grammar", lang), "callback_data": "menu|grammar"}],
            [{"text": t("menu.verbs", lang), "callback_data": "menu|verbs"}],
            [{"text": t("menu.weak", lang), "callback_data": "pick|weak|"}],
            [{"text": t("menu.back", lang), "callback_data": "main_menu"}],
        ]
    }


def category_keyboard(keys, back, lang="ru"):
    """Список категорий по две в ряд плюс «всё вперемешку».

    Принимает ключи, а не готовые подписи: название темы берётся из
    quiz.section_label на языке собеседника. Раньше сюда передавали
    словарь TOPIC_LABELS целиком, и подписи были только русские.
    """
    buttons = [{"text": quiz.section_label("vocab", key, lang),
                "callback_data": f"pick|vocab|{key}"} for key in keys]
    rows = keyboard_rows(buttons, per_row=2)
    rows.append([{"text": t("menu.mix", lang), "callback_data": "pick|vocab|"}])
    rows.append([{"text": t("menu.back", lang), "callback_data": back}])
    return {"inline_keyboard": rows}


def verbs_menu_keyboard(lang="ru"):
    return {
        "inline_keyboard": [
            [{"text": t("menu.infinitives", lang), "callback_data": "pick|verbs|"}],
            [{"text": t("menu.past", lang), "callback_data": "pick|past|"},
             {"text": t("menu.present", lang), "callback_data": "pick|present|"}],
            [{"text": t("menu.future", lang), "callback_data": "pick|future|"}],
            [{"text": t("menu.back", lang), "callback_data": "menu|words"}],
        ]
    }


def format_keyboard(mode, cat, lang="ru"):
    """Последний шаг: как отвечать."""
    rows = [
        [{"text": t("menu.choice", lang), "callback_data": f"go|choice|{mode}|{cat}"}],
        [{"text": t("menu.type", lang), "callback_data": f"go|type|{mode}|{cat}"}],
    ]
    if mode in ANAGRAM_MODES:
        rows.append([{"text": t("menu.anagram", lang),
                      "callback_data": f"go|anagram|{mode}|{cat}"}])
    rows.append([{"text": t("menu.back", lang), "callback_data": "menu|words"}])
    return {"inline_keyboard": rows}


def alphabet_menu_keyboard(lang="ru"):
    return {
        "inline_keyboard": [
            [{"text": t("alef.table", lang), "callback_data": "alef_table"}],
            [{"text": t("alef.names", lang), "callback_data": "start_alef_names"},
             {"text": t("alef.sounds", lang), "callback_data": "start_alef_sounds"}],
            [{"text": t("alef.byName", lang), "callback_data": "start_alef_by_name"},
             {"text": t("alef.finals", lang), "callback_data": "start_alef_finals"}],
            [{"text": t("alef.niqqud", lang), "callback_data": "start_alef_niqqud"},
             {"text": t("alef.syllables", lang), "callback_data": "start_alef_syllables"}],
            [{"text": t("alef.dotted", lang), "callback_data": "start_alef_dotted"}],
            [{"text": t("menu.back", lang), "callback_data": "main_menu"}],
        ]
    }


def send_alphabet_table(chat_id, lang="ru"):
    """Справочник: все буквы с названием и звуком, потом огласовки.

    Названия и звуки букв берём из alphabet_en: по-английски хет — не
    «хет», а «chet», и звук у неё описывается своими средствами.
    """
    import alphabet_en as ae
    en = lang == "en"
    name_of = lambda ltr, ru: (ae.LETTER_NAMES_EN.get(ltr) or ru) if en else ru
    sound_of = lambda ltr, ru: (ae.LETTER_SOUNDS_EN.get(ltr) or ru) if en else ru

    lines = [t("alef.title", lang), ""]
    for letter, name, sound, final in alphabet.LETTERS:
        note = t("alef.atEnd", lang, final=final) if final else ""
        lines.append(f"<b>{letter}</b> — {name_of(letter, name)}, "
                     f"{sound_of(letter, sound)}{note}")

    lines += ["", t("alef.dotHead", lang), ""]
    for shown, name, sound in alphabet.DOTTED:
        lines.append(t("alef.dotLine", lang, shown=shown, name=name,
                       sound=(ae.DOTTED_EN.get(shown) or sound) if en else sound))

    lines += ["", t("alef.niqqudHead", lang), ""]
    for shown, _, sound in alphabet.NIQQUD:
        lines.append(t("alef.niqqudLine", lang, shown=shown,
                       sound=(ae.NIQQUD_EN.get(shown) or sound) if en else sound))

    lines += ["", t("alef.finalNote", lang)]
    send_message(chat_id, "\n".join(lines), alphabet_menu_keyboard(lang))


# ---------- Игровая логика ----------

def keyboard_rows(buttons, per_row=2):
    """Разбивает кнопки на ряды по per_row штук — сетка 2x2 вместо одного
    узкого столбца, площадь тапа на кнопку больше."""
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def send_question(chat_id):
    s = sessions[chat_id]
    lang = s.get("lang", "ru")
    q = build_question(s["pool"], s["used"], s.get("priorities"), lang=lang)
    s["used"].add(q["id"])
    s["current"] = q

    # Нативная (reply) клавиатура вместо inline — кнопки растягиваются на
    # всю ширину экрана и рендерятся крупнее, чем инлайн-кнопки в пузыре
    # сообщения. Сетка 2x2 вместо одного столбца — площадь тапа больше.
    # resize_keyboard НЕ ставим (по умолчанию false) — по документации
    # Telegram именно этот флаг "сжимает" клавиатуру; без него кнопки
    # занимают высоту стандартной системной клавиатуры, то есть выше.
    # one_time_keyboard прячет клавиатуру сразу после тапа.
    idx = s["index"] + 1
    mode = card_mode(s, q)
    is_form = mode in ("past", "present", "future")

    if s.get("anagram"):
        # Буквы вразброс — задача собрать из них слово.
        s["hints"] = 0
        letters = " ".join(scramble(q["correct"], random))
        text = (
            f"{t('q.counter', lang, idx=idx, total=s['total'])}\n"
            f"<b>{q['ru']}</b>\n"
            f"{t('q.letters', lang, letters=letters)}\n\n"
            f"{t('q.anagramHint', lang)}"
        )
        send_message(chat_id, text, {"remove_keyboard": True})
        return

    if s.get("typing"):
        # Вариантов не показываем — ответ нужно вспомнить и написать.
        # Клавиатуру с прошлого раунда убираем, чтобы не мешала набору.
        s["hints"] = 0
        task = t("q.typeForm" if is_form else "q.typeWord", lang)
        text = (
            f"{t('q.counter', lang, idx=idx, total=s['total'])}\n"
            f"<b>{q['ru']}</b>\n{task}.\n\n"
            f"{t('q.typeHint', lang)}"
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
    head = t("q.counter", lang, idx=idx, total=s["total"])
    if mode in ALPHABET_MODES:
        # Подсказка уже сформулирована как вопрос («буква א», «прочитай מָ»)
        text = f"{head}\n<b>{q['ru']}</b>?"
    elif is_form:
        text = f"{head}\n<b>{q['ru']}</b>\n{t('q.whichForm', lang)}"
    else:
        text = f"{head}\n{t('q.howToSay', lang, ru=q['ru'])}"
    send_message(chat_id, text, keyboard)


def start_round(chat_id, mode, cat=None, typing=False, anagram=False, lang="ru"):
    pool, label, modes = round_pool(chat_id, mode, cat, lang)
    if len(pool) < 4:
        # Меньше четырёх карточек — не из чего собрать варианты ответа.
        send_message(
            chat_id,
            t("round.noWeak" if mode == "weak" else "round.tooSmall", lang),
            main_menu_keyboard(lang),
        )
        return
    total = min(ROUND_LEN, len(pool))
    # Приоритеты читаем один раз на раунд, а не на каждый вопрос —
    # лишние обращения к БД внутри раунда не нужны.
    try:
        db.touch_user(chat_id)
        # В смешанном раунде приоритеты не нужны: карточки и так отобраны
        # по числу ошибок, это уже и есть приоритет.
        priorities = {} if mode == "weak" else db.card_priorities(chat_id, mode)
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
        "modes": modes,       # режим по карточке (только в «слабых местах»)
        "label": label,
        # Язык кладём в сессию, а не спрашиваем базу на каждый вопрос:
        # раунд идёт десять сообщений подряд, и менять язык посреди него
        # человек всё равно не станет.
        "lang": lang,
        "hints": 0,
        "streak": 0,          # верных подряд прямо сейчас
        "best_streak": 0,     # лучшая серия за раунд
        "recent": [],         # недавние реплики, чтобы не повторяться
        "last_memory": -9,    # на каком вопросе бот последний раз вспоминал
        "reacted_msg": None,  # на какое сообщение уже повесили реакцию
    }
    due = sum(1 for v in priorities.values() if v >= 2)
    hint = t("round.due", lang, n=min(due, total)) if due else ""
    if anagram:
        how = t("round.anagram", lang)
    elif typing:
        how = t("round.typing", lang)
    else:
        how = ""
    send_message(
        chat_id,
        t("round.start", lang, label=label, total=total,
          qw=plural(total, "n.question", lang), hint=hint, how=how),
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


def card_mode(s, q):
    """Режим карточки. В обычном раунде он один на всех, в «слабых
    местах» — свой у каждой: они собраны из разных режимов."""
    return s.get("modes", {}).get(q["id"], s["mode"])


def lively(chat_id):
    """Включены ли живые реплики. Сбой БД не должен глушить бота."""
    try:
        return db.reactions_enabled(chat_id)
    except Exception:
        return True


def say_verdict(chat_id, s, outcome, answer, message_id=None, before=None,
                extra=None, mode=None):
    """Ответ на попытку: реплика, память о слове, отметка серии.

    Собрано в одном месте, потому что выбор с кнопок, набор руками и
    анаграмма отвечают по-разному, а звучать должны одинаково.
    """
    pool, sep = VERDICT_POOLS[outcome]
    lang = s.get("lang", "ru")
    alive = lively(chat_id)
    # С выключенными реакциями поведение прежнее: одна и та же формулировка.
    phrase = (reactions.pick(pool, s["recent"], random, lang) if alive
              else (pool.get(lang) or pool["ru"])[0])

    lines = [f"{phrase}{sep}{with_reading(answer, mode or s['mode'], lang)}"]
    if extra:
        lines.append(extra)

    # Серия. Описку засчитываем как верный ответ: слово вспомнил,
    # промахнулся по буквам — серию за это обрывать несправедливо.
    scored = outcome in ("correct", "typo")
    s["streak"] = s["streak"] + 1 if scored else 0
    s["best_streak"] = max(s["best_streak"], s["streak"])

    emoji = None
    if alive:
        memory = reactions.memory_line(before, scored, lang)
        if memory and s["index"] - s["last_memory"] >= MEMORY_COOLDOWN:
            lines.append(f"<i>{memory}</i>")
            s["last_memory"] = s["index"]

        event = reactions.streak_event(s["streak"], lang) if scored else None
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


def card_history(chat_id, card_id, mode):
    """История карточки до текущего ответа (для «я это помню»)."""
    try:
        return db.card_history(chat_id, card_id, mode)
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
    mode = card_mode(s, q)
    before = card_history(chat_id, q["id"], mode)

    # Записываем ответ в БД: отсюда берутся и статистика, и расписание
    # повторений. Сбой БД не должен ломать игру, поэтому не роняем раунд.
    try:
        db.record_answer(chat_id, mode, q["id"], is_correct)
        db.award_for_answer(chat_id, is_correct)
    except Exception as e:
        print(f"[handle_answer] не удалось записать ответ: {e}")

    if is_correct:
        s["score"] += 1
    say_verdict(chat_id, s, "correct" if is_correct else "wrong",
                q["correct"], message_id, before, mode=mode)
    maybe_send_voice(chat_id, q["correct"], mode)

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


SPEED_LABELS = {"normal": "voice.normal", "slow": "voice.slow"}


def ask_sample_speed(chat_id, lang="ru"):
    """Спрашивает скорость: образцов много, слать все сразу — каша."""
    if not audio.voice_samples():
        send_message(chat_id, t("voice.missing", lang))
        return

    speeds = audio.sample_speeds()
    if not speeds:
        # старые образцы без пометки скорости — просто отправляем всё
        send_voice_samples(chat_id)
        return

    send_message(
        chat_id,
        f"{t('voice.compare', lang)}\n\n"
        f"{audio.SAMPLE_TEXT}\n\n"
        f"<i>{audio.SAMPLE_TRANSLATION}</i>\n\n"
        f"{t('voice.whichSpeed', lang)}",
        {"inline_keyboard": [[
            {"text": ("🚶 " if sp == "normal" else "🐢 ")
                     + t(SPEED_LABELS[sp], lang),
             "callback_data": f"voices_{sp}"}
            for sp in speeds
        ]]},
    )


def send_voice_samples(chat_id, speed=None, lang="ru"):
    """Один и тот же текст в разных вариантах озвучки."""
    samples = audio.voice_samples(speed=speed)
    if not samples:
        send_message(chat_id, t("voice.missing", lang))
        return

    if speed:
        name = t(SPEED_LABELS[speed], lang) if speed in SPEED_LABELS else speed
        send_message(chat_id, t("voice.chosen", lang, speed=name))
    for name, path in samples:
        audio.send_voice_file(API_URL, chat_id, path, caption=name)




def with_reading(answer, mode, lang="ru"):
    """Добавляет произношение: «מִטְבָּח (митбах)» или «(mitbakh)».

    В курсе алфавита не показываем — там ответ и так уже либо звук, либо
    название буквы, произношение было бы шумом.
    """
    if mode in ALPHABET_MODES:
        return answer
    return f"{answer}{reading_suffix(answer, mode, lang)}"


def reading_suffix(answer, mode, lang="ru"):
    """« (митбах)» — произношение в скобках, если его есть чем показать."""
    if mode in ALPHABET_MODES:
        return ""
    said = reading(answer, lang)
    return f" ({said})" if said else ""


def finish_question(chat_id):
    """Переходит к следующему вопросу или закрывает раунд."""
    s = sessions[chat_id]
    s["index"] += 1
    if s["index"] >= s["total"]:
        db.award_for_round(chat_id, s["score"], s["total"])
        lang = s.get("lang", "ru")
        pct = round(100 * s["score"] / s["total"])
        if lively(chat_id):
            head, emoji = reactions.round_summary(
                s["score"], s["total"], s["best_streak"], lang)
        else:
            head = t("round.result", lang, score=s["score"],
                     total=s["total"], pct=pct)
            emoji = None
        send_message(
            chat_id,
            t("round.again", lang, head=head),
            main_menu_keyboard(lang),
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
        send_message(chat_id, t("q.hint", s.get("lang", "ru"),
                                hint=hint_for(q["correct"], s["hints"])))
        return

    # «пропустить» и «skip» словом — на случай, если человек напишет их
    # вместо команды. Оба языка принимаем всегда: понять просьбу дешевле,
    # чем заставлять вспоминать точное слово.
    if typed.strip().lower() in ("/skip", "пропустить", "skip"):
        mode = card_mode(s, q)
        before = card_history(chat_id, q["id"], mode)
        try:
            db.record_answer(chat_id, mode, q["id"], False)
        except Exception as e:
            print(f"[handle_typed_answer] не удалось записать пропуск: {e}")
        say_verdict(chat_id, s, "skip", q["correct"], message_id, before, mode=mode)
        finish_question(chat_id)
        return

    verdict = check_answer(typed, q["correct"], KNOWN_FORMS.get(card_mode(s, q)))
    # Подсказками пользовался — засчитываем, но в повторениях как неуверенный
    is_correct = verdict in ("exact", "typo") and not s.get("hints")

    mode = card_mode(s, q)
    before = card_history(chat_id, q["id"], mode)
    try:
        db.record_answer(chat_id, mode, q["id"], is_correct)
        db.award_for_answer(chat_id, is_correct)
    except Exception as e:
        print(f"[handle_typed_answer] не удалось записать ответ: {e}")

    outcome = {"exact": "correct", "typo": "typo"}.get(verdict, "wrong")
    if verdict in ("exact", "typo"):
        s["score"] += 1
    # Подсказка — это не провал, но и не чистое попадание: честнее сказать
    # вслух, что слово вернётся, чем молча подсунуть его снова.
    extra = (t("q.hintUsed", s.get("lang", "ru"))
             if verdict == "exact" and s.get("hints") else None)
    say_verdict(chat_id, s, outcome, q["correct"], message_id, before, extra,
                mode=mode)
    maybe_send_voice(chat_id, q["correct"], mode)

    finish_question(chat_id)


# ---------- Слово дня ----------

def send_word_of_day(chat_id, subscribe_hint=True, lang="ru"):
    """Слово дня: перевод, написание и кнопка потренироваться."""
    card = quiz.pick_daily_word(chat_id)
    he = card.he
    try:
        # Отмечаем сразу, а не после отправки: даже если сообщение не
        # уйдёт, повторить это же слово завтра хуже, чем пропустить его.
        # Ключ устойчивый: при смене языка слово не придёт повторно.
        db.record_daily_word(chat_id, card.key())
    except Exception as e:
        print(f"[send_word_of_day] не удалось запомнить слово: {e}")

    try:
        subscribed = db.is_subscribed(chat_id)
    except Exception:
        subscribed = False

    lines = [
        t("word.title", lang),
        "",
        f"<b>{he}</b> — {card.prompt(lang)}",
        t("word.reading", lang, reading=reading(he, lang)),
    ]
    if subscribe_hint:
        lines += ["", t("word.unsubscribe" if subscribed else "word.subscribe", lang)]

    keyboard = {
        "inline_keyboard": [
            [{"text": t("menu.trainWords", lang), "callback_data": "start_vocab"}],
            [{"text": t("menu.toMenu", lang), "callback_data": "main_menu"}],
        ]
    }
    send_message(chat_id, "\n".join(lines), keyboard)
    maybe_send_voice(chat_id, he, "vocab")


# ---------- Статистика ----------

def send_stats(chat_id, lang="ru"):
    """Сводка прогресса: точность, streak, что пора повторить, слабые места."""
    try:
        overall = db.overall_stats(chat_id)
        by_mode = db.stats_by_mode(chat_id)
        weak = db.weak_cards(chat_id, limit=5)
        streak = db.streak_days(chat_id)
        due = db.due_count(chat_id)
    except Exception as e:
        print(f"[send_stats] БД недоступна: {e}")
        send_message(chat_id, t("stats.off", lang))
        return

    if not overall["total"]:
        send_message(chat_id, t("stats.empty", lang))
        return

    pct = round(100 * overall["correct"] / overall["total"])
    lines = [
        t("stats.title", lang),
        "",
        t("stats.total", lang, n=overall["total"]),
        t("stats.correct", lang, n=overall["correct"], pct=pct),
    ]
    if streak:
        lines.append(t("stats.streak", lang, n=streak,
                       word=plural(streak, "n.day", lang)))
    if due:
        lines.append(t("stats.due", lang, n=due))

    if by_mode:
        lines += ["", t("stats.byMode", lang)]
        for mode in LABELS:
            st = by_mode.get(mode)
            if not st:
                continue
            p = round(100 * st["correct"] / st["total"])
            label = quiz.section_label(mode, lang=lang)
            lines.append(f"• {label}: {st['correct']}/{st['total']} ({p}%)")

    if weak:
        lines += ["", t("stats.weak", lang)]
        for w in weak:
            n = w["n_wrong"]
            errors = f"{n} {plural(n, 'n.error', lang)}"
            card = quiz.find_card(w["mode"], w["card_id"])
            # Слово убрали из словаря, а прогресс по нему остался.
            # Показать ключ («food:לחם») нельзя — это машинная строка,
            # человеку она ничего не говорит. Просто пропускаем.
            if not card:
                continue
            # Ответ первым: глаз цепляется за то, что надо выучить,
            # а не за подсказку, которую и так знаешь.
            lines.append(
                f"• <b>{card.he}</b>{reading_suffix(card.he, w['mode'], lang)} — "
                f"{card.prompt(lang)} · {errors}")
        lines.append("")
        lines.append(t("stats.weakNote", lang))

    keyboard = main_menu_keyboard(lang)
    if weak:
        # Видеть свои ошибки мало — до сих пор, чтобы их проработать,
        # надо было запускать обычный раунд и надеяться, что они выпадут.
        keyboard["inline_keyboard"] = (
            [[{"text": t("menu.trainWeak", lang), "callback_data": "pick|weak|"}]]
            + keyboard["inline_keyboard"])

    send_message(chat_id, "\n".join(lines), keyboard)


# ---------- Сводка для владельца ----------

def human_time(seconds):
    """«2 ч 15 мин», «40 мин», «3 мин»."""
    m = int(seconds) // 60
    if m >= 60:
        h, rest = divmod(m, 60)
        return f"{h} ч {rest} мин" if rest else f"{h} ч"
    return f"{m} мин" if m else "меньше минуты"


def send_admin_stats(chat_id):
    """Сводка по всей аудитории. Только владельцу бота.

    Намеренно остаётся по-русски и в messages.py не переносится: её
    видит один человек — тот, чей chat_id стоит в ADMIN_CHAT_ID. Перевод
    добавил бы полсотни строк в словарь ради читателя, которого нет."""
    if not ADMIN_CHAT_ID:
        send_message(
            chat_id,
            "Сводка не настроена.\n\n"
            f"Твой chat_id: <code>{chat_id}</code>\n"
            "Впиши его в <code>.env</code> как <code>ADMIN_CHAT_ID</code> "
            "и перезапусти бота.",
        )
        return
    if str(chat_id) != ADMIN_CHAT_ID:
        # Молча: сообщать, что команда существует, посторонним незачем.
        print(f"[admin] отказано {chat_id}")
        return

    try:
        a = db.audience()
        people = db.engagement()
    except Exception as e:
        print(f"[send_admin_stats] {e}")
        send_message(chat_id, "Сводка недоступна: не читается база.")
        return

    acc = round(100 * a["correct"] / a["answers"]) if a["answers"] else 0
    total_seconds = sum(p["seconds"] for p in people)
    total_sessions = sum(p["sessions"] for p in people)

    lines = [
        "🛠 <b>Сводка</b>", "",
        f"Всего заходило: {a['total']}",
        f"Из них играли: {a['played']}",
        f"Вернулись на второй день: {a['returned']}"
        + (f" из {a['played']}" if a["played"] else ""),
        "",
        f"Активны за сутки: {a['day']}",
        f"За неделю: {a['week']} (новых {a['new_week']})",
        f"За месяц: {a['month']}",
        "",
        f"Ответов: {a['answers']} ({acc}% верных)",
        f"Заходов: {total_sessions}",
        f"Времени в боте: {human_time(total_seconds)}",
    ]

    if people:
        lines += ["", "<b>По людям:</b>"]
        for p in people[:15]:
            mark = " ← ты" if p["chat_id"] == ADMIN_CHAT_ID else ""
            lines.append(
                f"• <code>{p['chat_id']}</code> — {human_time(p['seconds'])}, "
                f"{p['sessions']} зах., {p['days']} дн., {p['answers']} отв.{mark}")
        if len(people) > 15:
            lines.append(f"<i>…и ещё {len(people) - 15}</i>")

    lines += [
        "",
        "<i>Время считается по отметкам ответов: перерыв больше десяти "
        "минут — новый заход. Это оценка, а не секундомер.</i>",
    ]
    send_message(chat_id, "\n".join(lines))


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

        # Язык определяем один раз на сообщение и передаём вниз. Иначе
        # каждая функция ходила бы в базу за одним и тем же ответом.
        lang = user_lang(chat_id, msg.get("from"))
        s = sessions.get(chat_id)
        if s is not None:
            # На это сообщение вешается реакция за серию, а в конце
            # раунда — за итог.
            s["last_msg"] = message_id
        in_typing_round = bool(s and s.get("current") and s.get("typing"))

        if text.startswith("/start"):
            first = (msg.get("from") or {}).get("first_name", "")
            send_message(chat_id,
                         welcome_text(hebrew_name.to_hebrew(first) or first, lang),
                         main_menu_keyboard(lang))
        elif text.startswith("/about") or text.startswith("/help"):
            send_message(chat_id, about_text(lang), main_menu_keyboard(lang))
        elif text.startswith("/quiz"):
            send_message(chat_id, t("ask.today", lang), main_menu_keyboard(lang))
        elif text.startswith("/stats"):
            send_stats(chat_id, lang)
        elif text.startswith("/admin"):
            send_admin_stats(chat_id)
        elif text.startswith("/word"):
            send_word_of_day(chat_id, lang=lang)
        elif text.startswith("/daily_on"):
            db.set_daily_word(chat_id, True)
            send_message(chat_id, t("set.dailyOn", lang))
        elif text.startswith("/daily_off"):
            db.set_daily_word(chat_id, False)
            send_message(chat_id, t("set.dailyOff", lang))
        elif text.startswith("/lang"):
            # Переключатель языка есть в приложении, но человек, который
            # живёт в чате, туда может и не заходить.
            new = "en" if lang == "ru" else "ru"
            db.set_lang(chat_id, new)
            send_message(chat_id, welcome_text(lang=new), main_menu_keyboard(new))
        elif text.startswith("/voices"):
            ask_sample_speed(chat_id, lang)
        elif text.startswith("/voice_on"):
            db.set_voice(chat_id, True)
            send_message(chat_id, t("set.voiceOn", lang))
        elif text.startswith("/voice_off"):
            db.set_voice(chat_id, False)
            send_message(chat_id, t("set.voiceOff", lang))
        elif text.startswith("/reactions_on"):
            db.set_reactions(chat_id, True)
            send_message(chat_id, t("set.reactionsOn", lang))
        elif text.startswith("/reactions_off"):
            db.set_reactions(chat_id, False)
            send_message(chat_id, t("set.reactionsOff", lang))
        elif text.startswith("/speed"):
            slow = not db.slow_voice(chat_id)
            db.set_slow_voice(chat_id, slow)
            send_message(chat_id, t("set.slow" if slow else "set.normal", lang))
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
        lang = user_lang(chat_id, cq.get("from"))

        if data == "main_menu":
            send_message(chat_id, t("ask.today", lang), main_menu_keyboard(lang))
        elif data == "menu|words":
            send_message(chat_id, t("ask.what", lang), words_menu_keyboard(lang))
        elif data == "menu|topics":
            send_message(chat_id, t("ask.topic", lang),
                         category_keyboard(TOPIC_LABELS, "menu|words", lang))
        elif data == "menu|grammar":
            send_message(chat_id, t("ask.grammar", lang),
                         category_keyboard(GRAMMAR_LABELS, "menu|words", lang))
        elif data == "menu|verbs":
            send_message(chat_id, t("ask.verbs", lang), verbs_menu_keyboard(lang))
        elif data.startswith("pick|"):
            # Тема выбрана — остался формат ответа. Раньше формат был
            # отдельной веткой меню и дублировал весь список тем.
            _, mode, cat = data.split("|", 2)
            send_message(chat_id, t("ask.format", lang),
                         format_keyboard(mode, cat, lang))
        elif data.startswith("go|"):
            _, fmt, mode, cat = data.split("|", 3)
            start_round(chat_id, mode, cat or None,
                        typing=(fmt == "type"), anagram=(fmt == "anagram"),
                        lang=lang)
        elif data == "start_vocab":
            # Старая кнопка из «слова дня» — оставляем рабочей.
            start_round(chat_id, "vocab", lang=lang)
        elif data == "word_of_day":
            send_word_of_day(chat_id, lang=lang)
        elif data == "alphabet_menu":
            send_message(chat_id, t("alef.intro", lang),
                         alphabet_menu_keyboard(lang))
        elif data == "alef_table":
            send_alphabet_table(chat_id, lang)
        elif data.startswith("start_alef_"):
            start_round(chat_id, data[len("start_"):], lang=lang)
        elif data.startswith("voices_"):
            send_voice_samples(chat_id, speed=data[len("voices_"):], lang=lang)
        elif data == "show_stats":
            send_stats(chat_id, lang)


@app.route("/")
def health():
    return "Hebrew quiz bot is running."


if __name__ == "__main__":
    app.run(debug=True)
