# -*- coding: utf-8 -*-
"""
Огласовщик Dicta Nakdan: расставляет никуд в ивритском тексте.

Что это и зачем
---------------
Nakdan — бесплатный открытый огласовщик Бар-Иланского университета
(группа Дикта). Он разбирает КОНТЕКСТ, а не отдельное слово, и поэтому
различает то, чего не различить по буквам: `ספר` в разных фразах выйдет
и «сефер», и «сапар», и «сипер».

Нужен он нам в двух совершенно разных ролях, и путать их нельзя.

1. В РАЗГОВОРЕ он источник. Собеседника ведёт языковая модель, своих
   огласовок у нас там нет вовсе, а просить их у модели оказалось
   ненадёжно: она отвечала «שלום, אני בסדר» без единого значка, и наша
   транскрипция выдавала «шлвм, нй всдр». Nakdan эту дыру закрывает.

2. В БАНКЕ он второе мнение, и только. Словарь, спряжения и формы
   множественного выверены словарями, таблицами форм и Академией, слово
   за словом. Класть машинную огласовку поверх выверенной — шаг назад,
   даже если она совпадает в девяноста восьми случаях из ста. Польза в
   РАСХОЖДЕНИЯХ: каждое из них — повод перепроверить, как это уже
   сработало со словарями (18 ошибок в спряжениях, 5 в множественном).

Об устройстве службы
--------------------
Это бесплатная академическая служба без ключей и без объявленных
пределов. Отсюда два правила приличия, встроенных ниже: пауза между
запросами и кэш на диске, чтобы одно и то же слово не спрашивать
дважды. Прогон всего банка — это десятки тысяч слов, и делать его надо
редко и по одному разу.

Адрес и формат запроса сняты с самой страницы nakdan.dicta.org.il
(сентябрь 2026): заголовок Content-Type НЕ ставим намеренно — с ним
браузер и curl уходят в preflight, а служба его не разрешает.
"""

import json
import os
import time
import unicodedata
from pathlib import Path

import requests

API = os.environ.get("NAKDAN_API",
                     "https://nakdan-u2-1a.loadbalancer.dicta.org.il/api")

# Предел поля на их странице — 5000 знаков. Берём с запасом: длинный
# запрос дольше идёт и при обрыве теряется целиком.
MAX_CHARS = 2000

# Пауза между запросами. Служба бесплатная и чужая.
PAUSE = 0.4
TIMEOUT = 30

CACHE_PATH = Path(os.environ.get(
    "NAKDAN_CACHE",
    Path(__file__).resolve().parent / "audio" / "nakdan_cache.json"))

# Разделитель приставки в ответе: «בְּ|קִילוֹ». Нам он не нужен.
PREFIX_MARK = "|"

# Метег — вертикальная чёрточка под буквой, знак ритма для чтеца. Dicta
# ставит его охотно, мы не ставим нигде, и в ответе собеседника он
# выглядел соринкой: «אֲנִי נֹוֽעַם». Снимаем — на чтение он не влияет, а
# наш разбор огласовок о нём не знает.
METEG = "\u05bd"

_cache = None


def _load_cache():
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _cache = {}
    return _cache


def save_cache():
    cache = _load_cache()
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=0),
                              encoding="utf-8")
    except OSError as e:
        print(f"[nakdan] кэш не сохранился: {e}")


def strip_niqqud(text):
    return "".join(c for c in (text or "") if not unicodedata.combining(c))


