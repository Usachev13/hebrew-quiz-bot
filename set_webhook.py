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

resp = requests.post(
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
    json={"url": webhook_url},
    timeout=10,
)
print("Webhook URL:", webhook_url)
print("Ответ Telegram:", resp.json())
