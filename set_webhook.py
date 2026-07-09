# -*- coding: utf-8 -*-
"""
Запусти этот файл ОДИН РАЗ после того, как бот задеплоен и веб-приложение
запущено, чтобы сообщить Telegram, куда слать сообщения.

    python3 set_webhook.py
"""

import os
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "PASTE_YOUR_TOKEN_HERE")
PA_USERNAME = os.environ.get("PA_USERNAME", "PASTE_YOUR_PYTHONANYWHERE_USERNAME")

webhook_url = f"https://{PA_USERNAME}.pythonanywhere.com/webhook/{TELEGRAM_TOKEN}"

resp = requests.post(
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
    json={"url": webhook_url},
    timeout=10,
)
print("Webhook URL:", webhook_url)
print("Ответ Telegram:", resp.json())
