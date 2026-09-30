# -*- coding: utf-8 -*-
"""
Проверка упражнения на смихут.

Устроена как check_syntax: слова берутся из выверенных данных, а риск —
в неверных вариантах. Каждый обязан отличаться от верного ровно тем
правилом, которое назван, иначе разбор соврёт: назовёт одно правило, а
ошибок в ответе было две.

Отдельно — формы с артиклем. Они собраны нашим правилом и сверены с
огласовщиком Dicta: шесть из восьми сошлись, два расхождения — его
промахи на омографах («трапеза скота» вместо завтрака, «комната года»
вместо спальни). Здесь их и закрепляем, чтобы правка правила не
разъехалась со сверкой молча.
"""

import os
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import hebrew_meta  # noqa: E402
import quiz  # noqa: E402
import smichut  # noqa: E402
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


# Сверено с Dicta по одному сочетанию за запрос (чтобы соседние не давали
# друг другу контекст). Шесть сошлись; два — промахи Dicta на омографах,
# наши формы верны.
CHECKED = {
    "אֲרוּחַת הַצָּהֳרַיִם", "בֵּית הַמִּרְקַחַת", "בֵּית הַסֵּפֶר",
    "בֵּית הַקָּפֶה", "בֵּית הַכְּנֶסֶת", "נְמַל הַתְּעוּפָה",
}

# ------------------------------------------------------------- данные
# Каждая пара в упражнении — из размеченных в hebrew_meta.
known = set(hebrew_meta.SMICHUT)
stray = []
for ru, _en, right, _w, frame in smichut.SENTENCES:
    if frame == "construct" and right not in known:
        stray.append(f"{ru}: {right}")
check("пара не из размеченных", stray)

# Первое слово в смихуте обязано отличаться от исходного — иначе
# выбирать не из чего, и вопрос был бы с одинаковыми вариантами.
same = [s for s in smichut.SENTENCES if s[2] in [w for w, _r in s[3]]]
check("верный вариант совпал с неверным", same, lambda s: s[0])

# ----------------------------------------------- одно правило на вариант
def split2(text):
    parts = text.split(" ", 1)
    return parts if len(parts) == 2 else (text, "")


wrong_rule = []
for ru, _en, right, wrongs, frame in smichut.SENTENCES:
    r1, r2 = split2(right)
    for wrong, rule in wrongs:
        w1, w2 = split2(wrong)
        if rule == "construct":
            # Меняется только первое слово — оно стоит в исходной форме,
            # второе остаётся как было.
            if w2 != r2 or w1 == r1:
                wrong_rule.append(f"{ru}: «{wrong}» — не только первое слово")
        elif rule == "article":
            # На первом слове появился артикль — это и есть ошибка.
            if not w1.startswith(syntax.THE):
                wrong_rule.append(f"{ru}: «{wrong}» — артикля на первом нет")
check("неверный вариант нарушает не то правило", wrong_rule)

# ------------------------------------------------ формы с артиклем
article_right = {s[2] for s in smichut.SENTENCES if s[4] == "article"}
# Артикль стоит на втором слове и только на нём.
misplaced = [r for r in article_right
             if split2(r)[0].startswith(syntax.THE)
             or not split2(r)[1].startswith(syntax.THE)]
check("в верном ответе артикль не на втором слове", misplaced)

# Всё, что упражнение показывает с артиклем, должно быть сверено. Не
# наоборот: сверено больше, чем показывается, — «אֲרוּחַת הַצָּהֳרַיִם»
# проверена, но в упражнение не идёт, потому что первое слово на
# гортанную. Первый заход требовал обратного и падал на этом.
checked = {norm(x) for x in CHECKED}
check("форма с артиклем не сверена",
      [x for x in article_right if norm(x) not in checked])

# ------------------------------------------------------------ карточки
pool = quiz.POOLS["smichut"]
check("карточек нет", [] if pool else ["пусто"])
check("карточка без неверного варианта", [c.cid for c in pool if not c.wrong])
check("разбор не называет правило",
      [s[0] for s in smichut.SENTENCES
       for w, _r in s[3] if not smichut.rule_of(s[2], w)])

one = [c.ru for c in pool if len(c.wrong) < 2]
print(f"\nкарточек: {len(pool)}; с одним неверным вариантом: {len(one)}")
print("  (там первое слово на гортанную — артикль у неё другой, и честного "
      "второго варианта нет)")
if fails:
    print(f"\nСБОЕВ: {len(fails)}")
    sys.exit(1)
