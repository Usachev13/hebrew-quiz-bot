# -*- coding: utf-8 -*-
"""
Проверка «собери фразу».

Что здесь проверяется и почему именно это
-----------------------------------------
Слова в этом упражнении не сочинены: существительные и их род — из
nouns.py, где род подтверждён словарём; прилагательные — четырьмя
формами из словарных таблиц; глагол — из conjugations.py, прогнанного
через словарь форм целиком. Проверка следит, чтобы так и осталось:
любое слово, которое кто-нибудь впишет здесь руками, всплывёт.

Риск в этом упражнении не в словах, а в НЕВЕРНЫХ вариантах. Если
неверный вариант отличается от верного больше, чем одним нарушенным
правилом, разбор соврёт: он назовёт одно правило, а ошибок в ответе
было две. Поэтому главная проверка — про это.

Артикль. `definite()` приклеивает הַ и ставит дагеш в первую букву. Это
не выведено из книги, а взято из наших же фраз: в банке 17 определённых
форм с дагешем и ни одной без него, кроме слов на ח, которая дагеш
принять не может. Проверка сверяет сгенерированные формы с теми, что уже
есть в банке фраз, — там, где они встречаются.

Правильность каркасов машина не проверяет. Их пять, они ушли Вадиму.
"""

import os
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import nouns  # noqa: E402
import phrases  # noqa: E402
import quiz  # noqa: E402
import words  # noqa: E402
import syntax  # noqa: E402
from conjugations import CONJUGATIONS  # noqa: E402

fails = []


def check(title, bad, show=lambda x: x):
    if bad:
        fails.append(title)
        print(f"  СБОЙ {title}: {len(bad)}")
        for item in bad[:8]:
            print(f"     {show(item)}")
        if len(bad) > 8:
            print(f"     … ещё {len(bad) - 8}")
    else:
        print(f"✓ {title} — не найдено")


def strip_niqqud(word):
    return "".join(c for c in word if not unicodedata.combining(c))


# ---------------------------------------------------------------- слова
# Каждое ивритское слово в упражнении должно находиться в проверенных
# данных. Ищем по согласному скелету: совпадения огласовок требовать
# нельзя, потому что прилагательное меняет их по роду.
KNOWN = set()
for he, *_ in syntax.NOUNS:
    KNOWN.add(strip_niqqud(he))
for forms in (v[1] for v in syntax.ADJECTIVES.values()):
    for f in forms:
        KNOWN.add(strip_niqqud(f))
for data in CONJUGATIONS.values():
    for tense in ("past", "present", "future"):
        for form in data.get(tense, {}).values():
            if form:
                KNOWN.add(strip_niqqud(form))
# Служебные слова каркаса. Их немного, и они перечислены здесь нарочно:
# новое служебное слово должно попасть в этот список осознанно.
SERVICE = {"אני", "את", "יש", "אין", "לי", "לא", "ה"}

unknown = []
for ru, en, right, wrongs, frame in syntax.SENTENCES:
    for variant in [right] + [w for w, _ in wrongs]:
        for token in variant.split():
            bare = strip_niqqud(token)
            if bare in SERVICE or bare in KNOWN:
                continue
            # слово с приклеенным артиклем
            if bare.startswith("ה") and bare[1:] in KNOWN:
                continue
            unknown.append((frame, token, variant))
check("слово не из проверенных данных", unknown,
      lambda x: f"{x[1]} в «{x[2]}» ({x[0]})")

# ---------------------------------------- род прилагательного и слова
wrong_gender = []
for he, ru_nom, _acc, _gen, _rug, _anim, _en in syntax.NOUNS:
    g = nouns.gender_of(he)
    if g not in (nouns.M, nouns.F):
        wrong_gender.append((he, ru_nom, g))
check("род существительного не размечен", wrong_gender,
      lambda x: f"{x[0]} ({x[1]}) — {x[2]!r}")

# -------------------------------------------- один вариант — одно правило
# Неверный вариант обязан отличаться от верного ровно тем, что названо.
# Проверяем формально: набор слов и порядок.
def words_of(s):
    return s.split()


def diff_kind(right, wrong):
    """Чем именно отличается неверный вариант."""
    r, w = words_of(right), words_of(wrong)
    if sorted(r) == sorted(w) and r != w:
        return "порядок"
    if len(r) == len(w) and sum(a != b for a, b in zip(r, w)) == 1:
        return "одно слово"
    if len(w) == len(r) + 1 and all(x in w for x in r):
        return "слово добавлено"
    if len(w) == len(r) - 1 and all(x in r for x in w):
        return "слово убрано"
    # Содержательное слово на месте, разошлись только служебные: это
    # целиком другая конструкция вокруг того же слова — «אֲנִי יֵשׁ בַּיִת»
    # вместо «יֵשׁ לִי בַּיִת». Ошибка здесь одна, хотя слов сменилось два.
    content_r = [x for x in r if strip_niqqud(x) not in SERVICE]
    content_w = [x for x in w if strip_niqqud(x) not in SERVICE]
    if content_r and content_r == content_w:
        return "другая конструкция"
    if len(r) == len(w):
        return f"слов разошлось: {sum(a != b for a, b in zip(r, w))}"
    return f"длина {len(r)} против {len(w)}"


