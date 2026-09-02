#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка полноты и связности переводов.

Зачем
-----
Недостающий перевод не ломает приложение: карточка просто откатывается
на русскую подсказку. Это худший вид ошибки — молчаливый. Англоязычный
человек увидит «хороший» посреди английского интерфейса, решит, что
приложение сломано, и уйдёт, а в логах не будет ни строчки.

Ещё опаснее рассинхрон у речевых моделей: их переводы лежат под номерами
(`("daily", 0)`), и стоит переставить фразы местами, как подписи молча
разъедутся — человек увидит «How much is it?» над фразой про пакет.
Поэтому в phrases_en.py рядом с переводом хранится русский оригинал, и
здесь он сверяется дословно.

Запуск:  python3 tools/check_i18n.py
Выход 1, если хоть что-то не сходится.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import phrases            # noqa: E402
import phrases_en         # noqa: E402
import quiz               # noqa: E402


def check_cards():
    """У каждой карточки должна быть английская подсказка."""
    bad = []
    for mode, pool in quiz.POOLS.items():
        for c in pool:
            if not c.en:
                bad.append(f"{mode}: {c.ru}")
            # Ответ переводим только там, где он не на иврите. Проверить
            # это машинно нельзя без списка режимов, поэтому опираемся на
            # него же — он задан в quiz.
    return "нет английской подсказки", bad


def check_answers():
    """У карточек алфавита ответ — текст, и он тоже должен переводиться.

    Исключение — режимы, где ответом служит сама буква: её переводить
    не во что.
    """
    LETTER_IS_ANSWER = {"alef_by_name", "alef_finals"}
    bad = []
    for mode in quiz.ALPHABET_MODES - LETTER_IS_ANSWER:
        for c in quiz.POOLS[mode]:
            if not c.en_ans:
                bad.append(f"{mode}: {c.ru} -> {c.he}")
    return "ответ не переведён", bad


def check_ids():
    """Ключи внутри режима обязаны быть уникальны.

    Совпадение ключей означало бы, что две разные карточки делят одну
    коробку Лейтнера: ответ на одну переписывает расписание другой.
    """
    bad = []
    for mode, pool in quiz.POOLS.items():
        seen = {}
        for c in pool:
            if c.key() in seen:
                bad.append(f"{mode}: «{c.ru}» и «{seen[c.key()]}» -> {c.key()}")
            seen[c.key()] = c.ru
    return "два ключа совпали", bad


def check_labels():
    """Названия разделов и тем — на обоих языках."""
    bad = []
    for mode in quiz.LABELS:
        if mode not in quiz.LABELS_EN:
            bad.append(f"режим {mode}")
    for cat in quiz.TOPIC_LABELS:
        if cat not in quiz.TOPIC_LABELS_EN:
            bad.append(f"тема {cat}")
    for cat in quiz.GRAMMAR_LABELS:
        if cat not in quiz.GRAMMAR_LABELS_EN:
            bad.append(f"группа {cat}")
    return "нет английского названия раздела", bad


def check_vocab_topics():
    """У каждой категории словаря должно быть человеческое название.

    Иначе в списке слов вместо темы окажется системный ключ вроде
    `place_prepositions` — или, что хуже, название соседнего раздела,
    если сработает откат на подпись режима.
    """
    bad = []
    for c in quiz.POOLS["vocab"]:
        if c.cat not in quiz.TOPIC_LABELS and c.cat not in quiz.GRAMMAR_LABELS:
            bad.append(f"категория {c.cat} (например, «{c.ru}»)")
    return "категория словаря без названия", sorted(set(bad))


def check_phrase_alignment():
    """Русский оригинал в phrases_en должен совпадать с phrases.

    Это защита от перестановки фраз: номера остались прежними, а тексты
    под ними поменялись. Сверяем дословно.
    """
    bad = []
    for s, items in phrases.PHRASES.items():
        for i, p in enumerate(items):
            found = phrases_en.PHRASES_EN.get((s, i))
            if not found:
                bad.append(f"({s}, {i}) «{p['ru']}» — перевода нет")
                continue
            was, _en = found
            if was != p["ru"]:
                bad.append(f"({s}, {i}) было «{was}», стало «{p['ru']}» — "
                           f"проверьте, к той ли фразе привязан перевод")
    extra = set(phrases_en.PHRASES_EN) - {
        (s, i) for s, items in phrases.PHRASES.items() for i in range(len(items))
    }
    for key in sorted(extra):
        bad.append(f"{key} — перевод есть, а фразы нет")
    return "речевые модели разошлись с переводом", bad


