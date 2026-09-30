#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сравнение моделей на одних и тех же репликах.

Зачем
-----
Выбирать модель по описанию бесполезно: нам нужен не «общий уровень», а
две коротких фразы бытового иврита и умение не терять нить. Это
проверяется за пять минут, если задать всем одно и то же и положить
ответы рядом.

Мы уже знаем, на чём спотыкается нынешняя: она переспрашивала имя через
реплику после того, как его назвали, и путалась в простых словах.
Поэтому реплики подобраны так, чтобы это вылезло.

Что считается само
------------------
Правильность иврита машина не проверяет — это к носителю. Но три вещи
она посчитать может, и они говорят многое:

* сколько ответов прошло формальные правила записи;
* сколько раз собеседник задал встречный вопрос (без него разговор
  обрывается на второй реплике);
* длину ответа (уровень алеф — это две коротких фразы, а не абзац).

Запуск (нужны ключи в .env):
    python3 tools/dialog_compare.py
    python3 tools/dialog_compare.py --providers google,openai
"""

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
sys.path.insert(0, str(HERE.parent))

import dialog  # noqa: E402
import hebrew_rules  # noqa: E402

# Разговор, а не набор отдельных вопросов: важно, помнит ли собеседник
# сказанное. Третья реплика проверяет ровно это — имя названо в первой.
SCRIPT = [
    "שלום",
    "אני דניאל. איך קוראים לך?",
    "מה השם שלי?",
    "אני גר בתל אביב",
    "как сказать «я хочу открыть счёт в банке»?",
]


def run(provider, verbose=True):
    saved = (dialog.ANTHROPIC_KEY, dialog.OPENAI_KEY, dialog.GOOGLE_KEY)
    os.environ["DIALOG_PROVIDER"] = provider
    if not dialog.provider():
        print(f"  {provider}: {dialog.why_unavailable()}")
        return None

    history, rows = [], []
    for said in SCRIPT:
        try:
            res = dialog.reply(history, said, gender="m", lang="ru")
        except Exception as e:                                # noqa: BLE001
            print(f"  {provider}: {str(e)[:160]}")
            return None
        history += [("user", said), ("bot", res["he"])]
        rows.append((said, res))
        if verbose:
            print(f"    > {said}")
            print(f"      {res['he']}")
            print(f"      {res['ru']}")
            if res["fixed"]:
                print(f"      поправка: {res['fixed']}")
        time.sleep(0.5)
    dialog.ANTHROPIC_KEY, dialog.OPENAI_KEY, dialog.GOOGLE_KEY = saved
    return rows


def score(rows):
    """Три числа, которые можно посчитать без носителя."""
    clean = sum(1 for _s, r in rows if r["ok"])
    asks = sum(1 for _s, r in rows if "?" in r["he"])
    length = sum(len(r["he"]) for _s, r in rows) / max(len(rows), 1)
    tin = sum(r["usage"][0] for _s, r in rows)
    tout = sum(r["usage"][1] for _s, r in rows)
    # Помнит ли имя: третья реплика спрашивает «как меня зовут?».
    # Огласовки снимаем: ответ придёт огласованным, а ищем мы скелет.
    # Первый заход этого не делал и всегда отвечал «НЕТ» — проверка
    # проверяла сама себя.
    third = hebrew_rules.strip_niqqud(rows[2][1]["he"]) if len(rows) > 2 else ""
    remembers = "דניאל" in third
    return {"огласовки в порядке": f"{clean}/{len(rows)}",
            "встречных вопросов": f"{asks}/{len(rows)}",
            "средняя длина": f"{length:.0f} знаков",
            "помнит имя": "да" if remembers else "НЕТ",
            "токенов": f"{tin} + {tout}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", default="google,openai,anthropic")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    results = {}
    for provider in args.providers.split(","):
        provider = provider.strip()
        if not provider:
            continue
        print(f"\n=== {provider} ===")
        rows = run(provider, verbose=not args.quiet)
        if rows:
            results[provider] = score(rows)

    if not results:
        print("\nНи одна модель не ответила. Проверьте ключи: "
              "tools/check_dialog_key.py")
        return 1

    keys = list(next(iter(results.values())))
    width = max(len(k) for k in keys) + 2
    print("\n" + " " * width + "".join(f"{p:>16}" for p in results))
    for key in keys:
        print(f"{key:<{width}}" + "".join(f"{results[p][key]:>16}"
                                          for p in results))
    print("\nПравильность иврита здесь не оценивается — это к носителю. "
          "Реплики сохранены в базе разговора.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
