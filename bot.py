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
import quiz
import reactions
from quiz import (
    POOLS, LABELS, TOPIC_LABELS, GRAMMAR_LABELS, ALPHABET_MODES,
    ANSWERS, KNOWN_FORMS, ANAGRAM_MODES, ROUND_LEN, VOCAB_FLAT,
    build_question, round_pool,
)
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

def main_menu_keyboard():
    rows = []
    if WEBAPP_URL:
        rows.append([{"text": "📱 Открыть приложение",
                      "web_app": {"url": WEBAPP_URL}}])
    return {
        "inline_keyboard": rows + [
            [{"text": "📚 Слова и грамматика", "callback_data": "menu|words"}],
            [{"text": "🔤 Алфавит (с нуля)", "callback_data": "alphabet_menu"}],
            [{"text": "🗓 Слово дня", "callback_data": "word_of_day"},
             {"text": "📊 Статистика", "callback_data": "show_stats"}],
        ]
    }


def words_menu_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🗂 По темам", "callback_data": "menu|topics"}],
            [{"text": "✏️ Грамматика", "callback_data": "menu|grammar"}],
            [{"text": "🔤 Глаголы", "callback_data": "menu|verbs"}],
            [{"text": "⚡ Мои слабые места", "callback_data": "pick|weak|"}],
            [{"text": "‹ Назад", "callback_data": "main_menu"}],
        ]
    }


def category_keyboard(labels, back):
    """Список категорий по две в ряд плюс «всё вперемешку»."""
    buttons = [{"text": name, "callback_data": f"pick|vocab|{key}"}
               for key, name in labels.items()]
    rows = keyboard_rows(buttons, per_row=2)
    rows.append([{"text": "🎲 Всё вперемешку", "callback_data": "pick|vocab|"}])
    rows.append([{"text": "‹ Назад", "callback_data": back}])
    return {"inline_keyboard": rows}


def verbs_menu_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🔤 Инфинитивы", "callback_data": "pick|verbs|"}],
            [{"text": "⏪ Прошедшее", "callback_data": "pick|past|"},
             {"text": "▶️ Настоящее", "callback_data": "pick|present|"}],
            [{"text": "⏩ Будущее", "callback_data": "pick|future|"}],
            [{"text": "‹ Назад", "callback_data": "menu|words"}],
        ]
    }


def format_keyboard(mode, cat):
    """Последний шаг: как отвечать."""
    rows = [
        [{"text": "🔘 Выбрать из вариантов", "callback_data": f"go|choice|{mode}|{cat}"}],
        [{"text": "⌨️ Написать самому", "callback_data": f"go|type|{mode}|{cat}"}],
    ]
    if mode in ANAGRAM_MODES:
        rows.append([{"text": "🔡 Собрать из букв", "callback_data": f"go|anagram|{mode}|{cat}"}])
    rows.append([{"text": "‹ Назад", "callback_data": "menu|words"}])
    return {"inline_keyboard": rows}


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


# ---------- Игровая логика ----------

def keyboard_rows(buttons, per_row=2):
    """Разбивает кнопки на ряды по per_row штук — сетка 2x2 вместо одного
    узкого столбца, площадь тапа на кнопку больше."""
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


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
    mode = card_mode(s, q)
    is_form = mode in ("past", "present", "future")

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
    if mode in ALPHABET_MODES:
        # Подсказка уже сформулирована как вопрос («буква א», «прочитай מָ»)
        text = f"Вопрос {idx}/{s['total']}\n<b>{q['ru']}</b>?"
    elif is_form:
        text = f"Вопрос {idx}/{s['total']}\n<b>{q['ru']}</b>\nКакая это форма?"
    else:
        text = f"Вопрос {idx}/{s['total']}\nКак будет «<b>{q['ru']}</b>»?"
    send_message(chat_id, text, keyboard)