def check_situations():
    bad = [k for k in phrases.SITUATIONS if k not in phrases_en.SITUATIONS_EN]
    return "ситуация без английского названия", bad


def check_he_en():
    """Фраза с he_en не должна зависеть от пола говорящего.

    text() смотрит he_en первым, и женская форма была бы потеряна молча.
    Пока такая фраза одна, но правило должно держаться само.
    """
    bad = [f"({s}, {i}) {p['ru']}"
           for s, items in phrases.PHRASES.items()
           for i, p in enumerate(items)
           if p.get("he_en") and p.get("he_f")]
    return "he_en вместе с he_f: женская форма потеряется", bad


# ---------------------------------------------------------------- страница

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "static", "app.html")


def _page():
    with open(PAGE, encoding="utf-8") as f:
        return f.read()


def _catalogues(page):
    """Два словаря интерфейса из app.html: {язык: множество ключей}.

    Разбираем текстом, а не запуском JS: заводить движок ради проверки
    двух списков ключей — несоразмерная цена. Формат словаря
    фиксированный (`"ключ": "текст"`), и на нём регулярного выражения
    достаточно.
    """
    # Хвост «\n}};» дописываем обратно как «\n}»: у последнего языка
    # блок закрывается вместе со всем словарём, и без этого он остался
    # бы без признака конца — разбор находил только первый язык.
    body = page[page.index("const L = {"):page.index("\n}};")] + "\n}"
    out = {}
    for lang, chunk in re.findall(r"(?m)^(ru|en): \{(.*?)(?=^\},?$)", body, re.S):
        out[lang] = set(re.findall(r'"([a-zA-Z0-9._]+)":\s*"', chunk))
    return out


def check_catalogue_parity():
    """В двух языках должны быть одни и те же ключи.

    Ключ, забытый в английском, не падает: t() молча откатится на
    русский, и человек увидит русскую надпись посреди английского
    экрана. Именно такую тихую недостачу и ловим.
    """
    cat = _catalogues(_page())
    if len(cat) != 2:
        return "словари интерфейса не разобрались", [f"нашлось языков: {sorted(cat)}"]
    bad = [f"нет в en: {k}" for k in sorted(cat["ru"] - cat["en"])]
    bad += [f"нет в ru: {k}" for k in sorted(cat["en"] - cat["ru"])]
    return "ключ есть только в одном языке", bad


def check_keys_used():
    """Каждый ключ, который вызывает код, должен быть в словаре.

    Берём только законченные литералы: за закрывающей кавычкой должна
    идти запятая или скобка. Ключи, собранные из кусков — `t("sec." +
    s.key)` — отбрасываются: в них литерал это лишь префикс, и считать
    его отсутствующим ключом было бы ложной тревогой. Полнота таких
    держится на check_catalogue_parity.
    """
    page = _page()
    cat = _catalogues(page)
    known = set().union(*cat.values()) if cat else set()
    # Комментарии выбрасываем: пример «t("x", {n: 5})» в пояснении к
    # словарю — не вызов, а текст, и первый же прогон принял его за
    # обращение к несуществующему ключу.
    script = re.sub(r"/\*.*?\*/", "", page[page.rindex("<script>"):], flags=re.S)
    script = re.sub(r"(?m)^\s*//.*$", "", script)
    used = set(re.findall(r'\bt\("([a-zA-Z0-9._]+)"\s*[,)]', script))
    used |= set(re.findall(r'\bplur\([^,]+,\s*"([a-zA-Z0-9._]+)"\s*\)', script))
    used |= set(re.findall(r'data-t(?:-aria|-ph)?="([a-zA-Z0-9._]+)"', page))
    return "код зовёт ключ, которого нет в словаре", sorted(used - known)


CHECKS = [check_cards, check_answers, check_ids, check_labels,
          check_vocab_topics, check_phrase_alignment, check_situations,
          check_he_en, check_catalogue_parity, check_keys_used]


def main():
    failed = 0
    for check in CHECKS:
        title, bad = check()
        if bad:
            failed += 1
            print(f"✗ {title}: {len(bad)}")
            for line in bad[:12]:
                print(f"    {line}")
            if len(bad) > 12:
                print(f"    … и ещё {len(bad) - 12}")
        else:
            print(f"✓ {title} — не найдено")

    total = sum(len(p) for p in quiz.POOLS.values())
    print(f"\nкарточек проверено: {total}, "
          f"речевых моделей: {sum(len(v) for v in phrases.PHRASES.values())}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
