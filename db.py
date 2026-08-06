# -*- coding: utf-8 -*-
"""
Хранилище прогресса на SQLite.

Зачем: раньше всё жило в памяти процесса и стиралось при каждом
перезапуске сервера. Без хранилища невозможны ни статистика, ни streak,
ни главное — интервальные повторения (карточки, в которых ошибаешься,
должны попадаться чаще).

Почему SQLite, а не Postgres: у нас один процесс gunicorn на одной
машине, отдельный сервер БД тут — лишняя движущаяся часть. Когда
пользователей станет много и понадобится несколько процессов, схема
переносится в Postgres почти без изменений.
"""

import os
import sqlite3
import threading
from datetime import date, datetime, timedelta

# Файл БД лежит рядом с кодом, но в git не попадает (см. .gitignore).
# Путь можно переопределить через переменную окружения — удобно в тестах.
DB_PATH = os.environ.get(
    "BOT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "progress.db"),
)

# gunicorn работает в несколько потоков, а соединение SQLite нельзя
# использовать из разных потоков одновременно. Держим отдельное
# соединение на поток.
_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    chat_id     TEXT PRIMARY KEY,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL
);

-- Каждый ответ пользователя. Нужен для статистики и разбора ошибок.
CREATE TABLE IF NOT EXISTS answers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     TEXT NOT NULL,
    mode        TEXT NOT NULL,      -- vocab / verbs / past / present / future
    card_id     TEXT NOT NULL,      -- уникальный ключ карточки (подсказка)
    correct     INTEGER NOT NULL,   -- 0/1
    answered_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_answers_chat ON answers(chat_id, answered_at);
CREATE INDEX IF NOT EXISTS idx_answers_card ON answers(chat_id, card_id);

-- Состояние карточки для интервальных повторений (система Лейтнера).
CREATE TABLE IF NOT EXISTS card_state (
    chat_id     TEXT NOT NULL,
    card_id     TEXT NOT NULL,
    mode        TEXT NOT NULL,
    box         INTEGER NOT NULL DEFAULT 1,   -- 1..5, чем выше, тем реже
    due_date    TEXT NOT NULL,                -- когда показать снова
    n_correct   INTEGER NOT NULL DEFAULT 0,
    n_wrong     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, card_id)
);

CREATE INDEX IF NOT EXISTS idx_state_due ON card_state(chat_id, mode, due_date);
"""

# Интервалы системы Лейтнера: сколько дней ждать до следующего показа.
BOX_INTERVALS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 21}
MAX_BOX = 5


def get_conn():
    """Соединение текущего потока (создаётся при первом обращении)."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        # WAL заметно снижает блокировки при параллельных запросах
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn = conn
    return conn


def init_db():
    """Создаёт таблицы, если их ещё нет. Безопасно вызывать при каждом старте."""
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()


