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
from xml.sax.saxutils import escape

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import audio  # noqa: E402
from conjugations import CONJUGATIONS  # noqa: E402
from matching import _full_spelling  # noqa: E402
from translit import to_ktiv_male  # noqa: E402
from words import VOCAB, VERBS  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Провайдер синтеза. Azure — по умолчанию: у него есть голоса, обученные
# именно на иврите (he-IL), а не многоязычные модели, для которых иврит
# побочная возможность. Это как раз и слышно на гласных.
PROVIDER = os.environ.get("TTS_PROVIDER", "azure")

# --- OpenAI ---
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_URL = "https://api.openai.com/v1/audio/speech"
OPENAI_MODEL = os.environ.get("TTS_MODEL", "tts-1")

# --- Azure Speech ---
AZURE_KEY = os.environ.get("AZURE_SPEECH_KEY", "")
AZURE_REGION = os.environ.get("AZURE_SPEECH_REGION", "westeurope")

# Голос по умолчанию для каждого провайдера
DEFAULT_VOICE = {"openai": "nova", "azure": "he-IL-HilaNeural"}
VOICE = os.environ.get("TTS_VOICE") or DEFAULT_VOICE.get(PROVIDER, "nova")

# Темп речи. Для разбора слова на слух медленнее обычно полезнее:
# «-10%» заметно помогает расслышать огласовки. Поддерживает только Azure.
RATE = os.environ.get("TTS_RATE", "-10%")

# С огласовками или без. По умолчанию с огласовками: на слух так
# получилось лучше — модель реже угадывает гласные неверно, хотя текст
# для неё непривычный. Меняется через TTS_TEXT_FORM в .env.
TEXT_FORM = os.environ.get("TTS_TEXT_FORM", "niqqud")

# Цена за миллион символов. У Azure нейроголоса ещё и с бесплатным
# лимитом 500 тыс. символов в месяц — наши ~17 тыс. в него укладываются.
PRICE_PER_1M_CHARS = {"tts-1": 15.0, "tts-1-hd": 30.0, "azure": 16.0}


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


def for_speech(text, form=None):
    """Что именно отправляем в синтезатор.

    niqqud — как в нашем банке, с огласовками (חֻלְצָה). Вариант по
             умолчанию: на слух оказался лучше — огласовки прямо задают
             гласные, и модель реже их выдумывает.
    plain  — «полное написание» без огласовок (חולצה), как иврит пишут
             в жизни. Текст для модели привычнее, но гласные она
             восстанавливает сама и иногда ошибается.

    Единого правильного ответа тут нет: это зависит от модели, поэтому
    режим переключается и сравнивается на слух.
    """
    form = form or TEXT_FORM
    return to_ktiv_male(text) if form == "plain" else text


def synth_openai(text, voice):
    r = requests.post(
        OPENAI_URL,
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={
            "model": OPENAI_MODEL,
            "voice": voice,
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


def synth_azure(text, voice):
    """Azure Speech. Текст передаётся в SSML, поэтому его надо экранировать:
    в наших словах спецсимволов нет, но одна кавычка в будущем словаре
    сломала бы запрос молча."""
    safe = escape(text)
    ssml = (
        "<speak version='1.0' xml:lang='he-IL'>"
        f"<voice name='{voice}'>"
        f"<prosody rate='{RATE}'>{safe}</prosody>"
        "</voice></speak>"
    )
    r = requests.post(
        f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1",
        headers={
            "Ocp-Apim-Subscription-Key": AZURE_KEY,
            "Content-Type": "application/ssml+xml",
            # тот же ogg/opus, что и у OpenAI — Telegram примет как есть
            "X-Microsoft-OutputFormat": "ogg-48khz-16bit-mono-opus",
            "User-Agent": "hebrew-quiz-bot",
        },
        data=ssml.encode("utf-8"),
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
    return r.content


def synth(text, voice=None):
    voice = voice or VOICE
    if PROVIDER == "azure":
        return synth_azure(text, voice)
    return synth_openai(text, voice)


def missing_key():
    """Понятное сообщение, если ключ не настроен."""
    if PROVIDER == "azure" and not AZURE_KEY:
        return ("Не найден AZURE_SPEECH_KEY — добавь его и AZURE_SPEECH_REGION "
                "в .env рядом с ботом.")
    if PROVIDER == "openai" and not OPENAI_KEY:
        return "Не найден OPENAI_API_KEY — добавь его в .env рядом с ботом."
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="озвучить только N штук")
    ap.add_argument("--scope", choices=["all", "words", "forms"], default="all")
    ap.add_argument("--dry-run", action="store_true", help="только оценка, без трат")
    ap.add_argument("--force", action="store_true", help="перегенерировать существующие")
    ap.add_argument("--text-form", choices=["plain", "niqqud"], default=TEXT_FORM,
                    help="что отправлять в синтезатор: с огласовками (по умолчанию) или без")
    ap.add_argument("--only", nargs="*", default=None,
                    help="озвучить только указанные слова (иврит, можно без огласовок)")
    args = ap.parse_args()

    texts = collect(args.scope)

    if args.only:
        # Сверяем по написанию без огласовок, чтобы можно было указать
        # слово так, как оно набирается с клавиатуры.
        wanted = {_full_spelling(w) for w in args.only}
        texts = [t for t in texts if _full_spelling(t) in wanted]
        if not texts:
            print("Ни одно из указанных слов не найдено в банке.")
            return 1

    todo = texts if (args.force or args.only) else [t for t in texts if not audio.has_audio(t)]
    if args.limit:
        todo = todo[: args.limit]

    chars = sum(len(t) for t in todo)
    rate_key = "azure" if PROVIDER == "azure" else OPENAI_MODEL
    price = PRICE_PER_1M_CHARS.get(rate_key, 15.0) * chars / 1_000_000
    print(f"Всего текстов: {len(texts)}, уже озвучено: {len(texts) - len([t for t in texts if not audio.has_audio(t)])}")
    print(f"К озвучке сейчас: {len(todo)} ({chars} символов)")
    details = f"Провайдер {PROVIDER}, голос {VOICE}, текст: {args.text_form}"
    if PROVIDER == "azure":
        details += f", темп {RATE}, регион {AZURE_REGION}"
    print(f"{details}. Ориентировочно: ${price:.2f}")
    if PROVIDER == "azure":
        print("(у Azure 500 тыс. символов в месяц бесплатно — этот объём в них укладывается)")
    if todo:
        example = todo[0]
        print(f"Пример отправляемого текста: {example} -> {for_speech(example, args.text_form)}")

    if args.dry_run:
        print("Пробный расчёт, ничего не потрачено.")
        return 0
    if not todo:
        print("Всё уже озвучено.")
        return 0
    problem = missing_key()
    if problem:
        print(problem)
        return 1

    os.makedirs(audio.AUDIO_DIR, exist_ok=True)
    done = failed = 0
    try:
        for i, text in enumerate(todo, 1):
            try:
                data = synth(for_speech(text, args.text_form))
                with open(audio.audio_path(text), "wb") as f:
                    f.write(data)
                done += 1
            except Exception as e:
                failed += 1
                print(f"  не удалось «{text}»: {e}")
                time.sleep(2)   # скорее всего лимит запросов — подождём
            if i % 25 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}…")
    except KeyboardInterrupt:
        print(f"\nПрервано. Озвучено {done}, файлы сохранены.")
        print("Запусти скрипт снова — продолжит с того же места.")
        return 0

    print(f"Готово: озвучено {done}, ошибок {failed}.")
    print(f"Файлы: {audio.AUDIO_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
