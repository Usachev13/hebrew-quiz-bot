# -*- coding: utf-8 -*-
"""
Образцы голосов: одна и та же ивритская фраза всеми голосами OpenAI.

Слушать английские демо на сайте бесполезно — вопрос в том, как голос
читает именно иврит, а тут они различаются заметно (гортанные ח и ע,
ударения, «р»).

    python3 tools/voice_samples.py

Потом в боте команда /voices пришлёт все образцы голосовыми.
Стоит копейки: ~30 символов на голос.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import audio  # noqa: E402
from generate_audio import synth, for_speech, PROVIDER, missing_key  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SAMPLE_TEXT = audio.SAMPLE_TEXT

# У Azure это голоса, обученные именно на иврите (he-IL), у OpenAI —
# универсальные многоязычные. Поэтому и списки разные.
VOICES_BY_PROVIDER = {
    "azure": ["he-IL-HilaNeural", "he-IL-AvriNeural"],
    "openai": ["alloy", "echo", "fable", "onyx", "nova", "shimmer",
               "ash", "coral", "sage"],
}
VOICES = VOICES_BY_PROVIDER.get(PROVIDER, VOICES_BY_PROVIDER["openai"])

SAMPLES_DIR = os.path.join(audio.AUDIO_DIR, "samples")


def sample_path(voice):
    return os.path.join(SAMPLES_DIR, f"{voice}.ogg")


def main():
    problem = missing_key()
    if problem:
        print(problem)
        return 1

    print(f"Провайдер: {PROVIDER}, голосов к сравнению: {len(VOICES)}")
    os.makedirs(SAMPLES_DIR, exist_ok=True)

    # Образцы озвучиваем ровно так же, как карточки, иначе они не
    # покажут реального звучания.
    spoken = for_speech(SAMPLE_TEXT)
    print(f"Текст для синтеза: {spoken[:60]}…\n")

    made, skipped = [], []
    for voice in VOICES:
        try:
            data = synth(spoken, voice=voice)
            with open(sample_path(voice), "wb") as f:
                f.write(data)
            made.append(voice)
            print(f"  {voice}: готово")
        except Exception as e:
            skipped.append(voice)
            print(f"  {voice}: пропущен ({str(e)[:80]})")

    print(f"\nГотово: {len(made)} голосов -> {SAMPLES_DIR}")
    if skipped:
        print(f"Недоступны для выбранной модели: {', '.join(skipped)}")
    print("Теперь отправь боту /voices, чтобы послушать их в Telegram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