def start_round(chat_id, mode, cat=None, typing=False, anagram=False):
    pool, label, modes = round_pool(chat_id, mode, cat)
    if len(pool) < 4:
        # Меньше четырёх карточек — не из чего собрать варианты ответа.
        send_message(
            chat_id,
            "Пока нечего повторять: ошибок слишком мало. Это хорошая новость."
            if mode == "weak" else
            "В этой теме слишком мало слов для раунда.",
            main_menu_keyboard(),
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
        f"Начинаем! Раунд «{label}», {total} вопросов.{hint}{how}",
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
    return s.get("modes", {}).get((q["ru"], q["correct"]), s["mode"])


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
    alive = lively(chat_id)
    # С выключенными реакциями поведение прежнее: одна и та же формулировка.
    phrase = reactions.pick(pool, s["recent"], random) if alive else pool[0]

    lines = [f"{phrase}{sep}{with_reading(answer, mode or s['mode'])}"]
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
    before = card_history(chat_id, q["ru"], mode)

    # Записываем ответ в БД: отсюда берутся и статистика, и расписание
    # повторений. Сбой БД не должен ломать игру, поэтому не роняем раунд.
    try:
        db.record_answer(chat_id, mode, q["ru"], is_correct)
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




def plural(n, one, few, many):
    """«1 ошибка», «2 ошибки», «5 ошибок».

    Мелочь, но «ошибок 1» — ровно та шероховатость, из-за которой текст
    читается как вывод программы, а не как речь.
    """
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def with_reading(answer, mode):
    """Добавляет произношение кириллицей: «מִטְבָּח (митбах)».

    В курсе алфавита не показываем — там ответ и так уже либо звук, либо
    название буквы, произношение было бы шумом.
    """
    if mode in ALPHABET_MODES:
        return answer
    return f"{answer}{reading_suffix(answer, mode)}"


def reading_suffix(answer, mode):
    """« (митбах)» — произношение в скобках, если его есть чем показать."""
    if mode in ALPHABET_MODES:
        return ""
    reading = translit(answer)
    return f" ({reading})" if reading else ""


def finish_question(chat_id):
    """Переходит к следующему вопросу или закрывает раунд."""
    s = sessions[chat_id]
    s["index"] += 1
    if s["index"] >= s["total"]:
        db.award_for_round(chat_id, s["score"], s["total"])
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
        mode = card_mode(s, q)
        before = card_history(chat_id, q["ru"], mode)
        try:
            db.record_answer(chat_id, mode, q["ru"], False)
        except Exception as e:
            print(f"[handle_typed_answer] не удалось записать пропуск: {e}")
        say_verdict(chat_id, s, "skip", q["correct"], message_id, before, mode=mode)
        finish_question(chat_id)
        return

    verdict = check_answer(typed, q["correct"], KNOWN_FORMS.get(card_mode(s, q)))
    # Подсказками пользовался — засчитываем, но в повторениях как неуверенный
    is_correct = verdict in ("exact", "typo") and not s.get("hints")

    mode = card_mode(s, q)
    before = card_history(chat_id, q["ru"], mode)
    try:
        db.record_answer(chat_id, mode, q["ru"], is_correct)
        db.award_for_answer(chat_id, is_correct)
    except Exception as e:
        print(f"[handle_typed_answer] не удалось записать ответ: {e}")

    outcome = {"exact": "correct", "typo": "typo"}.get(verdict, "wrong")
    if verdict in ("exact", "typo"):
        s["score"] += 1
    # Подсказка — это не провал, но и не чистое попадание: честнее сказать
    # вслух, что слово вернётся, чем молча подсунуть его снова.
    extra = ("<i>(с подсказкой — повторим ещё раз)</i>"
             if verdict == "exact" and s.get("hints") else None)
    say_verdict(chat_id, s, outcome, q["correct"], message_id, before, extra,
                mode=mode)
    maybe_send_voice(chat_id, q["correct"], mode)

    finish_question(chat_id)


# ---------- Слово дня ----------

def pick_daily_word(chat_id):
    """Слово дня. По очереди, от самого желанного к запасному варианту:

    1. не приходило как слово дня и ещё не встречалось в раундах — новое;
    2. не приходило как слово дня, хоть и встречалось — напоминание;
    3. приходило дольше всех остальных — круг пошёл заново.

    Важен именно первый фильтр. Раньше бот отбирал только по «не
    встречалось в раундах», а этот запас тает по мере учёбы: на 272
    отвеченных словах из 273 выбор сужается до одного, и оно приходит
    каждый день. Что и случилось.
    """
    try:
        seen = db.seen_cards(chat_id, "vocab")
        sent = db.daily_sent_words(chat_id)
    except Exception as e:
        print(f"[pick_daily_word] БД недоступна: {e}")
        return random.choice(VOCAB_FLAT)

    never_sent = [w for w in VOCAB_FLAT if w[0] not in sent]
    unseen = [w for w in never_sent if w[0] not in seen]
    if unseen:
        return random.choice(unseen)
    if never_sent:
        return random.choice(never_sent)

    # Всё уже присылали — берём то, что было дальше всего по времени.
    oldest = min(sent.values())
    return random.choice([w for w in VOCAB_FLAT if sent.get(w[0]) == oldest])


def send_word_of_day(chat_id, subscribe_hint=True):
    """Слово дня: перевод, написание и кнопка потренироваться."""
    ru, he, _ = pick_daily_word(chat_id)
    try:
        # Отмечаем сразу, а не после отправки: даже если сообщение не
        # уйдёт, повторить это же слово завтра хуже, чем пропустить его.
        db.record_daily_word(chat_id, ru)
    except Exception as e:
        print(f"[send_word_of_day] не удалось запомнить слово: {e}")

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
        lines.append(f"Занимаешься подряд: {streak} "
                     f"{plural(streak, 'день', 'дня', 'дней')}")
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
            n = w["n_wrong"]
            errors = f"{n} {plural(n, 'ошибка', 'ошибки', 'ошибок')}"
            found = ANSWERS.get(w["mode"], {}).get(w["card_id"])
            he = found[0] if found else None
            if he:
                # Ответ первым: глаз цепляется за то, что надо выучить,
                # а не за русскую подсказку, которую и так знаешь.
                lines.append(
                    f"• <b>{he}</b>{reading_suffix(he, w['mode'])} — "
                    f"{w['card_id']} · {errors}")
            else:
                # Карточки из старых версий словаря: подсказка в базе
                # осталась, а слова уже нет — показываем что есть.
                lines.append(f"• {w['card_id']} · {errors}")
        lines.append("")
        lines.append("<i>Эти карточки бот будет показывать чаще.</i>")

    keyboard = main_menu_keyboard()
    if weak:
        # Видеть свои ошибки мало — до сих пор, чтобы их проработать,
        # надо было запускать обычный раунд и надеяться, что они выпадут.
        keyboard["inline_keyboard"] = (
            [[{"text": "⚡ Потренировать эти", "callback_data": "pick|weak|"}]]
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
    """Сводка по всей аудитории. Только владельцу бота."""
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
        elif text.startswith("/admin"):
            send_admin_stats(chat_id)
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

        if data == "main_menu":
            send_message(chat_id, "Что тренируем сегодня?", main_menu_keyboard())
        elif data == "menu|words":
            send_message(chat_id, "Что тренируем?", words_menu_keyboard())
        elif data == "menu|topics":
            send_message(chat_id, "Выбери тему:",
                         category_keyboard(TOPIC_LABELS, "menu|words"))
        elif data == "menu|grammar":
            send_message(chat_id, "Что из грамматики?",
                         category_keyboard(GRAMMAR_LABELS, "menu|words"))
        elif data == "menu|verbs":
            send_message(chat_id, "Глаголы — что тренируем?",
                         verbs_menu_keyboard())
        elif data.startswith("pick|"):
            # Тема выбрана — остался формат ответа. Раньше формат был
            # отдельной веткой меню и дублировал весь список тем.
            _, mode, cat = data.split("|", 2)
            send_message(chat_id, "Как отвечаем?", format_keyboard(mode, cat))
        elif data.startswith("go|"):
            _, fmt, mode, cat = data.split("|", 3)
            start_round(chat_id, mode, cat or None,
                        typing=(fmt == "type"), anagram=(fmt == "anagram"))
        elif data == "start_vocab":
            # Старая кнопка из «слова дня» — оставляем рабочей.
            start_round(chat_id, "vocab")
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
