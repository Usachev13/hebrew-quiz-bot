# -*- coding: utf-8 -*-
"""
Разовая генерация озвучки через OpenAI TTS.

Запускать вручную: синтез стоит денег, поэтому он не должен происходить
сам по себе. Скрипт возобновляемый — уже готовые файлы пропускаются,
так что его можно прерывать и запускать снова.

Использование:
    # сначала посмотреть, сколько это будет стоить (ничего не тратит)
    python3 tools/generate_audio.py --dry-run

    # проба на 10 словах: послушать, устраивает ли голос
    python3 tools/generate_audio.py --limit 10

    # всё остальное
    python3 tools/generate_audio.py

Ключ берётся из OPENAI_API_KEY в .env рядом с ботом.
"""

import argparse
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import audio  # noqa: E402
from conjugations import CONJUGATIONS  # noqa: E402
from words import VOCAB, VERBS  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_KEY = os.environ.get("OPENAI_API_KEY", "")
API_URL = "https://api.openai.com/v1/audio/speech"

# tts-1 дешевле и для отдельных слов звучит достаточно чисто.
# Голоса: alloy, echo, fable, onyx, nova, shimmer.
MODEL = os.environ.get("TTS_MODEL", "tts-1")
VOICE = os.environ.get("TTS_VOICE", "nova")

PRICE_PER_1M_CHARS = {"tts-1": 15.0, "tts-1-hd": 30.0}


def collect(scope):
    """Тексты для озвучки. Порядок — от самого нужного к менее нужному,
    чтобы при --limit сначала озвучились слова, а не редкие формы."""
    items = []
    if scope in ("all", "words"):
        for cat, pairs in VOCAB.items():
            for ru, he in pairs:
                items.append(he)
        for cat, pairs in VERBS.items():
            for ru, he in pairs:
                items.append(he)
    if scope in ("all", "forms"):
        for root, data in CONJUGATIONS.items():
            for section in ("present", "past", "future"):
                for form in data[section].values():
                    items.append(form)
    # уникальные, порядок сохраняем
    seen = set()
    return [t for t in items if not (t in seen or seen.add(t))]


def synth(text, voice=None):
    r = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": MODEL,
            "voice": voice or VOICE,
            "input": text,
            # opus в контейнере ogg — ровно то, что Telegram ждёт
            # для голосовых сообщений, перекодировать не нужно
            "response_format": "opus",
        },
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
    return r.content


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="озвучить только N штук")
    ap.add_argument("--scope", choices=["all", "words", "forms"], default="all")
    ap.add_argument("--dry-run", action="store_true", help="только оценка, без трат")
    ap.add_argument("--force", action="store_true", help="перегенерировать существующие")
    args = ap.parse_args()

    texts = collect(args.scope)
    todo = texts if args.force else [t for t in texts if not audio.has_audio(t)]
    if args.limit:
        todo = todo[: args.limit]

    chars = sum(len(t) for t in todo)
    price = PRICE_PER_1M_CHARS.get(MODEL, 15.0) * chars / 1_000_000
    print(f"Всего текстов: {len(texts)}, уже озвучено: {len(texts) - len([t for t in texts if not audio.has_audio(t)])}")
    print(f"К озвучке сейчас: {len(todo)} ({chars} символов)")
    print(f"Модель {MODEL}, голос {VOICE}. Ориентировочно: ${price:.2f}")

    if args.dry_run:
        print("Пробный расчёт, ничего не потрачено.")
        return 0
    if not todo:
        print("Всё уже озвучено.")
        return 0
    if not API_KEY:
        print("Не найден OPENAI_API_KEY — добавь его в .env рядом с ботом.")
        return 1

    os.makedirs(audio.AUDIO_DIR, exist_ok=True)
    done = failed = 0
    for i, text in enumerate(todo, 1):
        try:
            data = synth(text)
            with open(audio.audio_path(text), "wb") as f:
                f.write(data)
            done += 1
        except Exception as e:
            failed += 1
            print(f"  не удалось «{text}»: {e}")
            time.sleep(2)   # скорее всего лимит запросов — подождём
        if i % 25 == 0 or i == len(todo):
            print(f"  {i}/{len(todo)}…")

    print(f"Готово: озвучено {done}, ошибок {failed}.")
    print(f"Файлы: {audio.AUDIO_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
