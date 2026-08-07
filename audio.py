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


SAMPLES_DIR = os.path.join(AUDIO_DIR, "samples")

# Текст для сравнения голосов. Специально без огласовок — карточки
# озвучиваются так же, и образец должен отражать реальное звучание.
# Подобран из нашей же лексики и так, чтобы звучали спорные места:
# гортанные ח и ע, «р», ש/שׂ, разные типы предложений.
SAMPLE_TEXT = (
    "שלום! קוראים לי דניאל ואני לומד עברית. "
    "אני גר בישראל, וכל בוקר אני שותה קפה עם חבר טוב. "
    "בערב אני הולך לשוק, קונה לחם וירקות, ומשלם בכרטיס. "
    "מחר אני רוצה לנסוע לים ולנוח קצת."
)

SAMPLE_TRANSLATION = (
    "Привет! Меня зовут Даниэль, и я учу иврит. "
    "Я живу в Израиле, и каждое утро пью кофе с хорошим другом. "
    "Вечером иду на рынок, покупаю хлеб и овощи, плачу картой. "
    "Завтра хочу поехать на море и немного отдохнуть."
)


def voice_samples():
    """Готовые образцы голосов: [(имя голоса, путь к файлу), ...]."""
    if not os.path.isdir(SAMPLES_DIR):
        return []
    out = []
    for name in sorted(os.listdir(SAMPLES_DIR)):
        if name.endswith(".ogg"):
            path = os.path.join(SAMPLES_DIR, name)
            if os.path.getsize(path) > 0:
                out.append((name[:-4], path))
    return out


def send_voice_file(api_url, chat_id, path, caption=None):
    """Отправляет конкретный файл голосовым."""
    try:
        with open(path, "rb") as f:
            data = {"chat_id": str(chat_id)}
            if caption:
                data["caption"] = caption
            requests.post(
                f"{api_url}/sendVoice",
                data=data,
                files={"voice": (os.path.basename(path), f, "audio/ogg")},
                timeout=20,
            )
        return True
    except (requests.exceptions.RequestException, OSError) as e:
        print(f"[send_voice_file] {e}")
        return False


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
