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
    -- Режим ОБЯЗАН входить в ключ. Подсказка карточки складывается из
    -- глагола и лица («писать (לִכְתּוֹב) — я»), а лица в прошедшем и
    -- будущем называются одинаково — значит 388 подсказок совпадают
    -- дословно. Без режима в ключе прошедшее и будущее делят одну
    -- строку: ответ по одному времени переписывал коробку Лейтнера
    -- другому, и форма молча выпадала из повторений.
    PRIMARY KEY (chat_id, card_id, mode)
);

CREATE INDEX IF NOT EXISTS idx_state_due ON card_state(chat_id, mode, due_date);

-- «Слово дня»: кому шлём и когда отправляли в последний раз.
-- last_sent защищает от повторной отправки, если задача по расписанию
-- вдруг запустится дважды за день.
CREATE TABLE IF NOT EXISTS daily_word (
    chat_id     TEXT PRIMARY KEY,
    subscribed  INTEGER NOT NULL DEFAULT 1,
    last_sent   TEXT
);

-- Какие слова уже приходили как «слово дня». Раньше бот помнил только
-- дату последней отправки, но не само слово, а выбирал из тех, что ещё
-- не встречались в раундах. По мере учёбы этот запас тает, и под конец
-- бот присылал одно и то же слово каждый день.
CREATE TABLE IF NOT EXISTS daily_sent (
    chat_id     TEXT NOT NULL,
    card_id     TEXT NOT NULL,
    sent_on     TEXT NOT NULL,
    PRIMARY KEY (chat_id, card_id)
);

-- Настройки пользователя. Пока одна: присылать ли произношение голосом.
CREATE TABLE IF NOT EXISTS prefs (
    chat_id     TEXT PRIMARY KEY,
    voice       INTEGER NOT NULL DEFAULT 1,
    slow_voice  INTEGER NOT NULL DEFAULT 0,
    reactions   INTEGER NOT NULL DEFAULT 1
);

