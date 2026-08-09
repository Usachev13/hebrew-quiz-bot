# -*- coding: utf-8 -*-
"""
Автоматическая проверка озвучки: слушаем её распознаванием речи.

Синтезированные файлы прогоняются через Azure Speech-to-Text, и то, что
он услышал, сверяется с исходным словом. Так находятся карточки, где
синтезатор прочитал не то слово или произнёс невнятно — без того, чтобы
переслушивать 1884 файла вручную.

Чего проверка НЕ ловит: ударение. Распознавание вернёт «тапуах»
одинаково, куда бы оно ни падало — тут по-прежнему нужны уши.

    # быстрая проба
    python3 tools/verify_audio.py --limit 30

    # всё
    python3 tools/verify_audio.py

Расход: распознавание тарифицируется по времени звучания. Наши файлы
короткие, весь банк — примерно полчаса аудио, и это укладывается в
бесплатные 5 часов в месяц.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import audio  # noqa: E402
from generate_audio import AZURE_KEY, AZURE_REGION, collect, missing_key  # noqa: E402
from matching import _normalize, accepted_forms  # noqa: E402
from translit import to_ktiv_male  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

STT_URL = (f"https://{AZURE_REGION}.stt.speech.microsoft.com"
           "/speech/recognition/conversation/cognitiveservices/v1")


def recognize(path):
    """Что синтезатор произнёс, по мнению распознавания."""
    with open(path, "rb") as f:
        data = f.read()
    r = requests.post(
        STT_URL,
        params={"language": "he-IL", "format": "simple"},
        headers={
            "Ocp-Apim-Subscription-Key": AZURE_KEY,
            # ровно тот формат, в котором мы синтезируем
            "Content-Type": "audio/ogg; codecs=opus",
            "Accept": "application/json",
        },
        data=data,
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
    body = r.json()
    if body.get("RecognitionStatus") != "Success":
        return ""          # тишина или неразборчиво — тоже результат
    return body.get("DisplayText", "")


def matches(heard, expected):
    """Совпало ли услышанное с ожидаемым.

    Сравниваем без огласовок и знаков препинания: распознавание всегда
    возвращает обычное письмо, а у нас эталон огласованный. Принимаем и
    «скелет», и полное написание — как в проверке набранных ответов.
    """
    heard_norm = _normalize(heard.rstrip(".,!?"))
    return bool(heard_norm) and heard_norm in accepted_forms(expected)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="проверить только N карточек")
    ap.add_argument("--slow", action="store_true", help="проверять медленные файлы")
    ap.add_argument("--out", default="audio_report.txt", help="куда сохранить отчёт")
    args = ap.parse_args()

    problem = missing_key()
    if problem:
        print(problem)
        return 1

    texts = [t for t in collect("all") if audio.has_audio(t, slow=args.slow)]
    if not texts:
        print("Озвученных файлов не найдено — сначала tools/generate_audio.py")
        return 1
    if args.limit:
        texts = texts[: args.limit]

    print(f"Проверяю {len(texts)} карточек "
          f"({'медленные' if args.slow else 'обычные'} файлы)…\n")

    ok, bad, errors = 0, [], 0
    try:
        for i, text in enumerate(texts, 1):
            path = audio.audio_path(text, slow=args.slow)
            try:
                heard = recognize(path)
            except Exception as e:
                errors += 1
                print(f"  ! {text}: {str(e)[:80]}")
                time.sleep(2)
                continue

            if matches(heard, text):
                ok += 1
            else:
                bad.append((text, to_ktiv_male(text), heard))
            if i % 25 == 0 or i == len(texts):
                print(f"  {i}/{len(texts)} — совпало {ok}, расхождений {len(bad)}")
    except KeyboardInterrupt:
        print("\nПрервано.")

    print(f"\nИтог: совпало {ok}, расхождений {len(bad)}, ошибок связи {errors}")

    if bad:
        lines = ["Карточки, где распознавание услышало не то.",
                 "Это не всегда ошибка озвучки — иврит без огласовок",
                 "омонимичен, и распознавание тоже ошибается.", "",
                 f"{'эталон':22} {'ожидали':16} {'услышано'}", "-" * 60]
        for orig, expected, heard in bad:
            lines.append(f"{orig:22} {expected:16} {heard or '(тишина)'}")
        Path(args.out).write_text("\n".join(lines), encoding="utf-8")
        print(f"Список расхождений: {args.out}")
        print("\nПервые несколько:")
        for orig, expected, heard in bad[:10]:
            print(f"  {orig:20} ожидали {expected:14} услышано {heard or '(тишина)'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
