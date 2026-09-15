#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Состояние вебхука — без токена на экране.

Зачем отдельный скрипт, а не curl одной строкой
-----------------------------------------------
Очевидная проверка выглядит так:

    curl -s "https://api.telegram.org/bot$TELEGRAM_TOKEN/getWebhookInfo"

и она печатает поле `url`, в котором токен стоит целиком: он намеренно
включён в путь вебхука, чтобы сервер отличал запросы Telegram от чужих.

То есть команда, которой проверяют «всё ли в порядке после утечки»,
сама выкладывает токен в прокрутку терминала. А терминал фотографируют
и пересылают — именно так второй токен этого бота сгорел через двадцать
минут после первого.

Здесь тот же запрос, но вывод разобран и токен закрыт.

Запуск:
    sudo -u botuser venv/bin/python3 tools/webhook_info.py
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent.parent
load_dotenv(HERE / ".env")

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DOMAIN = os.environ.get("BOT_DOMAIN", "")


def hide(text):
    """Убирает токен из любой строки, которая пойдёт на экран."""
    if not text:
        return text
    return str(text).replace(TOKEN, TOKEN[:6] + "…скрыто") if TOKEN else str(text)


def main():
    if not TOKEN:
        print("В .env нет TELEGRAM_TOKEN.")
        return 1

    try:
        r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo",
                         timeout=10).json()
    except requests.exceptions.RequestException as e:
        print(f"Не достучаться до Telegram: {hide(e)}")
        return 1

    if not r.get("ok"):
        # Самая частая причина — токен отозван или неверен.
        print(f"Telegram отказал: {hide(r.get('description', r))}")
        print("Если токен только что отозван — впишите новый в .env.")
        return 1

    info = r["result"]
    url = info.get("url") or ""

    print("Вебхук")
    if not url:
        print("  адрес:   ПУСТО — Telegram никуда не шлёт сообщения,")
        print("           бот не отвечает. Поднять: venv/bin/python3 set_webhook.py")
    else:
        print(f"  адрес:   {hide(url)}")
        # Сверяем домен: чужой адрес означал бы, что сообщения уходят
        # не вам. Сравниваем только домен — путь содержит токен.
        host = url.split("/")[2] if "//" in url else ""
        if DOMAIN and host != DOMAIN:
            print(f"  ⚠ ЧУЖОЙ ДОМЕН: ждали {DOMAIN}, получили {host}.")
            print("    Сообщения пользователей уходят не вам. Отзовите токен.")
        elif DOMAIN:
            print(f"  домен:   {host} — ваш, всё верно")

    print(f"  в очереди: {info.get('pending_update_count', 0)}")
    if info.get("ip_address"):
        print(f"  адрес сервера: {info['ip_address']}")

    err = info.get("last_error_message")
    if err:
        print(f"  ⚠ последняя ошибка доставки: {hide(err)}")
        print("    Telegram не может достучаться до сервера — проверьте,")
        print("    что сервис поднят и Caddy отдаёт HTTPS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
