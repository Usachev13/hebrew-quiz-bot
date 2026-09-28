#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Описание бота: то, что человек видит ДО первого запуска.

Зачем
-----
У свежеоткрытого бота Telegram показывает пустой экран с одной кнопкой
«Запустить». Человек, которому прислали ссылку, не знает ни что это, ни
зачем нажимать. Описание — единственный текст в этот момент, и он либо
объясняет, либо его нет.

Текстов у бота три, и они разные:

1. description — большой текст на пустом экране до первого запуска.
   До 512 знаков. Видит только тот, кто ещё не начинал.
2. short_description — строка в профиле бота и в поиске. До 120 знаков.
   Видят все и всегда.
3. Приветствие на /start — оно живёт в messages.py, здесь его нет:
   его шлёт сам бот, а эти два текста хранит Telegram.

Тексты на двух языках. Telegram показывает их по языку клиента, и
русскоязычный увидит русский, остальные — английский (он ставится без
кода языка, то есть как язык по умолчанию).

Запуск:
    sudo -u botuser venv/bin/python3 tools/set_description.py
    python3 tools/set_description.py --show     # посмотреть нынешние

Токен на экран не попадает — см. tools/webhook_info.py, там объяснено,
почему это отдельный скрипт, а не строчка с curl.
"""

import argparse
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent.parent
load_dotenv(HERE / ".env")

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
API = f"https://api.telegram.org/bot{TOKEN}"

# 512 знаков — предел Telegram. Уложиться надо так, чтобы человек понял
# три вещи: что тут разговаривают, что отвечать можно голосом, и что
# упражнения отдельно.
DESCRIPTION = {
    "ru": (
        "Иврит с нуля — и разговор с первого дня.\n\n"
        "В чате с вами говорят на иврите: скажите שלום голосом или "
        "текстом, и вам ответят, поправят фразу и переведут каждую "
        "реплику. Не знаете как — скажите по-русски, подскажут ивритом.\n\n"
        "В приложении — алфавит с нуля, слова по темам, глаголы во всех "
        "временах и фразы для банка, врача и съёма квартиры. Всё "
        "озвучено живым голосом и показано с ударением. Что даётся "
        "тяжело — возвращается чаще.\n\n"
        "Нажмите «Запустить»."
    ),
    "": (
        "Hebrew from scratch — and conversation from day one.\n\n"
        "In the chat people talk to you in Hebrew: say שלום by voice or "
        "text and you'll get an answer, a correction and a translation "
        "of every line. Don't know how? Say it in English and you'll be "
        "told the Hebrew.\n\n"
        "The app holds the alphabet from scratch, words by topic, verbs "
        "in every tense and phrases for the bank, the doctor and renting "
        "a flat. All voiced by a real voice, all shown with stress. "
        "Whatever is hard comes back more often.\n\n"
        "Press Start."
    ),
}

# 120 знаков. Это строка под именем бота — она должна работать в отрыве
# от всего остального.
SHORT = {
    "ru": "Иврит с нуля и разговор с первого дня: скажите שלום — и вам ответят.",
    "": "Hebrew from scratch, conversation from day one: say שלום and get an answer.",
}

LIMITS = {"description": 512, "short_description": 120}


def call(method, **params):
    r = requests.post(f"{API}/{method}", json=params, timeout=15).json()
    if not r.get("ok"):
        raise RuntimeError(r.get("description", "неизвестная ошибка"))
    return r.get("result")


def show():
    for method, field in (("getMyDescription", "description"),
                          ("getMyShortDescription", "short_description")):
        for lang, label in (("ru", "русский"), ("", "по умолчанию")):
            got = call(method, language_code=lang) or {}
            text = got.get(field, "")
            print(f"— {field}, {label}: {len(text)} знаков")
            print(f"    {text[:200] or '(пусто)'}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true", help="показать нынешние")
    args = ap.parse_args()

    if not TOKEN:
        print("В .env нет TELEGRAM_TOKEN.")
        return 1
    if args.show:
        return show()

    # Длину проверяем сами и до отправки: Telegram на превышение отвечает
    # отказом, но только по одному тексту за раз, и понять, какой именно
    # длинный, по ответу нельзя.
    too_long = []
    for field, texts in (("description", DESCRIPTION), ("short_description", SHORT)):
        for lang, text in texts.items():
            if len(text) > LIMITS[field]:
                too_long.append(f"{field} [{lang or 'по умолчанию'}]: "
                                f"{len(text)} из {LIMITS[field]}")
    if too_long:
        print("Слишком длинно, Telegram не примет:")
        for line in too_long:
            print(f"  {line}")
        return 1

    for lang, text in DESCRIPTION.items():
        call("setMyDescription", description=text, language_code=lang)
        print(f"описание [{lang or 'по умолчанию'}]: {len(text)} знаков — поставлено")
    for lang, text in SHORT.items():
        call("setMyShortDescription", short_description=text, language_code=lang)
        print(f"короткое [{lang or 'по умолчанию'}]: {len(text)} знаков — поставлено")

    # Команды в меню. Оставляем только те, что работают в чате: список
    # команд — это обещание, и упражнения из него ушли вместе с меню.
    commands = {
        "ru": [("talk", "Поговорить на иврите"),
               ("word", "Слово дня"),
               ("speed", "Скорость озвучки"),
               ("lang", "Сменить язык"),
               ("about", "Что внутри")],
        "": [("talk", "Talk in Hebrew"),
             ("word", "Word of the day"),
             ("speed", "Speech rate"),
             ("lang", "Switch language"),
             ("about", "What's inside")],
    }
    for lang, items in commands.items():
        call("setMyCommands",
             commands=[{"command": c, "description": d} for c, d in items],
             language_code=lang)
        print(f"команды [{lang or 'по умолчанию'}]: {len(items)} — поставлены")
    return 0


if __name__ == "__main__":
    sys.exit(main())