-- Идентификаторы уже загруженных в Telegram голосовых. Загрузка файла
-- занимает заметное время, а по file_id то же аудио уходит мгновенно.
-- Ключ включает размер и время правки файла, поэтому после
-- перегенерации озвучки старая запись просто перестаёт совпадать.
CREATE TABLE IF NOT EXISTS voice_files (
    file_key    TEXT PRIMARY KEY,
    file_id     TEXT NOT NULL,
    saved_at    TEXT NOT NULL
);
"""

# Столбцы, которые появились позже схемы. SQLite не умеет
# ADD COLUMN IF NOT EXISTS, поэтому проверяем сами — иначе у тех, у кого
# база уже создана, новые настройки молча не заработают.
LATER_COLUMNS = [
    ("prefs", "slow_voice", "INTEGER NOT NULL DEFAULT 0"),
    ("prefs", "reactions", "INTEGER NOT NULL DEFAULT 1"),
]

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


def _migrate_card_state_key(conn):
    """Добавляет mode в первичный ключ card_state.

    SQLite не умеет менять первичный ключ на месте — таблицу приходится
    пересобирать. Делается один раз: если mode уже в ключе, выходим.

    Уже слипшиеся строки разделить невозможно — данные о том, какому
    времени принадлежал прогресс, потеряны безвозвратно. Оставляем как
    есть: дальше расхождение просто перестанет накапливаться.
    """
    info = list(conn.execute("PRAGMA table_info(card_state)"))
    if not info:
        return
    if any(r["name"] == "mode" and r["pk"] for r in info):
        return

    conn.executescript("""
        CREATE TABLE card_state_new (
            chat_id     TEXT NOT NULL,
            card_id     TEXT NOT NULL,
            mode        TEXT NOT NULL,
            box         INTEGER NOT NULL DEFAULT 1,
            due_date    TEXT NOT NULL,
            n_correct   INTEGER NOT NULL DEFAULT 0,
            n_wrong     INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (chat_id, card_id, mode)
        );
        INSERT OR IGNORE INTO card_state_new
            SELECT chat_id, card_id, mode, box, due_date, n_correct, n_wrong
            FROM card_state;
        DROP TABLE card_state;
        ALTER TABLE card_state_new RENAME TO card_state;
        CREATE INDEX IF NOT EXISTS idx_state_due
            ON card_state(chat_id, mode, due_date);
    """)
    print("[db] card_state пересобрана: режим добавлен в первичный ключ")


def init_db():
    """Создаёт таблицы, если их ещё нет. Безопасно вызывать при каждом старте."""
    conn = get_conn()
    conn.executescript(SCHEMA)
    for table, column, decl in LATER_COLUMNS:
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
    _migrate_card_state_key(conn)
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
        "SELECT box, n_correct, n_wrong FROM card_state "
        "WHERE chat_id = ? AND card_id = ? AND mode = ?",
        (chat_id, card_id, mode),
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
        "ON CONFLICT(chat_id, card_id, mode) DO UPDATE SET "
        "  box = excluded.box, due_date = excluded.due_date,"
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

def card_history(chat_id, card_id, mode):
    """Что мы знаем про карточку ДО текущего ответа.

    Вызывать строго перед record_answer: она обновляет счётчики, и после
    неё «сколько раз ты на этом спотыкался» уже включает текущий раз.
    None — карточка встретилась впервые.
    """
    row = get_conn().execute(
        "SELECT box, n_correct, n_wrong FROM card_state "
        "WHERE chat_id = ? AND card_id = ? AND mode = ?",
        (str(chat_id), card_id, mode),
    ).fetchone()
    return dict(row) if row else None


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


# ---------- настройки ----------

def set_voice(chat_id, enabled):
    conn = get_conn()
    conn.execute(
        "INSERT INTO prefs (chat_id, voice) VALUES (?, ?) "
        "ON CONFLICT(chat_id) DO UPDATE SET voice = excluded.voice",
        (str(chat_id), 1 if enabled else 0),
    )
    conn.commit()


def voice_enabled(chat_id):
    """По умолчанию озвучка включена — ради неё всё и делалось."""
    row = get_conn().execute(
        "SELECT voice FROM prefs WHERE chat_id = ?", (str(chat_id),)
    ).fetchone()
    return True if row is None else bool(row["voice"])


def set_slow_voice(chat_id, slow):
    conn = get_conn()
    conn.execute(
        "INSERT INTO prefs (chat_id, slow_voice) VALUES (?, ?) "
        "ON CONFLICT(chat_id) DO UPDATE SET slow_voice = excluded.slow_voice",
        (str(chat_id), 1 if slow else 0),
    )
    conn.commit()


def slow_voice(chat_id):
    """Медленная озвучка. По умолчанию обычная скорость."""
    row = get_conn().execute(
        "SELECT slow_voice FROM prefs WHERE chat_id = ?", (str(chat_id),)
    ).fetchone()
    return bool(row["slow_voice"]) if row else False


def set_reactions(chat_id, enabled):
    conn = get_conn()
    conn.execute(
        "INSERT INTO prefs (chat_id, reactions) VALUES (?, ?) "
        "ON CONFLICT(chat_id) DO UPDATE SET reactions = excluded.reactions",
        (str(chat_id), 1 if enabled else 0),
    )
    conn.commit()


def reactions_enabled(chat_id):
    """Живые реплики и отметки серий. По умолчанию включены."""
    row = get_conn().execute(
        "SELECT reactions FROM prefs WHERE chat_id = ?", (str(chat_id),)
    ).fetchone()
    return True if row is None else bool(row["reactions"])


# ---------- слово дня ----------

# ---------- сводка для владельца бота ----------
#
# Времени в боте мы не пишем: считать секунды в вебхуке нечем — он живёт
# от сообщения до сообщения и не знает, ушёл человек или задумался.
# Зато у каждого ответа есть отметка времени, и по ним время
# восстанавливается: подряд идущие ответы с паузой меньше SESSION_GAP —
# один заход. Пауза больше — человек ушёл и вернулся, это уже новый.
#
# Это оценка, а не секундомер: последний ответ в заходе засчитывается
# как SESSION_TAIL секунд, потому что сколько человек смотрел на экран
# после него, мы знать не можем.
SESSION_GAP = 600        # 10 минут
SESSION_TAIL = 20        # сколько «стоит» одиночный ответ

ENGAGEMENT_SQL = """
WITH ordered AS (
    -- Разницу берём в целых секундах через strftime('%s'), а не через
    -- julianday: julianday возвращает дробные сутки, и на сотне ответов
    -- накапливается погрешность в пару секунд.
    SELECT chat_id, answered_at,
           CAST(strftime('%s', answered_at) AS INTEGER)
           - CAST(strftime('%s', LAG(answered_at) OVER (PARTITION BY chat_id
                                                        ORDER BY answered_at))
                  AS INTEGER) AS gap
    FROM answers
),
marked AS (
    SELECT chat_id,
           CASE WHEN gap IS NULL OR gap > ? THEN 1 ELSE 0 END AS new_session,
           CASE WHEN gap IS NULL OR gap > ? THEN ? ELSE gap END AS spent,
           answered_at
    FROM ordered
)
SELECT chat_id,
       COUNT(*)                              AS answers,
       SUM(new_session)                      AS sessions,
       SUM(spent)                            AS seconds,
       COUNT(DISTINCT date(answered_at))     AS days,
       MIN(answered_at)                      AS first_answer,
       MAX(answered_at)                      AS last_answer
