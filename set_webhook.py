# -*- coding: utf-8 -*-
"""
Запусти этот файл ОДИН РАЗ после того, как бот задеплоен и веб-приложение
запущено, чтобы сообщить Telegram, куда слать сообщения.

    python3 set_webhook.py
"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Явный путь к .env рядом с этим файлом — как и в bot.py, чтобы скрипт
# подхватывал токен независимо от того, откуда его запускают (systemd
# передаёт переменные через EnvironmentFile, а при ручном запуске по SSH
# их иначе неоткуда взять).
load_dotenv(Path(__file__).resolve().parent / ".env")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "PASTE_YOUR_TOKEN_HERE")

# BOT_DOMAIN — домен, на котором сейчас развёрнут бот. Для VPS задай его
# напрямую в .env, например BOT_DOMAIN=ivrit-trainer.duckdns.org.
# Если не задан — считаем, что бот всё ещё на PythonAnywhere, и собираем
# домен по-старому из PA_USERNAME (обратная совместимость).
BOT_DOMAIN = os.environ.get("BOT_DOMAIN")
if not BOT_DOMAIN:
    PA_USERNAME = os.environ.get("PA_USERNAME", "PASTE_YOUR_PYTHONANYWHERE_USERNAME")
    BOT_DOMAIN = f"{PA_USERNAME}.pythonanywhere.com"

webhook_url = f"https://{BOT_DOMAIN}/webhook/{TELEGRAM_TOKEN}"

API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def safe(text):
    """Прячет токен в том, что уходит на экран.

    Токен намеренно стоит в пути вебхука: так сервер отличает запросы от
    Telegram от чужих. Но печатать этот адрес целиком нельзя.

    Причина не теоретическая. Скрипт запускают по SSH, вывод остаётся в
    прокрутке терминала, а терминал фотографируют и пересылают — именно
    так и выглядит обычная жизнь. Один скриншот этой строки отдаёт токен
    так же полно, как публичный репозиторий, из-за которого бота уже
    однажды переименовали в чужую рекламу.
    """
    if not TELEGRAM_TOKEN or len(TELEGRAM_TOKEN) < 12:
        return text
    return text.replace(TELEGRAM_TOKEN, TELEGRAM_TOKEN[:6] + "…скрыто")


resp = requests.post(API + "/setWebhook", json={"url": webhook_url}, timeout=10)
print("Webhook URL:", safe(webhook_url))
print("Ответ Telegram:", safe(str(resp.json())))

# Кнопка Mini App рядом с полем ввода. Ставится один раз на бота, а не на
# чат, поэтому живёт здесь, а не в самом боте: дёргать этот вызов на
# каждый /start было бы лишним запросом к Telegram в каждом разговоре.
app_url = f"https://{BOT_DOMAIN}/app"
resp = requests.post(
    API + "/setChatMenuButton",
    json={"menu_button": {"type": "web_app", "text": "Открыть",
                          "web_app": {"url": app_url}}},
    timeout=10,
)
print("Mini App:", app_url)
print("Ответ Telegram:", resp.json())
