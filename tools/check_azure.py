#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка ключа Azure Speech — до того, как запускать озвучку.

Зачем
-----
Когда ключ перестаёт работать, generate_audio.py сообщает об этом
четырьмя строчками «401» посреди прогона, и непонятно главное: ключ
испорчен при правке .env или недействителен сам по себе. Это разные
беды с разным лечением, а отличаются они одним запросом.

Отдельный скрипт ещё и потому, что озвучка — операция с деньгами и
временем: выяснять исправность ключа, уже начав генерацию, поздно.

Что проверяется
---------------
1. Ключ на месте и похож на ключ: 32 знака у старого образца, 84 у
   нового. Другая длина — почти наверняка правка .env руками, при
   которой часть строки стёрлась вместе с соседней.
2. Ключ принимают. Спрашиваем токен — самый дешёвый вызов, который
   ничего не тратит и не создаёт файлов.

Ключ на экран не выводится: только длина и код ответа. Скрипт запускают
по SSH, а терминал фотографируют — см. историю с токеном Telegram в
tools/check_secrets.py.

Запуск:
    sudo -u botuser venv/bin/python3 tools/check_azure.py
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent.parent
load_dotenv(HERE / ".env")

KEY = os.environ.get("AZURE_SPEECH_KEY", "")
REGION = os.environ.get("AZURE_SPEECH_REGION", "")

# Длины, которые Azure выдаёт на самом деле. Значение не в точности, а в
# отличии от «строка порвалась»: 83 или 40 знаков не бывает.
GOOD_LENGTHS = (32, 84)


def main():
    if not KEY:
        print("✗ AZURE_SPEECH_KEY в .env нет.")
        print("  Портал Azure: Speech service -> Keys and Endpoint.")
        return 1
    if not REGION:
        print("✗ AZURE_SPEECH_REGION в .env нет.")
        print("  Регион написан там же, рядом с ключом.")
        return 1

    print(f"ключ:   {len(KEY)} знаков", end="")
    if len(KEY) not in GOOD_LENGTHS:
        print(f"  ⚠ ожидалось {' или '.join(map(str, GOOD_LENGTHS))}")
        print("        Похоже, строка в .env повреждена при правке.")
    else:
        print("  — длина обычная")
    if KEY != KEY.strip() or any(c.isspace() for c in KEY):
        print("        ⚠ внутри или по краям есть пробелы — лишние символы")
    print(f"регион: {REGION}")

    try:
        r = requests.post(
            f"https://{REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken",
            headers={"Ocp-Apim-Subscription-Key": KEY, "Content-Length": "0"},
            timeout=15,
        )
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Не достучаться до Azure: {e}")
        return 1

    if r.status_code == 200:
        print("\n✓ Ключ принят. Озвучку запускать можно.")
        return 0

    print(f"\n✗ Azure ответил {r.status_code}.")
    if r.status_code == 401 and len(KEY) not in GOOD_LENGTHS:
        # Длину мы уже посчитали и она странная — не противоречим себе:
        # сперва чинить строку в .env, а рассуждать о подписке потом.
        print("  Ключ не принят — и длина у него необычная. Сначала")
        print("  восстановите строку в .env целиком из портала Azure,")
        print("  а если и полный ключ не примут, читайте ниже.")
        print("  Причины недействительности, по убыванию:")
    elif r.status_code == 401:
        print("  Ключ не принят. Длина обычная, значит строка не порвана —")
        print("  он недействителен сам по себе. Причины, по убыванию:")
        print("    • ресурс Speech удалён или отключён;")
        print("    • подписка Azure закрыта или бесплатный период кончился;")
        print("    • ключ перевыпущен в портале — возьмите текущий;")
        print(f"    • ключ от ресурса в другом регионе, а здесь «{REGION}»:")
        print("      ключ привязан к региону намертво и в чужом даёт 401.")
    elif r.status_code == 404:
        print(f"  Региона «{REGION}» не существует — опечатка в названии.")
    elif r.status_code == 403:
        print("  Подписка приостановлена или исчерпан лимит.")
    print("\n  Портал: Speech service -> Keys and Endpoint. Там же регион.")
    print("  Пока ключа нет, бот работает: записанная раньше озвучка")
    print("  лежит на диске, без звука останутся только новые слова.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
