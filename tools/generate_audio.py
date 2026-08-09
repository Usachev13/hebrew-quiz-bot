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
import re
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
from translit import to_ktiv_male, to_ipa  # noqa: E402
from words import VOCAB, VERBS  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

AZURE_KEY = os.environ.get("AZURE_SPEECH_KEY", "")
AZURE_REGION = os.environ.get("AZURE_SPEECH_REGION", "westeurope")

# Голоса, обученные на иврите: женский и мужской.
VOICE = os.environ.get("TTS_VOICE", "he-IL-HilaNeural")
HEBREW_VOICES = ["he-IL-HilaNeural", "he-IL-AvriNeural"]

# Каждая карточка озвучивается в двух темпах: обычном и медленном.
# Скорость выбирается в самом боте (/speed), поэтому оба файла должны
# существовать заранее — на лету менять темп нельзя.
NORMAL_RATE = os.environ.get("TTS_RATE", "0%")
SLOW_RATE = os.environ.get("TTS_RATE_SLOW", "-25%")
RATE = NORMAL_RATE

# Текст всегда уходит транскрипцией с ударением. Варианты «с огласовками»
# и «без огласовок» проверялись на слух и отброшены: синтезатор в обоих
# случаях ставит ударение по общему правилу и ошибается на целом классе
# слов (бокЕр вместо бОкер), а гласные читает не всегда верно.

# Паузы в режиме ipa. По умолчанию выключены: после того как знаки
# препинания стали выноситься за тег <phoneme>, синтезатор снова видит
# границы фраз и расставляет паузы сам — явные поверх них звучали рвано.
# Включаются значением вида «150ms», если понадобится разделять слова
# сильнее (например, для совсем начинающих).
WORD_BREAK = os.environ.get("TTS_WORD_BREAK", "0ms")
SENTENCE_BREAK = os.environ.get("TTS_SENTENCE_BREAK", "0ms")

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


def ssml_inner(text):
    """Содержимое SSML: транскрипция каждого слова с ударением.

    Тег <phoneme> вешается на каждое слово отдельно — он задаёт чтение
    одного слова, а не всей фразы.
    """
    parts = []          # [(разметка слова, пауза после него), ...]
    for token in text.split(" "):
        # Знаки препинания выносим ЗА тег: внутри <phoneme> они не читаются,
        # синтезатор перестаёт видеть границы предложений и всё сливается
        # в сплошной поток без пауз.
        m = re.match(r"^(.*?)([.,!?;:\"'»)]*)$", token, re.S)
        word, tail = m.group(1), m.group(2)

        ipa = to_ipa(word)
        if ipa:
            shown = escape(to_ktiv_male(word))
            markup = (f"<phoneme alphabet='ipa' ph='{escape(ipa)}'>{shown}</phoneme>"
                      + escape(tail))
        else:
            markup = escape(token)

        # После конца предложения пауза должна быть заметно длиннее,
        # иначе предложения слипаются так же, как слова.
        ends_sentence = any(c in tail for c in ".!?")
        parts.append((markup, SENTENCE_BREAK if ends_sentence else WORD_BREAK))

    out = []
    for i, (markup, pause) in enumerate(parts):
        out.append(markup)
        if i < len(parts) - 1:
            out.append(f'<break time="{pause}"/>' if pause and pause != "0ms" else " ")
    return "".join(out)


def synth(text, voice=None, rate=None, inner=None):
    """Синтез через Azure Speech.

    inner — готовое содержимое SSML (например, с тегами <phoneme>).
    Если не передано, текст экранируется как есть: спецсимволов в наших
    словах нет, но одна кавычка в будущем словаре сломала бы запрос молча.
    """
    body = inner if inner is not None else escape(text)
    ssml = (
        "<speak version='1.0' xml:lang='he-IL'>"
        f"<voice name='{voice or VOICE}'>"
        f"<prosody rate='{rate if rate is not None else RATE}'>{body}</prosody>"
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
    ap.add_argument("--no-slow", action="store_true",
                    help="только обычный темп, без медленного варианта")
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

    # Каждую карточку озвучиваем в двух темпах: переключать скорость на
    # лету нельзя, файлы готовятся заранее. Оба варианта вместе всё равно
    # укладываются в бесплатный лимит.
    speeds = [(NORMAL_RATE, False)] if args.no_slow else [(NORMAL_RATE, False), (SLOW_RATE, True)]

    def pending(t):
        return [(r, s) for r, s in speeds if not audio.has_audio(t, slow=s)]

    todo = texts if (args.force or args.only) else [t for t in texts if pending(t)]
    if args.limit:
        todo = todo[: args.limit]

    jobs = [(t, r, s) for t in todo
            for (r, s) in (speeds if (args.force or args.only) else pending(t))]

    chars = sum(len(t) for t, _, _ in jobs)
    price = PRICE_PER_1M_CHARS * chars / 1_000_000
    ready = len([t for t in texts if not pending(t)])
    print(f"Всего текстов: {len(texts)}, полностью озвучено: {ready}")
    print(f"К озвучке сейчас: {len(todo)} слов, {len(jobs)} файлов ({chars} символов)")
    print(f"Голос {VOICE}, темпы {[r for r, _ in speeds]}, регион {AZURE_REGION}.")
    print(f"Сверх бесплатного лимита это стоило бы ${price:.2f}, "
          f"но 500 тыс. символов в месяц бесплатны — объём в них укладывается.")
    if todo:
        example = todo[0]
        print(f"Пример: {example} -> {ssml_inner(example)[:120]}")

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
        for i, (text, rate, slow) in enumerate(jobs, 1):
            try:
                data = synth(text, rate=rate, inner=ssml_inner(text))
                with open(audio.audio_path(text, slow=slow), "wb") as f:
                    f.write(data)
                done += 1
            except Exception as e:
                failed += 1
                print(f"  не удалось «{text}» ({rate}): {e}")
                time.sleep(2)   # скорее всего лимит запросов — подождём
            if i % 50 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)}…")
    except KeyboardInterrupt:
        print(f"\nПрервано. Озвучено {done}, файлы сохранены.")
        print("Запусти скрипт снова — продолжит с того же места.")
        return 0

    print(f"Готово: озвучено {done}, ошибок {failed}.")
    print(f"Файлы: {audio.AUDIO_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
