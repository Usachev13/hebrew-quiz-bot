# -*- coding: utf-8 -*-
"""
Проверка склонения предлогов.

Чем опасны эти данные
---------------------
Сорок форм, и все похожи друг на друга: לִי, לְךָ, לָךְ, לוֹ. Разница
между «тебе» мужского и женского рода — одна огласовка и порядок двух
знаков. Списать форму не в ту строку при вводе легче лёгкого, а
выглядеть таблица будет безупречно.

Поэтому проверяется не «данные есть», а внутренняя связность: что
формы не повторяются внутри предлога, что лиц ровно столько же, сколько
подписей, что форма начинается с той же основы, и что упражнение берёт
дистракторы из того же предлога, а не из чужого.

Правильность самих форм — к носителю: пары «ты мужской / ты женский»
машина различить не может, она видит только, что они разные.
"""

import os
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import hebrew_meta  # noqa: E402
import quiz  # noqa: E402

fails = []


def check(title, bad, show=lambda x: x):
    if bad:
        fails.append(title)
        print(f"  СБОЙ {title}: {len(bad)}")
        for item in bad[:8]:
            print(f"     {show(item)}")
    else:
        print(f"✓ {title} — не найдено")


def bare(word):
    return "".join(c for c in word if not unicodedata.combining(c))


# ------------------------------------------------------------- данные
count = []
for key, data in hebrew_meta.PREPOSITIONS.items():
    if len(data["forms"]) != len(hebrew_meta.PERSONS):
        count.append(f"{key}: форм {len(data['forms'])}, "
                     f"подписей {len(hebrew_meta.PERSONS)}")
check("форм и подписей поровну", count)

dupes = []
for key, data in hebrew_meta.PREPOSITIONS.items():
    forms = data["forms"]
    if len(set(forms)) != len(forms):
        seen = set()
        for i, f in enumerate(forms):
            if f in seen:
                dupes.append(f"{key}: {f} повторяется ({hebrew_meta.PERSONS[i]})")
            seen.add(f)
check("форма повторяется внутри предлога", dupes)

# Самая вероятная описка — «ты мужской» и «ты женский» одинаковы: они
# различаются только огласовкой, и при копировании строки сливаются.
same_you = []
for key, data in hebrew_meta.PREPOSITIONS.items():
    m, f = data["forms"][1], data["forms"][2]
    if m == f:
        same_you.append(f"{key}: {m}")
    elif bare(m) != bare(f) and key not in ("et", "al"):
        # У большинства предлогов согласные у «тебе» совпадают, а
        # различие только в огласовке. Где это не так — стоит назвать,
        # но не считать ошибкой: у אֶת и עַל формы устроены иначе.
        same_you.append(f"{key}: согласные «ты» разошлись — {m} / {f}")
check("формы «ты» неразличимы или неожиданны", same_you)

# Все формы предлога должны расти из его основы: у לְ они на ламед, у
# שֶׁל на шин. Если строка попала не в тот предлог, это видно сразу.
STEM = {"shel": "של", "le": "ל", "et": "את", "im": "את", "al": "על"}
stray = []
for key, data in hebrew_meta.PREPOSITIONS.items():
    stem = STEM.get(key)
    if not stem:
        continue
    for i, form in enumerate(data["forms"]):
        # «с» склоняется от другой основы: עִם, но אִתִּי. Это не ошибка,
        # а особенность, и она отмечена в таблице выше.
        if not bare(form).startswith(stem[0]):
            stray.append(f"{key}: {form} не от основы {stem}")
check("форма не от своей основы", stray)

# Таблица для страницы справочника берёт те же подписи. Однажды здесь
# появился второй список лиц — кортежами — и молча переопределил первый:
# страница показала бы «('я', 'I')» вместо «я». Упражнение при этом
# работало, и ни одна проверка не заметила.
bad_table = []
for key in hebrew_meta.PREPOSITIONS:
    for lang in ("ru", "en"):
        tab = hebrew_meta.table(key, lang)
        for row in tab["rows"]:
            if not isinstance(row["who"], str):
                bad_table.append(f"{key}/{lang}: {row['who']!r}")
                break
check("таблица справочника получила не строку", bad_table)
check("подписей лиц на двух языках поровну",
      [] if len(hebrew_meta.PERSONS) == len(hebrew_meta.PERSONS_EN)
      else [f"{len(hebrew_meta.PERSONS)} / {len(hebrew_meta.PERSONS_EN)}"])


# ---------------------------------------------------------- карточки
pool = quiz.POOLS["prepositions"]
check("карточек не столько, сколько форм",
      [] if len(pool) == sum(len(d["forms"])
                             for d in hebrew_meta.PREPOSITIONS.values())
      else [f"{len(pool)}"])

check("ключи карточек повторяются",
      [] if len({c.cid for c in pool}) == len(pool) else ["да"])

check("нет английской подсказки", [c.cid for c in pool if not c.en])

# Дистракторы обязаны приходить из того же предлога: иначе человек
# выбирает по внешнему виду («что-то на шин»), не вспоминая лицо.
import random  # noqa: E402

random.seed(7)
foreign = []
for _ in range(40):
    q = quiz.build_question(pool, set())
    card = next(c for c in pool if c.key() == q["id"])
    same_prep = {c.he for c in pool if c.cat == card.cat}
    for option in q["options"]:
        if option not in same_prep:
            foreign.append(f"{card.ru}: чужой вариант {option}")
check("дистрактор из чужого предлога", foreign)

print()
print(f"предлогов: {len(hebrew_meta.PREPOSITIONS)}, "
      f"форм: {len(pool)}, лиц: {len(hebrew_meta.PERSONS)}")
print("Различить «тебе» мужского и женского рода машина не может — "
      "она видит лишь, что формы разные. Это к носителю.")
if fails:
    print(f"\nСБОЕВ: {len(fails)}")
    sys.exit(1)