def reset_connection():
    """Закрывает соединение потока — нужно в тестах при смене файла БД."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None


# ---------- пользователи ----------

def touch_user(chat_id):
    """Отмечает, что пользователь активен (для streak и статистики)."""
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO users (chat_id, first_seen, last_seen) VALUES (?, ?, ?) "
        "ON CONFLICT(chat_id) DO UPDATE SET last_seen = excluded.last_seen",
        (str(chat_id), now, now),
    )
    conn.commit()


# ---------- запись ответов ----------

def record_answer(chat_id, mode, card_id, correct):
    """Сохраняет ответ и двигает карточку по коробкам Лейтнера.

    Правильный ответ -> карточка уходит в следующую коробку (показывается
    реже). Ошибка -> возвращается в первую (снова часто).
    """
    chat_id = str(chat_id)
    now = datetime.utcnow().isoformat()
    today = date.today()
    conn = get_conn()

    conn.execute(
        "INSERT INTO answers (chat_id, mode, card_id, correct, answered_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (chat_id, mode, card_id, 1 if correct else 0, now),
    )

    row = conn.execute(
        "SELECT box, n_correct, n_wrong FROM card_state WHERE chat_id = ? AND card_id = ?",
        (chat_id, card_id),
    ).fetchone()

    if row is None:
        box = 2 if correct else 1
        n_correct = 1 if correct else 0
        n_wrong = 0 if correct else 1
    else:
        box = min(row["box"] + 1, MAX_BOX) if correct else 1
        n_correct = row["n_correct"] + (1 if correct else 0)
        n_wrong = row["n_wrong"] + (0 if correct else 1)

    due = (today + timedelta(days=BOX_INTERVALS[box])).isoformat()

    conn.execute(
        "INSERT INTO card_state (chat_id, card_id, mode, box, due_date, n_correct, n_wrong) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(chat_id, card_id) DO UPDATE SET "
        "  box = excluded.box, due_date = excluded.due_date, mode = excluded.mode,"
        "  n_correct = excluded.n_correct, n_wrong = excluded.n_wrong",
        (chat_id, card_id, mode, box, due, n_correct, n_wrong),
    )
    conn.commit()


# ---------- выбор карточек для повторения ----------

# Приоритеты выбора карточек. Порядок важен: сначала повторяем то, что
# пора повторить (иначе ошибки не прорабатываются — бот будет бесконечно
# показывать новый материал), и только потом даём новое.
PRIORITY_DUE = 3        # пора повторять (в т.ч. всё, где только что ошибся)
PRIORITY_NEW = 2        # ещё не видел
PRIORITY_WEAK = 1       # ещё рано, но ошибок больше, чем верных
PRIORITY_FRESH = 0      # недавно ответил верно — не срочно


def card_priorities(chat_id, mode):
    """Возвращает {card_id: приоритет} для карточек, которые уже показывались.

    Карточек, которых тут нет, бот ещё не показывал — им назначается
    PRIORITY_NEW на стороне выбора.
    """
    chat_id = str(chat_id)
    today = date.today().isoformat()
    rows = get_conn().execute(
        "SELECT card_id, box, due_date, n_correct, n_wrong "
        "FROM card_state WHERE chat_id = ? AND mode = ?",
        (chat_id, mode),
    ).fetchall()

    priorities = {}
    for r in rows:
        if r["due_date"] <= today:
            priorities[r["card_id"]] = PRIORITY_DUE
        elif r["n_wrong"] > r["n_correct"]:
            priorities[r["card_id"]] = PRIORITY_WEAK
        else:
            priorities[r["card_id"]] = PRIORITY_FRESH
    return priorities


# ---------- статистика ----------

def overall_stats(chat_id):
    """Сводка: сколько всего ответов и общая точность."""
    row = get_conn().execute(
        "SELECT COUNT(*) AS total, COALESCE(SUM(correct), 0) AS correct "
        "FROM answers WHERE chat_id = ?",
        (str(chat_id),),
    ).fetchone()
    return {"total": row["total"], "correct": row["correct"]}


def stats_by_mode(chat_id):
    """Точность отдельно по каждому режиму."""
    rows = get_conn().execute(
        "SELECT mode, COUNT(*) AS total, COALESCE(SUM(correct), 0) AS correct "
        "FROM answers WHERE chat_id = ? GROUP BY mode",
        (str(chat_id),),
    ).fetchall()
    return {r["mode"]: {"total": r["total"], "correct": r["correct"]} for r in rows}


def weak_cards(chat_id, limit=5):
    """Карточки, где больше всего ошибок — «слабые места»."""
    rows = get_conn().execute(
        "SELECT card_id, mode, n_correct, n_wrong FROM card_state "
        "WHERE chat_id = ? AND n_wrong > 0 "
        "ORDER BY n_wrong DESC, n_correct ASC LIMIT ?",
        (str(chat_id), limit),
    ).fetchall()
    return [dict(r) for r in rows]


def streak_days(chat_id):
    """Сколько дней подряд занимался, включая сегодня."""
    rows = get_conn().execute(
        "SELECT DISTINCT DATE(answered_at) AS d FROM answers "
        "WHERE chat_id = ? ORDER BY d DESC",
        (str(chat_id),),
    ).fetchall()
    if not rows:
        return 0

    days = [datetime.fromisoformat(r["d"]).date() for r in rows]
    today = date.today()
    # streak засчитываем, если занимался сегодня или вчера
    if days[0] not in (today, today - timedelta(days=1)):
        return 0

    streak = 1
    for prev, cur in zip(days, days[1:]):
        if (prev - cur).days == 1:
            streak += 1
        else:
            break
    return streak


def due_count(chat_id, mode=None):
    """Сколько карточек ждут повторения сегодня."""
    today = date.today().isoformat()
    if mode:
        row = get_conn().execute(
            "SELECT COUNT(*) AS c FROM card_state "
            "WHERE chat_id = ? AND mode = ? AND due_date <= ?",
            (str(chat_id), mode, today),
        ).fetchone()
    else:
        row = get_conn().execute(
            "SELECT COUNT(*) AS c FROM card_state WHERE chat_id = ? AND due_date <= ?",
            (str(chat_id), today),
        ).fetchone()
    return row["c"]
