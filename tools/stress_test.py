# -*- coding: utf-8 -*-
"""
Проверка ударения на «сеголатных» словах.

Проблема: в иврите ударение обычно на последнем слоге, но у целого
класса существительных — на предпоследнем: БО́кер, ЛЕ́хем, КЕ́сеф, СЕ́фер.
Синтезатор произносит их «по общему правилу» и ошибается.

В огласовках ударение не записано, поэтому вывести его из текста
нельзя — но, возможно, синтезатор узнаёт слово по своему словарю, если
дать ему обычное написание без огласовок. Проверяется только на слух.

Скрипт озвучивает одни и те же слова тремя способами, чтобы было
слышно, какой работает:
  1. с огласовками — как сейчас;
  2. без огласовок — вдруг сработает словарь модели;
  3. с явной подсказкой ударения через IPA (если Azure её принимает
     для иврита — это и проверяем).

    python3 tools/stress_test.py

Потом в боте команда /stress.
"""

import json
import os
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import audio  # noqa: E402
from generate_audio import AZURE_KEY, AZURE_REGION, VOICE, RATE, missing_key  # noqa: E402
from translit import to_ktiv_male, to_ipa  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

STRESS_DIR = os.path.join(audio.AUDIO_DIR, "stress")

# Слова, на которых синтезатор чаще всего промахивается с ударением
# (заглавной отмечен ударный слог). Транскрипция не хранится рядом —
# она строится тем же кодом, что и для карточек, иначе проверка
# показывала бы не то, что уходит в реальную озвучку.
WORDS = [
    ("בֹּקֶר", "БО-кер"),
    ("לֶחֶם", "ЛЕ-хем"),
    ("כֶּסֶף", "КЕ-сеф"),
    ("סֵפֶר", "СЕ-фер"),
    ("תַּפּוּחַ", "та-ПУ-ах"),
    ("מְדַבֶּרֶת", "меда-БЕ-рет"),
]


def synth_ssml(inner):
    ssml = (
        "<speak version='1.0' xml:lang='he-IL'>"
        f"<voice name='{VOICE}'><prosody rate='{RATE}'>{inner}</prosody></voice>"
        "</speak>"
    )
    r = requests.post(
        f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1",
        headers={
            "Ocp-Apim-Subscription-Key": AZURE_KEY,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "ogg-48khz-16bit-mono-opus",
            "User-Agent": "hebrew-quiz-bot",
        },
        data=ssml.encode("utf-8"),
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
    return r.content


def main():
    problem = missing_key()
    if problem:
        print(problem)
        return 1

    os.makedirs(STRESS_DIR, exist_ok=True)
    manifest = {}
    made = failed = 0

    for word, ru_stress in WORDS:
        plain = to_ktiv_male(word)
        ipa = to_ipa(word)
        variants = [
            ("niqqud", f"{word} — с огласовками", escape(word)),
            ("plain", f"{word} — без огласовок", escape(plain)),
            ("ipa", f"{word} — транскрипция {ipa}",
             f"<phoneme alphabet='ipa' ph='{escape(ipa)}'>{escape(plain)}</phoneme>"),
        ]
        for tag, label, inner in variants:
            name = f"{plain}__{tag}.ogg"
            caption = f"{label}\nдолжно звучать: {ru_stress}"
            try:
                with open(os.path.join(STRESS_DIR, name), "wb") as f:
                    f.write(synth_ssml(inner))
                manifest[name] = caption
                made += 1
                print(f"  ✓ {label}")
            except Exception as e:
                failed += 1
                print(f"  ✗ {label}: {str(e)[:100]}")

    if manifest:
        with open(os.path.join(STRESS_DIR, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\nГотово: {made} образцов, ошибок {failed}.")
    if failed and made:
        print("Часть вариантов не поддерживается — это тоже результат.")
    if made:
        print("Отправь боту /stress, чтобы послушать.")
    return 0 if made else 1


if __name__ == "__main__":
    sys.exit(main())
