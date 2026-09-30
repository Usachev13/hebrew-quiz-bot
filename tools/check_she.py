# -*- coding: utf-8 -*-
"""
Проверка упражнения на частицу שֶׁ־.

Фразы написаны руками, а не выведены правилом, — поэтому главное здесь
сверка: каждая верная фраза проверена огласовщиком Dicta (восемь из
восьми сошлись), и правка текста не должна молча уйти от сверенного.

Второе — неверные варианты. Каждый обязан отличаться от верного ровно
названным: калька подменяет שֶׁ вопросительным словом, «раздельно»
отрывает שֶׁ от глагола. Если калька случайно совпадёт с верной фразой
или «раздельно» окажется слитным, упражнение соврёт.

Третье — озвучка. Кальку, сказанную живым голосом, человек запомнит как
образец. Озвучены должны быть верные фразы и только они.
"""

import os
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import quiz  # noqa: E402
import she  # noqa: E402

fails = []


def check(title, bad, show=lambda x: x):
    if bad:
        fails.append(title)
        print(f"  СБОЙ {title}: {len(bad)}")
        for item in bad[:8]:
            print(f"     {show(item)}")
    else:
        print(f"✓ {title} — не найдено")


def norm(word):
    groups = []
    for ch in word:
        if unicodedata.combining(ch):
            if groups:
                groups[-1][1].append(ch)
        else:
            groups.append([ch, []])
    return "".join(l + "".join(sorted(m)) for l, m in groups)


def bare(word):
    return "".join(c for c in word if not unicodedata.combining(c))


# Сверено с Dicta 30 сентября 2026, по одной фразе за запрос: 8 из 8.
CHECKED = {norm(x) for x in [
    "הַסֵּפֶר שֶׁקָּנִיתִי", "הַסֵּפֶר שֶׁקָּרָאתִי", "הַבַּיִת שֶׁרָאִיתִי",
    "הַדִּירָה שֶׁרָאִיתִי", "הַסֵּפֶר שֶׁלָּקַחְתִּי", "יָדַעְתִּי שֶׁהוּא כָּאן",
    "יָדַעְתִּי שֶׁהִיא כָּאן", "חָשַׁבְתִּי שֶׁזֶּה טוֹב",
]}
SHE = "שֶׁ"

check("верная фраза не сверена",
      [s[2] for s in she.SENTENCES if norm(s[2]) not in CHECKED])

# ------------------------------------------------ устройство вариантов
bad = []
for ru, _en, right, wrongs, kind in she.SENTENCES:
    # В верной фразе שֶׁ стоит слитно — ровно одно слово начинается с него.
    if not any(w.startswith(SHE) and len(bare(w)) > 1 for w in right.split()):
        bad.append(f"{ru}: в верной шин не слитно")
    for wrong, rule in wrongs:
        if rule.startswith("calque"):
            question = "אֵיזֶה" if rule == "calque_which" else "מָה"
            if bare(question) not in {bare(w) for w in wrong.split()} and \
                    bare("אֵיזוֹ") not in {bare(w) for w in wrong.split()}:
                bad.append(f"{ru}: в кальке нет вопросительного слова")
            if SHE in wrong:
                bad.append(f"{ru}: в кальке осталась שֶׁ")
        elif rule == "separate":
            if SHE not in wrong.split():
                bad.append(f"{ru}: «раздельно» не отдельным словом")
check("неверный вариант устроен не по своему правилу", bad)

check("неверный вариант совпал с верным",
      [s[0] for s in she.SENTENCES for w, _ in s[3] if w == s[2]])

# Прошедшее время выбрано затем, чтобы не спрашивать пол говорящего:
# «קָנִיתִי» одинаково у мужчины и женщины. Подсказка обязана это
# отражать — «купил(а)», а не «купил».
gender_hint = [s[0] for s in she.SENTENCES if "(а)" not in s[0]]
check("подсказка не показывает, что пол не важен", gender_hint)

# ------------------------------------------------------------ озвучка
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "gen_audio", os.path.join(os.path.dirname(__file__), "generate_audio.py"))
gen = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(gen)
    voiced = set(gen.collect("all"))
    pool = quiz.POOLS["she"]
    check("верная фраза не озвучивается", [c.he for c in pool if c.he not in voiced])
    check("калька попала в озвучку",
          [w for c in pool for w in c.wrong if w in voiced])
except Exception as exc:                                    # noqa: BLE001
    check("генератор озвучки не читается", [str(exc)])

print(f"\nфраз: {len(she.SENTENCES)}, сверено: {len(CHECKED)}")
if fails:
    print(f"\nСБОЕВ: {len(fails)}")
    sys.exit(1)
