# -*- coding: utf-8 -*-
"""
Проверка числительных.

Главная опасность здесь — перепутать наборы местами. Формы похожи, а
правило вывернуто наизнанку: с ־ָה идёт МУЖСКОЙ род. Ошибись мы один
раз при вводе данных — и упражнение будет старательно учить неверному,
причём выглядеть будет безупречно.

Поэтому ниже проверяется не «данные непротиворечивы», а привязка к
внешнему источнику: пары взяты из Викисловаря, где у каждой статьи
указано «feminine of …», и сверялись с двух сторон — и по женской
статье, и по мужской.

Правильность самих форм машина подтвердить не может; она следит, чтобы
записанное не разъехалось и чтобы упражнение не начало учить наоборот.
"""

import os
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import nouns  # noqa: E402
import numerals  # noqa: E402
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


# --------------------------------------------------- наборы не перепутаны
# Мужская форма от трёх до десяти оканчивается на ־ָה, женская — нет.
# Это и есть тот самый переворот; если данные введены наоборот, проверка
# увидит это сразу.
HE = "ה"
KAMATS = "ָ"


def ends_with_kamats_he(word):
    """Оканчивается ли слово на ־ָה.

    Через группы «буква + её знаки», а не сравнением хвоста строки:
    порядок знаков при букве у разных источников разный, и в «שְׁלוֹשָׁה»
    точка шина стоит ПОСЛЕ камаца. Проверка по хвосту на этом и
    споткнулась, объявив мужские формы женскими.
    """
    groups = []
    for ch in word:
        if unicodedata.combining(ch):
            if groups:
                groups[-1][1].append(ch)
        else:
            groups.append([ch, []])
    if len(groups) < 2 or groups[-1][0] != HE:
        return False
    return KAMATS in groups[-2][1]


wrong_way = []
for number, (fem, masc) in numerals.NUMERALS.items():
    if number in (1, 2):
        continue          # «один» и «два» устроены иначе
    if not ends_with_kamats_he(masc):
        wrong_way.append(f"{number}: мужская {masc} без окончания ־ָה")
    if ends_with_kamats_he(fem):
        wrong_way.append(f"{number}: женская {fem} с окончанием ־ָה")
check("наборы переставлены местами", wrong_way)

check("формы пары совпали", [f"{n}: {a}" for n, (a, b) in numerals.NUMERALS.items()
                             if a == b])
check("число без пары", [n for n in range(1, 11) if n not in numerals.NUMERALS])

# «Восемь» — известная ловушка: обе формы похожи и различаются одной
# огласовкой (שְׁמוֹנֶה при женском, שְׁמוֹנָה при мужском). Если данные
# ввели копированием, они окажутся одинаковыми — см. проверку выше, но
# отметим отдельно, чтобы не потерялось.
fem8, masc8 = numerals.NUMERALS[8]
check("восемь: формы не различаются",
      [] if fem8 != masc8 else [f"{fem8} = {masc8}"])

# ------------------------------------------------------- выбор по роду
mismatch = []
for number in numerals.NUMERALS:
    if numerals.form(number, nouns.M) != numerals.NUMERALS[number][1]:
        mismatch.append(f"{number}: мужской род выбран неверно")
    if numerals.form(number, nouns.F) != numerals.NUMERALS[number][0]:
        mismatch.append(f"{number}: женский род выбран неверно")
    if numerals.other_form(number, nouns.M) != numerals.NUMERALS[number][0]:
        mismatch.append(f"{number}: «другая форма» не та")
check("выбор формы по роду сбит", mismatch)

# Два перед существительным укорачивается, и это разные формы.
short_m = numerals.form(2, nouns.M, before_noun=True)
full_m = numerals.form(2, nouns.M, before_noun=False)
check("два перед словом не укоротилось",
      [] if short_m != full_m else [f"{short_m} = {full_m}"])

# Числа без рода не должны менять форму.
same = [n for n in numerals.INVARIABLE
        if numerals.form(n, nouns.M) != numerals.form(n, nouns.F)]
check("неизменяемое число изменилось по роду", same)

# ---------------------------------------------------------- карточки
pool = quiz.POOLS["numerals"]
check("карточек нет", [] if pool else ["пусто"])

no_wrong = [c.cid for c in pool if not c.wrong]
check("карточка без неверного варианта", no_wrong)

same_option = [c.cid for c in pool if c.he in c.wrong]
check("верный ответ повторён среди неверных", same_option)

# Существительное в карточке обязано быть из выверенных: род и
# множественное подтверждены словарём.
known = {nouns.plural_of(c.he) for c in quiz.VOCAB_FLAT if nouns.plural_of(c.he)}
stray = [c.cid for c in pool if c.he.split(" ", 1)[-1] not in known]
check("слово в карточке не из выверенных", stray)

# И главное: форма числа в карточке соответствует роду её слова.
by_plural = {nouns.plural_of(c.he): nouns.gender_of(c.he)
             for c in quiz.VOCAB_FLAT if nouns.plural_of(c.he)}
bad_form = []
for c in pool:
    parts = c.he.split(" ", 1)
    if len(parts) != 2:
        continue
    num_form, plural = parts
    gender = by_plural.get(plural)
    if gender is None:
        continue
    expected = {numerals.form(n, gender) for n in numerals.NUMERALS}
    expected |= {numerals.form(2, gender, before_noun=True)}
    if num_form not in expected:
        bad_form.append(f"{c.ru}: {num_form} при роде {gender}")
check("форма числа не под род слова", bad_form)

# Озвучка: связь между разделом и генератором нигде не объявлена, и
# разойтись они могут молча — так уже случилось с «собери фразу».
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "gen_audio", os.path.join(os.path.dirname(__file__), "generate_audio.py"))
gen = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(gen)
    voiced = set(gen.collect("all"))
    check("карточка не попадает в озвучку",
          [c.cid for c in pool if c.he not in voiced])
    # Неверные варианты озвучивать нельзя: неправильная форма, сказанная
    # живым голосом, запоминается не хуже правильной.
    right = {c.he for c in pool}
    check("неверный вариант попал в озвучку",
          [w for c in pool for w in c.wrong if w in voiced and w not in right])
except Exception as exc:                                    # noqa: BLE001
    check("генератор озвучки не читается", [str(exc)])

print()
print(f"чисел с двумя формами: {len(numerals.NUMERALS)}, "
      f"неизменяемых: {len(numerals.INVARIABLE)}, карточек: {len(pool)}")
print("Сами формы взяты из Викисловаря и сверены с двух сторон — "
      "по женской статье и по мужской.")
if fails:
    print(f"\nСБОЕВ: {len(fails)}")
    sys.exit(1)
