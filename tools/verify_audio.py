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
from matching import _normalize, accepted_forms, _levenshtein  # noqa: E402
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


def severity(heard, expected):
    """Насколько расхождение серьёзное.

    Распознавание отдельных слов ненадёжно само по себе: оно опирается
    на контекст, а у нас его нет. Поэтому «услышал похожее» — почти
    наверняка предел распознавания, а не брак озвучки. Реальные
    кандидаты на прослушивание — тишина и совсем другое слово.
    """
    heard_norm = _normalize(heard.rstrip(".,!?"))
    if not heard_norm:
        return "тишина"

    forms = accepted_forms(expected)
    dist = min(_levenshtein(heard_norm, f, limit=5) for f in forms)
    if dist <= 1:
        return "почти совпало"
    if dist <= 2:
        return "похоже"
    if len(heard_norm.split()) > 1:
        # одно слово услышано как несколько — обычно распознавание
        # домысливает, а не озвучка испорчена
        return "услышано несколько слов"
    return "другое слово"


SEVERITY_ORDER = ["тишина", "другое слово", "услышано несколько слов",
                  "похоже", "почти совпало"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="проверить только N карточек")
    ap.add_argument("--slow", action="store_true", help="проверять медленные файлы")
    ap.add_argument("--out", default="audio_report.txt", help="куда сохранить отчёт")
    ap.add_argument("--reuse", action="store_true",
                    help="взять прошлые результаты и только пересобрать отчёт")
    args = ap.parse_args()

    # Результаты распознавания кэшируем: пересобрать отчёт по-другому
    # стоит дороже, чем стоило узнать эти результаты.
    cache_path = Path("audio_recognition.json")
    cache = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except ValueError:
            pass

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
            if args.reuse or text in cache:
                if text not in cache:
                    continue
                heard = cache[text]
            else:
                path = audio.audio_path(text, slow=args.slow)
                try:
                    heard = recognize(path)
                    cache[text] = heard
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
        print("\nПрервано, результаты сохранены.")
    finally:
        if cache:
            cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                                  encoding="utf-8")

    print(f"\nИтог: совпало {ok}, расхождений {len(bad)}, ошибок связи {errors}")

    if bad:
        groups = {}
        for orig, expected, heard in bad:
            groups.setdefault(severity(heard, expected), []).append(
                (orig, expected, heard))

        print("\nРазбор расхождений:")
        for level in SEVERITY_ORDER:
            items = groups.get(level, [])
            if items:
                print(f"  {level:26} {len(items):4}")

        suspicious = groups.get("тишина", []) + groups.get("другое слово", [])
        print(f"\nСтоит послушать: {len(suspicious)} из {len(bad)} "
              f"(остальное — предел распознавания, а не брак озвучки)")

        lines = [
            "Проверка озвучки распознаванием речи.",
            "",
            "Распознавание отдельных слов ненадёжно: оно опирается на",
            "контекст, которого у нас нет. Поэтому «почти совпало» и",
            "«похоже» — почти наверняка предел распознавания, а не брак",
            "озвучки. Слушать имеет смысл «тишина» и «другое слово».",
            "",
        ]
        for level in SEVERITY_ORDER:
            items = groups.get(level, [])
            if not items:
                continue
            lines += [f"=== {level.upper()} ({len(items)}) ===",
                      f"{'эталон':24} {'ожидали':18} услышано", "-" * 64]
            for orig, expected, heard in items:
                lines.append(f"{orig:24} {expected:18} {heard or '(тишина)'}")
            lines.append("")

        Path(args.out).write_text("\n".join(lines), encoding="utf-8")
        print(f"Полный отчёт: {args.out}")

        if suspicious:
            print("\nПодозрительные (первые 15):")
            for orig, expected, heard in suspicious[:15]:
                print(f"  {orig:22} ожидали {expected:16} услышано {heard or '(тишина)'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
