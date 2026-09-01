# -*- coding: utf-8 -*-
"""
Проверка страницы Mini App без браузера.

Появилась после того, как правка вырезала из скрипта половину функций
вместе с той, которую убирали: `node --check` смотрит только синтаксис,
а вызов несуществующей функции для него законен. Приложение при этом
падало на первом же экране, и заметить это можно было только на
телефоне.

Запуск:
    python3 tools/check_app.py
"""

import re
import sys
from pathlib import Path

PAGE = Path(__file__).resolve().parent.parent / "static" / "app.html"

# Всё, что определяет сам язык, браузер или SDK Telegram, — не наши
# функции, и искать их определение в файле не нужно.
BUILTIN = {
    "if", "for", "while", "switch", "catch", "function", "return", "typeof",
    "await", "async", "new", "fetch", "setTimeout", "setInterval",
    "requestAnimationFrame", "matchMedia", "Audio", "parseInt", "parseFloat",
    "isNaN", "alert", "confirm", "encodeURIComponent", "decodeURIComponent",
    # методы, которые ловятся регуляркой как вызовы
    "map", "join", "filter", "find", "split", "replace", "forEach", "push",
    "includes", "then", "querySelectorAll", "querySelector", "getElementById",
    "createElement", "appendChild", "addEventListener", "toUpperCase",
    "toLowerCase", "trim", "slice", "stringify", "parse", "play", "focus",
    "scrollTo", "add", "remove", "toggle", "startsWith", "endsWith", "pop",
    "sort", "reduce", "some", "every", "indexOf", "repeat", "toFixed", "now",
    "random", "floor", "round", "min", "max", "abs", "pow", "test", "exec",
    "match", "setAttribute", "getAttribute", "performance", "keys", "values",
    # SDK Telegram и функции CSS, попадающие под ту же регулярку
    "hide", "show", "expand", "ready", "onEvent", "onClick", "json",
    "impactOccurred", "notificationOccurred", "setBackgroundColor",
    "setHeaderColor", "hsl", "calc", "translateY", "scale", "blur", "url",
    "rgba", "var", "rotate", "gradient", "onclick",
}


def check(html):
    js = re.findall(r"<script>(.*?)</script>", html, re.S)[-1]
    problems = []

    # 1. Вызовы функций, которых нет. Ради этого всё и затевалось.
    decls = {}
    for m in re.finditer(r"(?:const|let|var)\s+(\w+)\s*=", js):
        decls.setdefault(m.group(1), []).append(m.start())
    defined = set(decls) | set(re.findall(r"function\s+(\w+)\s*\(", js)) | {"tg"}
    calls = set(re.findall(r"(?<![\w.$])([a-z][A-Za-z0-9_]*)\s*\(", js))
    missing = sorted(calls - defined - BUILTIN)
    if missing:
        problems.append(f"вызовы без определения: {missing}")

    # 2. Повторные объявления на верхнем уровне — признак того, что кусок
    #    вставили дважды. Считаем только объявления без отступа: внутри
    #    разных функций одноимённые локальные переменные — норма, а вот
    #    два `const tap` в корне скрипта роняют страницу целиком.
    top = {}
    for m in re.finditer(r"^(?:const|let|var)\s+(\w+)\s*=", js, re.M):
        top.setdefault(m.group(1), 0)
        top[m.group(1)] += 1
    dups = {k: v for k, v in top.items() if v > 1}
    if dups:
        problems.append(f"объявлено дважды в корне: {dups}")

    # 3. Обращения к элементам, которых нет в разметке.
    ids = set(re.findall(r"""id=["']([\w-]+)["']""", html))
    refs = set(re.findall(r'\$\("([\w-]+)"\)', js))
    if refs - ids:
        problems.append(f"нет таких элементов: {sorted(refs - ids)}")

    # 4. Переходы на несуществующие экраны.
    screens = set(re.findall(r'id="s-(\w+)" class="screen', html))
    shown = set(re.findall(r'show\("(\w+)"', js))
    if shown - screens:
        problems.append(f"нет таких экранов: {sorted(shown - screens)}")

    # 5. Значки и рисунки, которых нет в спрайте.
    sprite = set(re.findall(r'id="i-([\w-]+)"', html))
    used = set(re.findall(r'icon\("([\w-]+)"', js))
    if used - sprite:
        problems.append(f"нет таких значков: {sorted(used - sprite)}")
    sketches = set(re.findall(r'id="sk-(\w+)"', html))
    if not sketches:
        problems.append("наброски тем потерялись")

    # 6. Эмодзи вместо значков — правило оформления, легко нарушить правкой.
    emoji = re.findall(r"[\U0001F300-\U0001FAFF]", html)
    if emoji:
        problems.append(f"эмодзи в разметке: {set(emoji)}")

    return problems, len(defined), len(sketches)


def main():
    if not PAGE.exists():
        print("Страница не найдена:", PAGE)
        return 1
    html = PAGE.read_text(encoding="utf-8")
    problems, defined, sketches = check(html)
    print(f"Страница: {len(html) // 1024} КБ, функций {defined}, набросков {sketches}")
    if problems:
        for p in problems:
            print("  СБОЙ", p)
        return 1
    print("  Всё на месте.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