def _request(text):
    body = json.dumps({
        "task": "nakdan", "data": text, "genre": "modern",
        "addmorph": True, "keepmetagim": True, "keepqq": False,
        "nodageshdefmem": False, "patachma": False, "useTokenization": True,
    }, ensure_ascii=False).encode("utf-8")
    r = requests.post(API, data=body, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


HOLAM = "\u05b9"
KUBUTS = "\u05bb"
DAGESH = "\u05bc"
VAV = "\u05d5"


def holam_on_vav(text):
    """Холам с буквы перед голым вавом — на сам вав.

    Dicta записывает «о» как холам на предыдущей букве плюс голый вав:
    «יֹופִי». Во всём нашем банке «о» записано иначе — холамом на самом
    ваве: «יוֹפִי». Звук один, запись разная, но наше чтение по первой
    записи принимало вав за согласную: «йовфи», «новам». Выравниваем на
    выходе огласовщика, чтобы всё дальше видело одну запись.
    """
    groups = []
    for ch in text or "":
        if unicodedata.combining(ch):
            if groups:
                groups[-1][1].append(ch)
        else:
            groups.append([ch, []])
    for i in range(len(groups) - 1):
        letter, marks = groups[i]
        nxt, nxt_marks = groups[i + 1]
        if nxt != VAV or nxt_marks:
            continue
        if HOLAM in marks:
            marks.remove(HOLAM)
            nxt_marks.append(HOLAM)
        # То же с «у»: Dicta пишет кубуц на букве перед голым вавом —
        # «מְעֻולָּה», а у нас «у» записано шуруком, вавом с точкой внутри:
        # «מְעוּלָה». Наше чтение принимало голый вав за согласную и
        # выдавало «меувла». Кубуц переносим на вав как шурук.
        elif KUBUTS in marks:
            marks.remove(KUBUTS)
            nxt_marks.append(DAGESH)
    return "".join(l + "".join(m) for l, m in groups)


def _assemble(payload):
    """Собирает огласованный текст из ответа.

    Ответ — список кусочков. У разделителей (пробелы, знаки) стоит
    sep=true и текст лежит прямо в `word`. У слов выбранный вариант —
    первый в `options`: именно его показывает их собственная страница.
    """
    out = []
    for item in payload.get("data", []):
        if isinstance(item, str):
            out.append(item)
            continue
        node = item.get("nakdan") or {}
        if node.get("sep"):
            out.append(node.get("word", ""))
            continue
        options = node.get("options") or []
        word = options[0].get("w") if options else node.get("word", "")
        word = (word or "").replace(PREFIX_MARK, "").replace(METEG, "")
        out.append(holam_on_vav(word))
    return "".join(out)


def vocalize(text, use_cache=True):
    """Огласованный текст. При сбое возвращает исходный, не падая.

    Огласовки на входе снимаем: иначе служба получает смесь своих и
    чужих значков и отвечает тем же. Нам нужно ЕЁ мнение целиком, а не
    поверх нашего — иначе сверка сравнивала бы наши данные сами с собой.
    """
    text = (text or "").strip()
    if not text:
        return ""
    bare = strip_niqqud(text)
    cache = _load_cache()
    if use_cache and bare in cache:
        return cache[bare]
    try:
        result = _assemble(_request(bare))
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"[nakdan] {e}")
        return text
    if result:
        cache[bare] = result
    time.sleep(PAUSE)
    return result or text


def vocalize_many(texts, progress=None):
    """Огласовка списка строк одним прогоном, с кэшем и склейкой.

    Строки склеиваются в один запрос через перевод строки: служба
    разбирает контекст, и отдельное слово она огласует хуже, чем слово
    во фразе. Но склеивать РАЗНЫЕ фразы в одну строку нельзя — контекст
    перемешается, поэтому разделяем переводом строки, который она
    возвращает как разделитель.
    """
    cache = _load_cache()
    todo = [t for t in texts if strip_niqqud(t) not in cache]
    done = 0
    batch, size = [], 0
    for text in todo:
        bare = strip_niqqud(text)
        if size + len(bare) > MAX_CHARS and batch:
            _run_batch(batch, cache)
            done += len(batch)
            if progress:
                progress(done, len(todo))
            batch, size = [], 0
        batch.append(bare)
        size += len(bare) + 1
    if batch:
        _run_batch(batch, cache)
        done += len(batch)
        if progress:
            progress(done, len(todo))
    save_cache()
    return [cache.get(strip_niqqud(t), t) for t in texts]


def _run_batch(batch, cache):
    try:
        payload = _request("\n".join(batch))
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"[nakdan] пачка не прошла ({e}), спрашиваю по одной")
        for text in batch:
            got = vocalize(text)
            if got:
                cache[text] = got
        return
    joined = _assemble(payload)
    parts = joined.split("\n")
    if len(parts) != len(batch):
        # Разошлось — значит склейка не сохранилась. Не гадаем, какой
        # кусок чей: спрашиваем по одному, это дороже, но честно.
        print(f"[nakdan] пачка вернулась другой длины "
              f"({len(parts)} против {len(batch)}), спрашиваю по одной")
        for text in batch:
            got = vocalize(text)
            if got:
                cache[text] = got
        return
    for text, got in zip(batch, parts):
        if got.strip():
            cache[text] = got.strip()
    time.sleep(PAUSE)


