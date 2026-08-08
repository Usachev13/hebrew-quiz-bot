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
import json
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

# Текст для сравнения голосов. Хранится с огласовками — как и весь наш
# банк; в синтезатор он уходит в том же виде, что и карточки (см.
# TTS_TEXT_FORM), поэтому образец всегда отражает реальное звучание.
# Подобран из нашей же лексики и так, чтобы звучали спорные места:
# гортанные ח и ע, «р», ש/שׂ, разные типы предложений.
SAMPLE_TEXT = (
    "שָׁלוֹם! קוֹרְאִים לִי דָּנִיֵּאל וַאֲנִי לוֹמֵד עִבְרִית. "
    "אֲנִי גָּר בְּיִשְׂרָאֵל, וְכָל בֹּקֶר אֲנִי שׁוֹתֶה קָפֶה עִם חָבֵר טוֹב. "
    "בָּעֶרֶב אֲנִי הוֹלֵךְ לַשּׁוּק, קוֹנֶה לֶחֶם וִירָקוֹת, וּמְשַׁלֵּם בְּכַרְטִיס. "
    "מָחָר אֲנִי רוֹצֶה לִנְסוֹעַ לַיָּם וְלָנוּחַ קְצָת."
)

SAMPLE_TRANSLATION = (
    "Привет! Меня зовут Даниэль, и я учу иврит. "
    "Я живу в Израиле, и каждое утро пью кофе с хорошим другом. "
    "Вечером иду на рынок, покупаю хлеб и овощи, плачу картой. "
    "Завтра хочу поехать на море и немного отдохнуть."
)


def voice_samples():
    """Готовые образцы: [(подпись, путь к файлу), ...].

    Подписи лежат в manifest.json рядом с файлами — разбирать их из имён
    файлов было бы хрупко, а показать в Telegram надо по-человечески.
    """
    if not os.path.isdir(SAMPLES_DIR):
        return []

    captions = {}
    manifest = os.path.join(SAMPLES_DIR, "manifest.json")
    if os.path.exists(manifest):
        try:
            with open(manifest, encoding="utf-8") as f:
                captions = json.load(f)
        except (ValueError, OSError) as e:
            print(f"[voice_samples] не читается manifest.json: {e}")

    out = []
    for name in sorted(os.listdir(SAMPLES_DIR)):
        if not name.endswith(".ogg"):
            continue
        path = os.path.join(SAMPLES_DIR, name)
        if os.path.getsize(path) > 0:
            out.append((captions.get(name, name[:-4]), path))
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
