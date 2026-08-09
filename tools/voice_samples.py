# -*- coding: utf-8 -*-
"""
Сравнение вариантов озвучки: голос × огласовки × скорость.

Слушать демо на сайте бесполезно — вопрос в том, как конкретный голос
читает наш текст. Сравниваются два голоса и две скорости; способ подачи
текста больше не варьируется — транскрипция с ударением победила
остальные варианты по итогам прослушивания.

    python3 tools/voice_samples.py

Потом в боте команда /voices.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import audio  # noqa: E402
from generate_audio import (  # noqa: E402
    synth, ssml_inner, missing_key, HEBREW_VOICES, NORMAL_RATE, SLOW_RATE,
)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SAMPLE_TEXT = audio.SAMPLE_TEXT

VOICE_LABELS = {
    "he-IL-HilaNeural": "Хила (жен.)",
    "he-IL-AvriNeural": "Аври (муж.)",
}

SPEEDS = [
    (NORMAL_RATE, "normal", "обычная"),
    (SLOW_RATE, "slow", "помедленнее"),
]


def main():
    problem = missing_key()
    if problem:
        print(problem)
        return 1

    # Чистим папку: иначе рядом остаются образцы от прошлых прогонов
    # (в том числе от другого провайдера) и путают при сравнении.
    if os.path.isdir(audio.SAMPLES_DIR):
        for old in os.listdir(audio.SAMPLES_DIR):
            os.remove(os.path.join(audio.SAMPLES_DIR, old))
    os.makedirs(audio.SAMPLES_DIR, exist_ok=True)

    manifest = {}
    made = failed = 0

    total = len(HEBREW_VOICES) * len(SPEEDS)
    print(f"Комбинаций: {total} ({len(HEBREW_VOICES)} голоса × "
          f"{len(SPEEDS)} скорости)")
    print(f"Символов: ~{total * len(SAMPLE_TEXT)} — доли процента от бесплатного лимита.\n")

    for voice in HEBREW_VOICES:
        for rate, speed_tag, speed_label in SPEEDS:
            name = f"{voice}__{speed_tag}.ogg"
            caption = f"{VOICE_LABELS.get(voice, voice)} · {speed_label}"
            try:
                data = synth(SAMPLE_TEXT, voice=voice, rate=rate,
                             inner=ssml_inner(SAMPLE_TEXT))
                with open(os.path.join(audio.SAMPLES_DIR, name), "wb") as f:
                    f.write(data)
                # Скорость храним отдельным полем: бот показывает образцы
                # по одной скорости за раз.
                manifest[name] = {"caption": caption, "speed": speed_tag}
                made += 1
                print(f"  ✓ {caption}")
            except Exception as e:
                failed += 1
                print(f"  ✗ {caption}: {str(e)[:100]}")

    # Подписи храним рядом с файлами: разбирать их из имени файла было бы
    # хрупко, а показать в Telegram надо по-человечески.
    if manifest:
        with open(os.path.join(audio.SAMPLES_DIR, "manifest.json"), "w",
                  encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\nГотово: {made} образцов, ошибок {failed}.")
    if made:
        print("Отправь боту /voices, чтобы послушать их в Telegram.")
    return 0 if made else 1


if __name__ == "__main__":
    sys.exit(main())