# Какое расхождение допустимо для каждого правила. Правило «одно слово»
# у agree и verb_agree — это и есть замена формы; у order — перестановка;
# et и yesh_li добавляют или убирают служебное слово.
ALLOWED = {
    "order": {"порядок"},
    "agree": {"одно слово"},
    "verb_agree": {"одно слово"},
    "definite": {"одно слово"},
    "et": {"слово добавлено", "слово убрано"},
    "yesh": {"другая конструкция"},
    "yesh_li": {"слово убрано", "другая конструкция"},
}

multi = []
for ru, en, right, wrongs, frame in syntax.SENTENCES:
    for wrong, rule in wrongs:
        kind = diff_kind(right, wrong)
        if kind not in ALLOWED.get(rule, set()):
            multi.append((frame, rule, kind, right, wrong))
check("неверный вариант отличается не только названным правилом", multi,
      lambda x: f"[{x[0]}/{x[1]}] {x[2]}: {x[3]} -> {x[4]}")

# Неверный вариант не должен совпадать с верным.
same = [(f, r, w) for ru, en, r, ws, f in syntax.SENTENCES
        for w, _ in ws if w == r]
check("неверный вариант совпал с верным", same, lambda x: f"{x[0]}: {x[1]}")

# И два неверных не должны совпадать между собой — иначе в вопросе
# окажется два одинаковых варианта, как когда-то в огласовках.
twins = [(f, ws) for ru, en, r, ws, f in syntax.SENTENCES
         if len({w for w, _ in ws}) != len(ws)]
check("два неверных варианта одинаковы", twins, lambda x: x[0])

# --------------------------------------- разбор обязан назвать правило
mute = []
for ru, en, right, wrongs, frame in syntax.SENTENCES:
    for wrong, rule in wrongs:
        for lang in ("ru", "en"):
            if not syntax.rule_of(right, wrong, lang):
                mute.append((frame, rule, lang))
check("разбор не нашёл правила для неверного варианта", mute,
      lambda x: f"{x[0]}/{x[1]} [{x[2]}]")

# ---------------------------------------------------- артикль и дагеш
# Сверка с определёнными формами, которые уже есть в банке фраз.
# Слова в банке идут со знаками препинания («הַדִּירָה?»), и без их
# снятия сверка молча не находила ни одной формы — ровно та же ловушка,
# что дала «хадира́х» в транслитерации.
TAIL = ".,!?:;\u2026\u00ab\u00bb\"'()"
bank = set()


