# -*- coding: utf-8 -*-
"""
Разовая генерация озвучки через Azure Speech.

Azure выбран потому, что у него есть голоса, обученные именно на иврите
(he-IL), а не многоязычные модели, для которых иврит побочная
возможность — на гласных разница слышна.

Запускать вручную: синтез расходует квоту, поэтому он не должен
происходить сам по себе. Скрипт возобновляемый — уже готовые файлы
пропускаются, так что его можно прерывать и запускать снова.

Использование:
    # сколько будет символов (ничего не тратит)
    python3 tools/generate_audio.py --dry-run

    # проба на 10 словах
    python3 tools/generate_audio.py --limit 10

    # всё остальное
    python3 tools/generate_audio.py

Ключ и регион берутся из AZURE_SPEECH_KEY / AZURE_SPEECH_REGION в .env.
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

AZURE_KEY = os.environ.get("AZURE_SPEECH_KEY", "")
AZURE_REGION = os.environ.get("AZURE_SPEECH_REGION", "westeurope")

# Голоса, обученные на иврите: женский и мужской.
VOICE = os.environ.get("TTS_VOICE", "he-IL-HilaNeural")
HEBREW_VOICES = ["he-IL-HilaNeural", "he-IL-AvriNeural"]

# Темп речи. Медленнее обычно полезнее для разбора слова на слух,
# но это дело вкуса — сравнивается через tools/voice_samples.py.
RATE = os.environ.get("TTS_RATE", "-10%")

# С огласовками или без. По умолчанию с огласовками: они прямо задают
# гласные, и модель реже их выдумывает. Меняется через TTS_TEXT_FORM.
TEXT_FORM = os.environ.get("TTS_TEXT_FORM", "niqqud")

# Нейроголоса Azure: 500 тыс. символов в месяц бесплатно, дальше ~$16
# за миллион. Наши ~17 тыс. укладываются в бесплатный лимит.
PRICE_PER_1M_CHARS = 16.0


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


# Слова, где огласовки сбивают синтезатор, и его лучше не «поправлять».
#
# Причина: камац катан читается как «о» (כָּל = коль), но по написанию он
# неотличим от обычного камаца — нужно знать ударение. Синтезатор этого
# не знает и читает букву в лоб: «каль». Зато без огласовок он узнаёт
# частотное слово по своему словарю и произносит верно.
#
# Поэтому для таких слов отдаём обычное написание даже в режиме niqqud.
FORCE_PLAIN = {"כָּל", "צָהֳרַיִם", "אֲרוּחַת צָהֳרַיִם"}


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
    if text in FORCE_PLAIN:
        return to_ktiv_male(text)
    return to_ktiv_male(text) if form == "plain" else text


def synth(text, voice=None, rate=None):
    """Синтез через Azure Speech.

    Текст идёт внутри SSML, поэтому его обязательно экранировать: сейчас
    спецсимволов в словах нет, но одна кавычка в будущем словаре сломала
    бы запрос молча.
    """
    safe = escape(text)
    ssml = (
        "<speak version='1.0' xml:lang='he-IL'>"
        f"<voice name='{voice or VOICE}'>"
        f"<prosody rate='{rate if rate is not None else RATE}'>{safe}</prosody>"
        "</voice></speak>"
    )
    r = requests.post(
        f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1",
        headers={
            "Ocp-Apim-Subscription-Key": AZURE_KEY,
            "Content-Type": "application/ssml+xml",
            # ogg/opus — ровно то, что Telegram ждёт для голосовых
            # сообщений, перекодировывать не нужно
            "X-Microsoft-OutputFormat": "ogg-48khz-16bit-mono-opus",
            "User-Agent": "hebrew-quiz-bot",
        },
        data=ssml.encode("utf-8"),
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
    return r.content


def missing_key():
    """Понятное сообщение, если ключ не настроен."""
    if not AZURE_KEY:
        return ("Не найден AZURE_SPEECH_KEY — добавь его и AZURE_SPEECH_REGION "
                "в .env рядом с ботом.")
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
    price = PRICE_PER_1M_CHARS * chars / 1_000_000
    print(f"Всего текстов: {len(texts)}, уже озвучено: {len(texts) - len([t for t in texts if not audio.has_audio(t)])}")
    print(f"К озвучке сейчас: {len(todo)} ({chars} символов)")
    print(f"Голос {VOICE}, темп {RATE}, текст: {args.text_form}, регион {AZURE_REGION}.")
    print(f"Сверх бесплатного лимита это стоило бы ${price:.2f}, "
          f"но 500 тыс. символов в месяц бесплатны — объём в них укладывается.")
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
