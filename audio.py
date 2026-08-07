# -*- coding: utf-8 -*-
"""
Озвучка карточек.

Файлы генерируются заранее (см. tools/generate_audio.py) и лежат на
сервере. В рантайме бот ничего не синтезирует: это и бесплатно, и
мгновенно, и не зависит от доступности стороннего API во время урока.

Имя файла — хеш от ивритского текста, чтобы не возиться с огласовками
и направлением письма в именах файлов.
"""

import hashlib
import os

import requests

AUDIO_DIR = os.environ.get(
    "BOT_AUDIO_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio"),
)


def audio_key(text):
    """Стабильное имя файла для ивритского текста."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def audio_path(text):
    return os.path.join(AUDIO_DIR, f"{audio_key(text)}.ogg")


def has_audio(text):
    p = audio_path(text)
    return os.path.exists(p) and os.path.getsize(p) > 0


def send_voice(api_url, chat_id, text, caption=None):
    """Отправляет голосовое с произношением. Молча ничего не делает,
    если файла нет — озвучка не должна ломать урок."""
    path = audio_path(text)
    if not has_audio(text):
        return False
    try:
        with open(path, "rb") as f:
            data = {"chat_id": str(chat_id)}
            if caption:
                data["caption"] = caption
            requests.post(
                f"{api_url}/sendVoice",
                data=data,
                files={"voice": (f"{audio_key(text)}.ogg", f, "audio/ogg")},
                timeout=20,
            )
        return True
    except requests.exceptions.RequestException as e:
        print(f"[send_voice] сетевая ошибка: {e}")
        return False