def _harvest(value):
    if isinstance(value, str):
        bank.update(w.strip(TAIL) for w in value.split())
    elif isinstance(value, dict):
        for v in value.values():
            _harvest(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _harvest(v)


for items in phrases.PHRASES.values():
    for item in items:
        _harvest(item)

def norm(word):
    """Порядок огласовок при букве у разных источников разный.

    Тот же нормализатор, что в check_conjugations: без него сверка
    сообщает о расхождении там, где строки отличаются только порядком
    комбинирующих знаков.
    """
    out = []
    for ch in word:
        if unicodedata.combining(ch):
            out[-1] += ch
        else:
            out.append(ch)
    return "".join(g[0] + "".join(sorted(g[1:])) for g in out)


# Все огласованные слова, какие у нас есть, — по ним узнаём, какое слово
# стоит под артиклем в банке фраз. Ключ — САМО слово с огласовками, а не
# скелет: по скелету «קָפֶה» (кофе) и «קֻפָּה» (касса) сливаются в одно, и
# сверка отчитывается о расхождении, которого нет. Эта ловушка тут уже
# отняла время, и не один раз.
VOCALIZED = {}
for cat, items in words.VOCAB.items():
    for _ru, he in items:
        VOCALIZED.setdefault(norm(he), he)
for he in nouns.NOUNS:
    VOCALIZED.setdefault(norm(he), he)
for he, *_ in syntax.NOUNS:
    VOCALIZED.setdefault(norm(he), he)

# Определённые формы банка: по ним и построен definite(). Слово под
# артиклем ищем целиком, с огласовками, сняв артикль и дагеш, который
# артикль же и поставил.
article = []
witnessed = 0
gutturals = []
for token in sorted(bank):
    plain = strip_niqqud(token)
    if not plain.startswith("ה") or len(plain) < 3:
        continue
    # снять артикль: первую букву с её огласовкой и дагеш следующей
    groups = []
    for ch in token:
        if unicodedata.combining(ch):
            groups[-1] += ch
        else:
            groups.append(ch)
    stem_groups = groups[1:]
    stem_groups[0] = stem_groups[0].replace(syntax.DAGESH, "", 1)
    stem = norm("".join(stem_groups))
    source = VOCALIZED.get(stem)
    if not source:
        continue
    if not syntax.simple_article(source):
        # Гортанные и ר: артикль у них другой (הָ, без дагеша). Это и есть
        # причина, по которой такие слова в упражнение не берутся, —
        # свидетели из банка, а не рассуждение.
        gutturals.append((token, source))
        continue
    witnessed += 1
    if norm(syntax.definite(source)) != norm(token):
        article.append((source, syntax.definite(source), token))
check("артикль разошёлся с банком фраз", article,
      lambda x: f"{x[0]}: собрано {x[1]}, в банке {x[2]}")

# Обратная сторона того же: у исключённых слов артикль в банке и правда
# не наш. Если вдруг окажется наш — значит, исключение можно снимать, и
# об этом надо знать.
wrongly_out = [(t, s) for t, s in gutturals
               if norm(t) == norm(syntax.THE + s)]
check("исключённое слово берёт обычный артикль — исключение лишнее",
      wrongly_out, lambda x: f"{x[1]} -> {x[0]}")


# Само правило — на всех определённых формах, какие есть в банке фраз, а
# не только на наших двенадцати словах. Именно эти свидетели и есть
# основание для definite(): дагеш стоит всюду, кроме букв, которые его
# принять не могут.
rule_bad = []
seen_forms = 0
for token in sorted(bank):
    bare = strip_niqqud(token)
    if not token.startswith(syntax.THE) or len(bare) < 3:
        continue
    seen_forms += 1
    stem_letter = bare[1]
    has_dagesh = syntax.DAGESH in token[2:5]
    if stem_letter in "אהחער":
        if has_dagesh:
            rule_bad.append((token, "дагеш на букве, которая его не берёт"))
    elif not has_dagesh:
        rule_bad.append((token, "нет дагеша после артикля"))
check("определённая форма в банке противоречит правилу дагеша", rule_bad,
      lambda x: f"{x[0]} — {x[1]}")

# Слова на гортанную и ר в упражнение не попадают: у них меняется
# огласовка артикля, и правилом мы её не выводим.
leaked = [he for he, *_ in syntax.NOUNS
          if syntax.simple_article(he) and strip_niqqud(he)[0] in "אהחער"]
check("слово с гортанной прошло в упражнение", leaked)

# ------------------------------------------------------------- карточки
pool = quiz.POOLS["syntax"]
bad_cards = [c for c in pool if len(c.wrong) < 2]
check("у карточки меньше двух неверных вариантов", bad_cards,
      lambda c: f"{c.cid}: {c.ru}")

dup = len({c.cid for c in pool}) != len(pool)
check("ключи карточек повторяются", ["да"] if dup else [])

no_en = [c for c in pool if not c.en]
check("нет английской подсказки", no_en, lambda c: c.cid)

# Внутри одного пула верный ответ одной карточки может быть неверным
# вариантом другой только по правилу определённости: הַבַּיִת גָּדוֹל —
# правильное предложение и неправильный ответ на «этот большой дом».
# Это и есть смысл второго правила. Любое другое пересечение — ошибка.
cross = []
for female in (False, True):
    p = quiz.syntax_pool(female)
    right = {c.he for c in p}
    for c in p:
        for w in c.wrong:
            if w not in right:
                continue
            rule = next(r for ww, r in
                        next(s[3] for s in syntax.SENTENCES if s[2] == c.he)
                        if ww == w)
            if rule != "definite":
                cross.append((c.cid, rule, w))
check("верный ответ одной карточки стал неверным у другой "
      "(кроме определённости)", cross, lambda x: f"{x[0]} / {x[1]}: {x[2]}")

# Карточки с формой глагола по роду говорящего разведены по полу: если
# они попадут в один пул, упражнение объявит неверной правильную форму.
mixed = [c.cid for c in quiz.syntax_pool(False) if c.cat == "et_f_sg"]
mixed += [c.cid for c in quiz.syntax_pool(True) if c.cat == "et_m_sg"]
check("карточка чужого рода попала в пул", mixed)

print()
print(f"фраз: {len(syntax.SENTENCES)}, карточек в пуле: {len(pool)}, "
      f"правил: {len(syntax.RULES)}")
print(f"определённых форм: {witnessed} сверено с банком слово в слово "
      f"(и {len(gutturals)} отведено как гортанные), "
      f"{seen_forms} проверено на правило дагеша")
print("Каркасов пять, их правильность — к носителю: они в ВОПРОСЫ_ВАДИМУ.md")
if fails:
    print(f"\nСБОЕВ: {len(fails)}")
    sys.exit(1)
