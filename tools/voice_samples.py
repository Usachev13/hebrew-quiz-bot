# -*- coding: utf-8 -*-
"""
Сравнение вариантов озвучки: голос × огласовки × скорость.

Слушать демо на сайте бесполезно — вопрос в том, как конкретный голос
читает наш текст. А ещё два решения, которые заранее не очевидны:

  • отдавать в синтезатор текст с огласовками или без. С огласовками
    гласные заданы явно, но текст для модели непривычный; без огласовок
    наоборот. Что лучше — зависит от модели, это надо слышать.
  • обычная скорость или помедленнее. Медленнее легче разобрать по
    звукам, но звучит неестественно.

Скрипт генерирует все комбинации и подписывает их, чтобы в Telegram
было понятно, где что.

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
from generate_audio import synth, for_speech, missing_key, HEBREW_VOICES  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SAMPLE_TEXT = audio.SAMPLE_TEXT

VOICE_LABELS = {
    "he-IL-HilaNeural": "Хила (жен.)",
    "he-IL-AvriNeural": "Аври (муж.)",
}

FORMS = [
    ("niqqud", "с огласовками"),
    ("plain", "без огласовок"),
]

RATES = [
    ("0%", "обычная скорость"),
    ("-15%", "помедленнее"),
]


def main():
    problem = missing_key()
    if problem:
        print(problem)
        return 1

    os.makedirs(audio.SAMPLES_DIR, exist_ok=True)
    manifest = {}
    made = failed = 0

    total = len(HEBREW_VOICES) * len(FORMS) * len(RATES)
    print(f"Комбинаций: {total} "
          f"({len(HEBREW_VOICES)} голоса × {len(FORMS)} формы текста × {len(RATES)} скорости)")
    print(f"Символов: ~{total * len(SAMPLE_TEXT)} — это доли процента от "
          f"бесплатного лимита.\n")

    for voice in HEBREW_VOICES:
        for form, form_label in FORMS:
            for rate, rate_label in RATES:
                name = f"{voice}__{form}__{rate.replace('%','').replace('-','m')}.ogg"
                caption = f"{VOICE_LABELS.get(voice, voice)} · {form_label} · {rate_label}"
                try:
                    data = synth(for_speech(SAMPLE_TEXT, form), voice=voice, rate=rate)
                    with open(os.path.join(audio.SAMPLES_DIR, name), "wb") as f:
                        f.write(data)
                    manifest[name] = caption
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
