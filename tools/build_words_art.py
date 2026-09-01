# -*- coding: utf-8 -*-
"""Собирает картинки к словам в спрайт и вставляет их в static/app.html.

Запускается после правки любого из art_w_*.py:
    python3 tools/build_words_art.py

Ключом в разметке служит короткий идентификатор (i0, i1…), а не русское
слово: кириллица в id ломает выборки и заметно раздувает страницу.
Соответствие «слово → ключ» уезжает в саму страницу отдельным словарём.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import art_w_food, art_w_home        # noqa: E402
import quiz                          # noqa: E402

MODULES = (art_w_food, art_w_home)
PAGE = HERE.parent / "static" / "app.html"
START = "<!-- картинки к словам: собираются tools/build_words_art.py -->"
END = "<!-- конец картинок к словам -->"


def collect():
    art = {}
    for m in MODULES:
        art.update(m.W)
    order = [ru for ru, _, _ in quiz.POOLS["vocab"]]
    unknown = [k for k in art if k not in set(order)]
    if unknown:
        raise SystemExit(f"картинки без слов в словаре: {unknown}")
    keys = {ru: f"i{i}" for i, ru in enumerate(order) if ru in art}
    sprite = "\n".join(
        f'<g id="w-{keys[ru]}" stroke="#FAF5EA" stroke-width="1.1" '
        f'stroke-linejoin="round">{art[ru]}</g>'
        for ru in order if ru in art)
    return keys, sprite, len(order)


def main():
    keys, sprite, total = collect()
    page = PAGE.read_text(encoding="utf-8")
    block = (f"{START}\n{sprite}\n"
             f'<script>window.WORD_ART = '
             f'{json.dumps(keys, ensure_ascii=False, separators=(",", ":"))};</script>\n'
             f"{END}")
    if START in page:
        page = re.sub(re.escape(START) + ".*?" + re.escape(END), block, page, flags=re.S)
    else:
        page = page.replace("<g id=\"ground\">", block + "\n<g id=\"ground\">", 1)
    PAGE.write_text(page, encoding="utf-8")
    print(f"картинок {len(keys)} из {total} слов, "
          f"спрайт {len(sprite.encode()) // 1024} КБ")


if __name__ == "__main__":
    main()
