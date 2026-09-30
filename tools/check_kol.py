# -*- coding: utf-8 -*-
"""
Проверка упражнения על כָּל: каждый, весь, все.

Здесь неверный вариант одной карточки — верный ответ другой: «כָּל
הַיּוֹם» неверно для «каждого дня» и верно для «всего дня». Поэтому
главное, за чем следить, — чтобы значение сочетания определялось ТОЛЬКО
артиклем и числом, как в правиле. Если однажды «каждый» окажется с
артиклем, упражнение начнёт учить наоборот, и выглядеть это будет
безупречно.

Все 24 сочетания сверены с огласовщиком Dicta, по одному за запрос:
разошлось ноль. С «כָּל» впереди у него есть контекст, и омографы вроде
«שָׁנָה / שֵׁנָה» он различает.
"""

import os
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import kol  # noqa: E402
import nouns  # noqa: E402
import quiz  # noqa: E402
import syntax  # noqa: E402

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


# Сверено с Dicta 30 сентября 2026: 24 из 24.
CHECKED = {norm(x) for x in [
    "כָּל בַּיִת", "כָּל דִּירָה", "כָּל הַבַּיִת", "כָּל הַבָּתִּים", "כָּל הַדִּירָה",
    "כָּל הַדִּירוֹת", "כָּל הַיְּלָדִים", "כָּל הַיֶּלֶד", "כָּל הַיָּמִים", "כָּל הַיּוֹם",
    "כָּל הַלֵּילוֹת", "כָּל הַלַּיְלָה", "כָּל הַסְּפָרִים", "כָּל הַסֵּפֶר",
    "כָּל הַשָּׁבוּעַ", "כָּל הַשָּׁבוּעוֹת", "כָּל הַשָּׁנִים", "כָּל הַשָּׁנָה",
    "כָּל יֶלֶד", "כָּל יוֹם", "כָּל לַיְלָה", "כָּל סֵפֶר", "כָּל שָׁבוּעַ", "כָּל שָׁנָה",
]}


def meaning_of(phrase):
    """Какое значение у сочетания — по артиклю и числу, как в правиле."""
    word = phrase.split(" ", 1)[1]
    has_article = word.startswith(syntax.THE)
    bare_word = syntax.THE and word[len(syntax.THE):] if has_article else word
    # Множественное — если слово совпадает с формой мн. числа из словаря.
    plurals = {norm(syntax.definite(nouns.plural_of(n))) for n, *_ in kol.NOUNS
               if nouns.plural_of(n)}
    if has_article and norm(word) in plurals:
        return "all"
    return "whole" if has_article else "every"


# ------------------------------------------ значение задаётся правилом
wrong_meaning = []
for ru, _en, right, wrongs, meaning in kol.SENTENCES:
    if meaning_of(right) != meaning:
        wrong_meaning.append(f"{ru}: «{right}» по правилу — {meaning_of(right)}")
    for w, m in wrongs:
        if meaning_of(w) != m:
            wrong_meaning.append(f"{ru}: неверный «{w}» подписан {m}, "
                                 f"а по правилу {meaning_of(w)}")
check("значение не совпадает с правилом", wrong_meaning)

# ------------------------------------------------------------- сверка
shown = {s[2] for s in kol.SENTENCES} | {w for s in kol.SENTENCES for w, _ in s[3]}
check("сочетание не сверено", [x for x in shown if norm(x) not in CHECKED])

# ------------------------------------------------------------ карточки
pool = quiz.POOLS["kol"]
check("карточек нет", [] if pool else ["пусто"])
check("верный совпал с неверным", [c.cid for c in pool if c.he in c.wrong])
check("меньше двух неверных", [c.cid for c in pool if len(c.wrong) < 2])
check("ключи повторяются", [] if len({c.cid for c in pool}) == len(pool) else ["да"])

# Русская подсказка обязана различать значения: одна и та же подсказка у
# двух карточек с разными ответами — вопрос без правильного ответа.
by_ru = {}
for c in pool:
    by_ru.setdefault(c.ru, set()).add(c.he)
check("одна подсказка — разные ответы",
      [f"{ru}: {v}" for ru, v in by_ru.items() if len(v) > 1])

print(f"\nкарточек: {len(pool)}, сочетаний сверено: {len(CHECKED)}")
if fails:
    print(f"\nСБОЕВ: {len(fails)}")
    sys.exit(1)
