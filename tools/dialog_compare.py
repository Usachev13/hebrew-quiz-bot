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
from translit import translit  # noqa: E402

# Разговор, а не набор отдельных вопросов: важно, помнит ли собеседник
# сказанное. Третья реплика проверяет ровно это — имя названо в первой.
SCRIPT = [
    "שלום",
    "אני דניאל. איך קוראים לך?",
    "מה השם שלי?",
    "אני גר בתל אביב",
    "как сказать «я хочу открыть счёт в банке»?",
]


def run(provider, verbose=True, raw=False, model=None):
    """Один разговор с одной моделью.

    model переопределяет имя на время прогона — чтобы сравнить две
    модели одного поставщика, не правя .env и не перезапуская бота.
    """
    saved_model = None
    if model:
        key = {"openai": "OPENAI_MODEL", "google": "GOOGLE_MODEL",
               "anthropic": "ANTHROPIC_MODEL"}[provider]
        saved_model = getattr(dialog, key)
        setattr(dialog, key, model)
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
            # Чтение кириллицей — не украшение. Иврит в терминале
            # раскладывается двунаправленным алгоритмом, и вперемешку с
            # русским и знаками порядок слов на экране может выглядеть
            # как угодно: показалось, что модель пишет слева направо.
            # По транскрипции видно, что она НА САМОМ ДЕЛЕ сказала, и
            # бессмыслица опознаётся сразу, без чтения на иврите.
            if res["ok"] and res["he"]:
                try:
                    print(f"      {translit(res['he'])}")
                except Exception:                            # noqa: BLE001
                    pass
            print(f"      {res['ru']}")
            if res["fixed"]:
                print(f"      поправка: {res['fixed']}")
            if res.get("no_ru"):
                print("      ⚠️ перевода нет — модель не заполнила поле ru")
            if raw:
                print(f"      сырой ответ: {res['raw'][:400]}")
        time.sleep(0.5)
    dialog.ANTHROPIC_KEY, dialog.OPENAI_KEY, dialog.GOOGLE_KEY = saved
    if saved_model is not None:
        key = {"openai": "OPENAI_MODEL", "google": "GOOGLE_MODEL",
               "anthropic": "ANTHROPIC_MODEL"}[provider]
        setattr(dialog, key, saved_model)
    return rows


def score(rows):
    """Три числа, которые можно посчитать без носителя."""
    clean = sum(1 for _s, r in rows if r["ok"])
    no_ru = sum(1 for _s, r in rows if r.get("no_ru"))
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
            "без перевода": f"{no_ru}/{len(rows)}",
            "встречных вопросов": f"{asks}/{len(rows)}",
            "средняя длина": f"{length:.0f} знаков",
            "помнит имя": "да" if remembers else "НЕТ",
            "токенов": f"{tin} + {tout}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", default="google,openai,anthropic")
    ap.add_argument("--models", default="",
                    help="сравнить модели ОДНОГО поставщика через запятую, "
                         "например: gpt-4o-mini,gpt-4o")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--niqqud", default="",
                    help="сравнить источники огласовок: model,nakdan — "
                         "кто ставит никуд, сама модель или Dicta")
    ap.add_argument("--raw", action="store_true",
                    help="печатать ответ модели как есть — видно, "
                         "какие поля она пропустила")
    args = ap.parse_args()

    results = {}
    if args.niqqud:
        # Первый вариант этого сравнения гонял два РАЗНЫХ разговора — по
        # одному на источник огласовок. Модель отвечает не одинаково, и
        # после первой же реплики разговоры расходились: в одном
        # собеседницу звали Шира, в другом Михаль. Сравнивались тексты,
        # а не огласовки.
        #
        # Теперь разговор один. Модель просится огласовывать сама, и
        # каждая её реплика, очищенная от значков, отдаётся ещё и Dicta.
        # Две огласовки ОДНОГО текста — рядом, и расхождения помечены.
        import nakdan
        provider = args.providers.split(",")[0].strip()
        saved = dialog.NIQQUD
        dialog.NIQQUD = "model"
        os.environ["DIALOG_PROVIDER"] = provider
        history = []
        differ = 0
        own_used = 0
        bare_replies = 0
        print(f"\n=== {provider}: огласовки модели против Dicta ===")
        for said in SCRIPT:
            res = dialog.reply(history, said, gender="m", lang="ru")
            history += [("user", said), ("bot", res["he"])]
            # Колонка «модель» — то, что модель написала САМА, до выбора
            # источника. Первый заход брал res["he"], то есть уже итог, и
            # при откате на Dicta сравнивал Dicta с Dicta.
            own = res["he_model"]
            complete = hebrew_rules.sanitize(own)[1]
            own_used += 1 if res["niqqud_by"] in ("model", "model+nakdan") else 0
            dicta = nakdan.vocalize_trusted(hebrew_rules.strip_niqqud(own))
            same = nakdan._norm_marks(own) == nakdan._norm_marks(dicta)
            # Модель не поставила ни одного значка — спорить не с чем, это
            # не расхождение, а пропуск. Первый счёт складывал их вместе и
            # завышал число «разногласий».
            silent = own == hebrew_rules.strip_niqqud(own)
            if silent:
                bare_replies += 1
            elif not same:
                differ += 1
            print(f"\n    > {said}")
            print(f"      {res['ru']}")
            for label, text in (("модель", own), ("Dicta ", dicta)):
                try:
                    reading = translit(text)
                except Exception:                            # noqa: BLE001
                    reading = "?"
                print(f"      {label}: {text}")
                print(f"              {reading}")
            if not complete:
                print("      ⚠️ у модели огласовано не всё — пропуски "
                      "заполнит Dicta")
            if res["he"] != own:
                print(f"      в бот:  {res['he']}   [{res['niqqud_by']}]")
            if not same and not silent:
                print("      ⚠️ огласовки разошлись — какое чтение верно, "
                      "видно по переводу выше")
            time.sleep(0.5)
        dialog.NIQQUD = saved
        print(f"\nРеплик: {len(SCRIPT)}. Модель не огласовала вовсе: "
              f"{bare_replies}. Огласовала и разошлась с Dicta: {differ}.")
        print("Где разошлись — смотреть по смыслу: перевод один на обоих.")
        return 0
    if args.models:
        # Сравниваем модели одного поставщика: он должен быть один.
        provider = args.providers.split(",")[0].strip()
        for model in args.models.split(","):
            model = model.strip()
            print(f"\n=== {provider}: {model} ===")
            rows = run(provider, verbose=not args.quiet, raw=args.raw,
                       model=model)
            if rows:
                results[model] = score(rows)
    else:
        for provider in args.providers.split(","):
            provider = provider.strip()
            if not provider:
                continue
            print(f"\n=== {provider} ===")
            rows = run(provider, verbose=not args.quiet, raw=args.raw)
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