FROM marked
GROUP BY chat_id
"""


def engagement(gap=SESSION_GAP, tail=SESSION_TAIL):
    """По каждому, кто хоть раз отвечал: заходы, время, дни, ответы."""
    rows = get_conn().execute(ENGAGEMENT_SQL, (gap, gap, tail)).fetchall()
    return sorted((dict(r) for r in rows),
                  key=lambda r: r["seconds"], reverse=True)


def audience():
    """Сводка по аудитории: сколько всего и сколько живых."""
    q = lambda sql: get_conn().execute(sql).fetchone()[0]
    return {
        "total": q("SELECT COUNT(*) FROM users"),
        "played": q("SELECT COUNT(DISTINCT chat_id) FROM answers"),
        "day": q("SELECT COUNT(*) FROM users WHERE last_seen >= date('now','-1 day')"),
        "week": q("SELECT COUNT(*) FROM users WHERE last_seen >= date('now','-7 day')"),
        "month": q("SELECT COUNT(*) FROM users WHERE last_seen >= date('now','-30 day')"),
        "new_week": q("SELECT COUNT(*) FROM users WHERE first_seen >= date('now','-7 day')"),
        "answers": q("SELECT COUNT(*) FROM answers"),
        "correct": q("SELECT COALESCE(SUM(correct),0) FROM answers"),
        # Вернулся хотя бы на второй день — самая честная метрика на старте:
        # показывает, зацепил продукт или человек посмотрел и ушёл.
        "returned": q("SELECT COUNT(*) FROM (SELECT chat_id FROM answers "
                      "GROUP BY chat_id HAVING COUNT(DISTINCT date(answered_at)) > 1)"),
    }


# ---------- кэш загруженных голосовых ----------

def voice_file_id(file_key):
    """Идентификатор уже загруженного файла или None."""
    if not file_key:
        return None
    row = get_conn().execute(
        "SELECT file_id FROM voice_files WHERE file_key = ?", (file_key,)
    ).fetchone()
    return row["file_id"] if row else None


def save_voice_file_id(file_key, file_id):
    if not file_key or not file_id:
        return
    conn = get_conn()
    conn.execute(
        "INSERT INTO voice_files (file_key, file_id, saved_at) VALUES (?, ?, ?) "
        "ON CONFLICT(file_key) DO UPDATE SET file_id = excluded.file_id, "
        "saved_at = excluded.saved_at",
        (file_key, file_id, datetime.utcnow().isoformat()),
    )
    conn.commit()


# ---------- слово дня ----------

def set_daily_word(chat_id, subscribed):
    """Подписывает или отписывает от ежедневного слова."""
    conn = get_conn()
    conn.execute(
        "INSERT INTO daily_word (chat_id, subscribed) VALUES (?, ?) "
        "ON CONFLICT(chat_id) DO UPDATE SET subscribed = excluded.subscribed",
        (str(chat_id), 1 if subscribed else 0),
    )
    conn.commit()


def is_subscribed(chat_id):
    row = get_conn().execute(
        "SELECT subscribed FROM daily_word WHERE chat_id = ?", (str(chat_id),)
    ).fetchone()
    return bool(row and row["subscribed"])


def daily_word_recipients():
    """Кому сегодня ещё не отправляли слово дня."""
    today = date.today().isoformat()
    rows = get_conn().execute(
        "SELECT chat_id FROM daily_word "
        "WHERE subscribed = 1 AND (last_sent IS NULL OR last_sent < ?)",
        (today,),
    ).fetchall()
    return [r["chat_id"] for r in rows]


def daily_sent_words(chat_id):
    """{слово: когда присылали}. Пустой словарь — ещё ничего не слали."""
    rows = get_conn().execute(
        "SELECT card_id, sent_on FROM daily_sent WHERE chat_id = ?",
        (str(chat_id),),
    ).fetchall()
    return {r["card_id"]: r["sent_on"] for r in rows}


def record_daily_word(chat_id, card_id):
    """Запоминает, что слово уже приходило (и когда в последний раз)."""
    conn = get_conn()
    conn.execute(
        "INSERT INTO daily_sent (chat_id, card_id, sent_on) VALUES (?, ?, ?) "
        "ON CONFLICT(chat_id, card_id) DO UPDATE SET sent_on = excluded.sent_on",
        (str(chat_id), card_id, date.today().isoformat()),
    )
    conn.commit()


def mark_daily_word_sent(chat_id):
    conn = get_conn()
    conn.execute(
        "UPDATE daily_word SET last_sent = ? WHERE chat_id = ?",
        (date.today().isoformat(), str(chat_id)),
    )
    conn.commit()


def seen_cards(chat_id, mode):
    """Карточки, которые пользователь уже видел (для выбора нового слова)."""
    rows = get_conn().execute(
        "SELECT card_id FROM card_state WHERE chat_id = ? AND mode = ?",
        (str(chat_id), mode),
    ).fetchall()
    return {r["card_id"] for r in rows}


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