# ------------------------------------------- наши формы важнее машинных
#
# Проба на тридцати фразах дала семь расхождений, и почти все — промахи
# самого Nakdan, а не наши:
#
#     הַקֻּפָּה (касса)      -> הַקָּפֶה (кофе)
#     שְׁנַיִם (два)         -> שָׁנִים (годы)
#     לִקְבֹּעַ (назначить)  -> לְקַבֵּעַ (закрепить)
#     לַחֲזֹר (повторить)    -> לְחַזֵּר (ухаживать)
#     לִפְתֹּחַ (открыть)    -> לְפַתֵּחַ (развивать)
#
# Видно, где он слаб: короткая фраза без контекста, и он выбирает не тот
# биньян. Наши же формы для этих слов выверены словарями.
#
# Отсюда правило: ЕСЛИ СЛОВО ЕСТЬ У НАС — БЕРЁМ НАШЕ. Nakdan заполняет
# только то, чего мы не знаем. Так его сила (контекст, омографы) работает
# там, где у нас нет ничего, и не переписывает то, что уже проверено.

_known = None


_ambiguous = None


def ambiguous_forms():
    """Скелеты, у которых в банке несколько прочтений: שָׁם и שֵׁם."""
    known_forms()
    return _ambiguous


def known_forms():
    """{согласный скелет: наша огласованная форма} — только однозначные.

    Первый заход брал для скелета первую попавшуюся форму. Для омографов
    это ловушка: в банке есть и שָׁם («там»), и שֵׁם («имя»), скелет у них
    один, и подмена брала первое. Модель правильно писала «что делаешь
    שָׁם», а наш слой «исправлял» на שֵׁם — то есть портил верное. Ровно
    так же он портил бы и правильный ответ Dicta.

    Теперь скелет с несколькими прочтениями в подмену не идёт вовсе: какое
    из них имелось в виду, решает контекст, а контекст знает модель или
    огласовщик, но не наш словарь.
    """
    global _known, _ambiguous
    if _known is not None:
        return _known
    readings = {}

    def add(word):
        word = (word or "").strip(".,!?:;…«»\"'()")
        if not word or "|" in word:
            return
        bare = strip_niqqud(word)
        if bare and bare != word:
            readings.setdefault(bare, set()).add(_norm_marks(word))

    try:
        import phrases
        from conjugations import CONJUGATIONS
        from words import VOCAB, VERBS
        for bank in (VOCAB, VERBS):
            for _cat, pairs in bank.items():
                for _ru, he in pairs:
                    add(he)
        for data in CONJUGATIONS.values():
            add(data["inf"])
            for tense in ("past", "present", "future"):
                for form in data[tense].values():
                    add(form)
        for _sit, item in phrases.all_phrases():
            for field in ("he", "he_f", "to_f"):
                for word in (item.get(field) or "").split():
                    add(word)
    except Exception as e:                                   # noqa: BLE001
        print(f"[nakdan] банк не прочитался: {e}")
    _known = {bare: next(iter(forms)) for bare, forms in readings.items()
              if len(forms) == 1}
    _ambiguous = {bare: sorted(forms) for bare, forms in readings.items()
                  if len(forms) > 1}
    return _known


def _norm_marks(word):
    """Одна запись для одного прочтения: порядок знаков при букве разный
    у разных источников, и без этого «одно» слово считалось бы двумя."""
    groups = []
    for ch in holam_on_vav(word):
        if unicodedata.combining(ch):
            if groups:
                groups[-1][1].append(ch)
        else:
            groups.append([ch, []])
    return "".join(l + "".join(sorted(m)) for l, m in groups)


def vocalize_trusted(text):
    """Огласовка, где наши выверенные формы важнее машинных.

    Порядок именно такой: сначала спрашиваем Nakdan (он разбирает
    контекст), потом возвращаем НАШИ формы всем словам, которые у нас
    есть. Наоборот было бы хуже: подставив своё до запроса, мы лишили бы
    его контекста, по которому он и различает омографы.
    """
    got = vocalize(text)
    if not got:
        return text
    return trusted_overlay(got)


def trusted_overlay(got):
    """Наши выверенные формы поверх любых огласовок — Dicta или модели."""
    ours = known_forms()
    out = []
    for word in got.split():
        core = word.strip(".,!?:;…«»\"'()")
        tail = word[len(core):] if core else ""
        mine = ours.get(strip_niqqud(core))
        out.append((mine or core) + tail)
    return " ".join(out)
