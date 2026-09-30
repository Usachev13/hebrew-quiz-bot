#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Живая проверка разговора: кто выбран и отвечает ли он.

Зачем отдельный скрипт
----------------------
Настройка разговора — единственное место, где всё может выглядеть
правильно и не работать. В .env этого проекта уже лежал OPENAI_API_KEY
от старых опытов с озвучкой; человек, вписавший рядом бесплатный ключ
Google, получал отказ авторизации от OpenAI — при совершенно верных
настройках. Понять это по журналу бота почти нельзя.

Скрипт отвечает на три вопроса по порядку: какие ключи вообще есть, кто
из них выбран и почему, и отвечает ли он на настоящий запрос. Последнее
стоит долей копейки — это одна короткая реплика.

Ключи на экран не попадают: печатается только «есть/нет». Почему это
важно, объяснено в tools/webhook_info.py.

Запуск:
    sudo -u botuser venv/bin/python3 tools/check_dialog_key.py
    sudo -u botuser venv/bin/python3 tools/check_dialog_key.py --no-call
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent.parent
load_dotenv(HERE / ".env")
sys.path.insert(0, str(HERE))

import dialog  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-call", action="store_true",
                    help="не обращаться к модели, только настройки")
    ap.add_argument("--models", action="store_true",
                    help="перечислить модели, доступные ключу Google")
    args = ap.parse_args()

    if args.models:
        if not dialog.GOOGLE_KEY:
            print("Ключа GOOGLE_API_KEY в .env нет.")
            return 1
        try:
            names = dialog.google_models()
        except Exception as e:                               # noqa: BLE001
            print(f"Не удалось спросить: {e}")
            return 1
        print(f"Моделей, заявленных как доступные: {len(names)}\n")
        for n in names:
            print(f"  {n}")
        print("\nЗаявлены — не значит работают: ключ может быть ограничен, "
              "а модель доступна только на платном уровне. Проверять "
              "настоящим запросом, вписав имя в DIALOG_MODEL_GOOGLE.")
        return 0

    print("Ключи в .env:")
    for name, getter in dialog.KEYS.items():
        key = getter()
        mark = f"есть ({len(key)} знаков)" if key else "нет"
        print(f"  {name:10} {mark}")

    named = os.environ.get("DIALOG_PROVIDER", "").strip().lower()
    print(f"\nDIALOG_PROVIDER: {named or '(не задан)'}")

    chosen = dialog.provider()
    if not chosen:
        print(f"\n✗ Разговор недоступен. {dialog.why_unavailable()}")
        return 1

    model = {"anthropic": dialog.ANTHROPIC_MODEL,
             "openai": dialog.OPENAI_MODEL,
             "google": dialog.GOOGLE_MODEL}[chosen]
    print(f"Выбран: {chosen}, модель {model}")
    if chosen == "openai":
        print(f"Адрес:  {dialog.OPENAI_BASE}")
    if not named and sum(1 for g in dialog.KEYS.values() if g()) > 1:
        print("\n⚠️  Ключей несколько, а DIALOG_PROVIDER не задан — взят "
              "первый по порядку. Если нужен другой, назовите его прямо.")

    if args.no_call:
        return 0

    print("\nСпрашиваю у модели «שלום»…")
    try:
        res = dialog.reply([], "שלום", gender="m", lang="ru")
    except Exception as e:                                   # noqa: BLE001
        # Ключ мог попасть в текст ошибки (некоторые библиотеки
        # печатают URL с параметрами) — на всякий случай вычищаем.
        text = str(e)
        for getter in dialog.KEYS.values():
            if getter():
                text = text.replace(getter(), "…ключ скрыт…")
        print(f"✗ Не ответил: {text[:300]}")
        print("\nЧастые причины: на счету нет средств; ключ от другого "
              "сервиса; не задан OPENAI_BASE_URL для Groq или OpenRouter; "
              "имя модели не то, что у этого поставщика.")
        return 1

    print(f"  иврит:   {res['he']}")
    print(f"  перевод: {res['ru']}")
    print(f"  токены:  {res['usage'][0]} на вход, {res['usage'][1]} на выход")
    if not res["ok"]:
        print("\n⚠️  Огласовки не прошли формальные правила — они сняты, "
              "транскрипции не будет. Один такой ответ ничего не значит; "
              "если их много, модель для иврита не годится.")
    else:
        print("\n✓ Разговор работает.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
