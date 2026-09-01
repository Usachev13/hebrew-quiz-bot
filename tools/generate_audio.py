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
import json
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


SCOPES = ["all", "words", "forms", "present", "past", "future", "phrases"]


def collect(scope):
    """Тексты для озвучки. Порядок — от самого нужного к менее нужному,
    чтобы при --limit сначала озвучились слова, а не редкие формы."""
    items = []
    # Разговорные фразы озвучиваем первыми: человек их произносит вслух,
    # и без образца произношения упражнение теряет половину смысла.
    # Слот из каркаса убираем — озвучивать «…» бессмысленно.
    if scope in ("all", "phrases"):
        import phrases as ph
        for _sit, item in ph.all_phrases():
            items.append(ph.spoken(item, female=False))
            if item.get("he_f"):
                items.append(ph.spoken(item, female=True))
            # Формы к собеседнику-женщине: у них свой текст и свой файл.
            pair = ph.listener_forms(item)
            if pair:
                items.append(pair["to_f"].replace(ph.SLOT, "").strip())
    if scope in ("all", "words"):
        for cat, pairs in VOCAB.items():
            for ru, he in pairs:
                items.append(he)
        for cat, pairs in VERBS.items():
            for ru, he in pairs:
                items.append(he)
    sections = [s for s in ("present", "past", "future")
                if scope in ("all", "forms", s)]
    if sections:
        for root, data in CONJUGATIONS.items():
            for section in sections:
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


# Как именно был озвучен каждый текст. Нужно, чтобы скрипт сам замечал
# правки в translit.py: имя файла — хеш от слова, и при исправлении
# ударения оно не меняется, так что готовый файл выглядит свежим, хотя
# звучит уже неправильно. Раньше это лечилось --force на весь банк —
# то есть переозвучкой всего из-за десятка правок.
#
# Слепок — это готовая разметка (транскрипция, ударение, паузы) плюс
# голос: всё, от чего зависит звучание. Изменился слепок — файл устарел.
RECIPE_PATH = Path(audio.AUDIO_DIR) / "pronunciation.json"


def recipe(text):
    return f"{VOICE}|{ssml_inner(text)}"


def load_recipes():
    if RECIPE_PATH.exists():
        try:
            return json.loads(RECIPE_PATH.read_text(encoding="utf-8"))
        except (ValueError, OSError) as e:
            print(f"Слепки произношения не читаются ({e}), считаем всё свежим.")
    return {}


def save_recipes(data):
    try:
        RECIPE_PATH.parent.mkdir(parents=True, exist_ok=True)
        RECIPE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                               encoding="utf-8")
    except OSError as e:
        print(f"Не удалось сохранить слепки произношения: {e}")


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
    ap.add_argument("--scope", choices=SCOPES, default="all")
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

    # Устаревшие — те, чей слепок произношения разошёлся с нынешним.
    # Про слова без слепка (озвученные до появления этой проверки) мы
    # ничего не знаем и считаем свежими; слепок им проставится в конце
    # этого же запуска, и дальше правки будут ловиться сами.
    recipes = load_recipes()
    broken = set()

    # Ловушка первого запуска. Слепков ещё нет, а файлы уже есть — и мы
    # не можем знать, чем они озвучены: правки в translit.py, сделанные
    # до появления слепков, в них не попали. Если промолчать, первый же
    # запуск запишет НЫНЕШНИЙ слепок к СТАРОМУ файлу и пометит его
    # свежим навсегда. Поэтому говорим об этом вслух.
    already = [t for t in texts if not pending(t)]
    if already and not recipes:
        print(f"⚠️  Слепков произношения ещё нет, а озвучено уже {len(already)}.")
        print("    Чем именно озвучены эти файлы — неизвестно: правки")
        print("    произношения, сделанные раньше, в них не попали.")
        print("    Один раз прогони с --force, иначе они останутся")
        print("    со старым звучанием, а скрипт будет считать их свежими.\n")

    def remember():
        """Слепок ставим только тем, кто реально озвучен: иначе сбой
        связи навсегда пометил бы файл свежим, хотя он звучит по-старому."""
        for t in texts:
            if t not in broken and not pending(t):
                recipes[t] = recipe(t)
        save_recipes(recipes)

    def stale(t):
        was = recipes.get(t)
        return was is not None and was != recipe(t)

    redo = args.force or args.only
    outdated = [t for t in texts if stale(t)]
    todo = texts if redo else [t for t in texts if pending(t) or stale(t)]
    if args.limit:
        todo = todo[: args.limit]

    jobs = [(t, r, s) for t in todo
            for (r, s) in (speeds if (redo or stale(t)) else pending(t))]

    chars = sum(len(t) for t, _, _ in jobs)
    price = PRICE_PER_1M_CHARS * chars / 1_000_000
    ready = len([t for t in texts if not pending(t)])
    print(f"Всего текстов: {len(texts)}, полностью озвучено: {ready}")
    if outdated:
        print(f"Из них устарело после правок произношения: {len(outdated)} "
              f"(например, {', '.join(outdated[:3])})")
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
        # Слепки записываем даже когда работы нет: иначе для набора,
        # который озвучили до появления этой проверки, они не появятся
        # никогда — и правку произношения скрипт молча пропустит.
        remember()
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
                broken.add(text)
                print(f"  не удалось «{text}» ({rate}): {e}")
                time.sleep(2)   # скорее всего лимит запросов — подождём
            if i % 50 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)}…")
    except KeyboardInterrupt:
        remember()
        print(f"\nПрервано. Озвучено {done}, файлы сохранены.")
        print("Запусти скрипт снова — продолжит с того же места.")
        return 0

    remember()
    print(f"Готово: озвучено {done}, ошибок {failed}.")
    print(f"Файлы: {audio.AUDIO_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
