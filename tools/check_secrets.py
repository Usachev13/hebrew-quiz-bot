#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Поиск секретов в том, что уходит в git.

Зачем
-----
15 сентября 2026 бота переименовали в рекламу чужого канала: поменяли
имя, описание и аватар. Взлома сервера не было и аккаунт Telegram не
трогали — хватило одного токена, который лежал в `deploy/README.md`
открытым текстом и уехал на публичный GitHub вместе с коммитом про
деплой. Такие строки на GitHub ищут автоматически.

Самое неприятное в этой истории — что заметить её было нечем. `.env`
честно лежал в `.gitignore`, рядом стоял комментарий «так токен не
утечёт на GitHub», и всё выглядело правильным. А настоящий токен в это
время лежал в соседнем файле как «пример из жизни».

Поэтому проверка смотрит не на имена файлов, а на СОДЕРЖИМОЕ: секрет
опознаётся по форме, где бы он ни лежал.

Что считается секретом
----------------------
Токен Telegram узнаётся однозначно: числовой id бота, двоеточие и 35
символов из ограниченного набора. Случайный текст такой формы не
принимает, поэтому ложных срабатываний тут не бывает.

Ключи Azure и OpenAI — длинные строки без словарных слов, и по одному
только виду их от хеша не отличить. Поэтому они ищутся рядом с именем
переменной: `AZURE_SPEECH_KEY=…`, а не «любая длинная строка».

Запуск:
    python3 tools/check_secrets.py          # файлы под контролем git
    python3 tools/check_secrets.py --all    # и вся история коммитов

Выход 1, если что-то найдено. Годится как хук pre-commit.
"""

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

# Токен бота: id, двоеточие, 35 символов. Форма жёсткая — ложных
# срабатываний не даёт.
#
# Границы заданы вручную, а не через \b. Токен часто попадает в текст
# приклеенным к чему-нибудь: «https://api.telegram.org/bot8931…/getMe».
# Между «bot» и цифрами границы слова нет, и с \b такая строка молча
# проходила мимо — а это самый обычный способ утечки: вставил в README
# пример запроса, и готово.
TELEGRAM = re.compile(r"(?<!\d)\d{8,10}:[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])")

# Прочие ключи ищем по имени переменной: сами по себе они неотличимы от
# любой длинной строки, а имя рядом делает находку однозначной.
NAMED = re.compile(
    r"(AZURE_SPEECH_KEY|OPENAI_API_KEY|TELEGRAM_TOKEN|[A-Z_]*SECRET[A-Z_]*|"
    r"[A-Z_]*PASSWORD[A-Z_]*)\s*=\s*([^\s\"'#]{16,})"
)

# Значения-заглушки: они и должны стоять в примерах.
PLACEHOLDER = re.compile(
    r"^(сюда|xxx|your|paste|<|\$|\{|change|placeholder|todo|пример)", re.I)

# Кириллица в значении — верный признак заглушки: «твой_токен_от_BotFather».
# Правило безопасное, а не удобное: ни один настоящий ключ из тех, что
# здесь бывают, кириллицы не содержит — ни токен Telegram, ни ключи
# Azure и OpenAI. Значит пропустить настоящий секрет оно не может.
CYRILLIC = re.compile(r"[А-Яа-яЁё]")


def hide(value):
    """Показываем начало — узнать можно, воспользоваться нельзя."""
    return value[:6] + "…" if len(value) > 6 else "…"


def scan(text, where):
    found = []
    for m in TELEGRAM.finditer(text):
        found.append(f"{where}: токен Telegram {hide(m.group(0))}")
    for m in NAMED.finditer(text):
        name, value = m.group(1), m.group(2)
        if PLACEHOLDER.match(value) or CYRILLIC.search(value):
            continue          # заглушка
        if TELEGRAM.search(value):
            continue          # настоящий токен уже посчитан выше
        found.append(f"{where}: {name} = {hide(value)}")
    return found


def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=HERE,
                         capture_output=True, text=True)
    return [line for line in out.stdout.split("\n") if line]


def check_tracked():
    """Файлы, которые git отслеживает прямо сейчас."""
    bad = []
    for name in tracked_files():
        path = HERE / name
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, IsADirectoryError):
            continue
        bad += scan(text, name)
    return bad


def check_history():
    """Вся история коммитов.

    Отозванный токен в истории безвреден, но знать о нём стоит: если он
    ещё жив, чистка истории не поможет — поможет только отзыв.
    """
    revs = subprocess.run(["git", "rev-list", "--all"], cwd=HERE,
                          capture_output=True, text=True).stdout.split()
    if not revs:
        return []

    # Шаблон для git — отдельный и нарочно проще. `git grep -E` понимает
    # POSIX ERE, а в нём нет ни look-behind, ни look-ahead: шаблон с ними
    # молча ничего не находит, и проверка радостно сообщает «чисто».
    # Поэтому просеиваем грубо здесь, а точно — уже в Python.
    rough = r"[0-9]{8,10}:[A-Za-z0-9_-]{35}"
    out = subprocess.run(["git", "grep", "-I", "-n", "-E", rough] + revs,
                         cwd=HERE, capture_output=True, text=True)
    hits = set()
    for line in out.stdout.split("\n"):
        m = TELEGRAM.search(line)
        if m:
            hits.add(hide(m.group(0)))
    return [f"в истории коммитов: токен {h} — отзовите его, "
            f"чистка истории сама по себе не поможет" for h in sorted(hits)]


def main():
    bad = check_tracked()
    if "--all" in sys.argv:
        bad += check_history()

    if not bad:
        print("✓ секретов в отслеживаемых файлах нет")
        return 0

    print(f"✗ НАЙДЕНЫ СЕКРЕТЫ ({len(bad)}):\n")
    for line in bad:
        print(f"    {line}")
    print("\nЧто делать:")
    print("  1. Отозвать: @BotFather → /mybots → бот → API Token → Revoke.")
    print("     Это единственное, что действительно помогает. Пока токен")
    print("     жив, чистка файлов и истории его не спасает.")
    print("  2. Заменить значение в файле на заглушку.")
    print("  3. Вписать настоящий токен только в .env на сервере.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
