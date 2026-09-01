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

import art_w_food, art_w_home, art_w_city        # noqa: E402
import art_w_body, art_w_time, art_w_gram        # noqa: E402
import quiz                          # noqa: E402

MODULES = (art_w_food, art_w_home, art_w_city,
           art_w_body, art_w_time, art_w_gram)
PAGE = HERE.parent / "static" / "app.html"
SPRITE = HERE.parent / "static" / "words.svg"
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
    missing = [ru for ru in order if ru not in art]
    if missing:
        print(f"без картинки осталось {len(missing)}: {missing[:8]}…")
    keys = {ru: f"i{i}" for i, ru in enumerate(order) if ru in art}
    sprite = "\n".join(
        f'<g id="w-{keys[ru]}" stroke="#FAF5EA" stroke-width="1.1" '
        f'stroke-linejoin="round">{art[ru]}</g>'
        for ru in order if ru in art)
    return keys, sprite, len(order)


def main():
    """Спрайт кладём отдельным файлом, а в страницу — только карту.

    Внутри страницы картинки весили 21 КБ под сжатием и грузились при
    каждом открытии, хотя нужны лишь когда человек начал раунд и у всех
    одинаковы. Отдельный файл браузер забирает один раз и кэширует.
    Ссылаться на него через <use href="words.svg#..."> нельзя: во многих
    вебвью внешние ссылки в use не работают, поэтому приложение
    подгружает файл текстом и вставляет в свой же документ.
    """
    keys, sprite, total = collect()
    SPRITE.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" '
        'style="position:absolute" aria-hidden="true"><defs>\n'
        + sprite + "\n</defs></svg>\n", encoding="utf-8")

    page = PAGE.read_text(encoding="utf-8")
    block = (f"{START}\n"
             f'<script>window.WORD_ART = '
             f'{json.dumps(keys, ensure_ascii=False, separators=(",", ":"))};</script>\n'
             f"{END}")
    if START in page:
        page = re.sub(re.escape(START) + ".*?" + re.escape(END), block, page, flags=re.S)
    else:
        page = page.replace("<g id=\"ground\">", block + "\n<g id=\"ground\">", 1)
    PAGE.write_text(page, encoding="utf-8")
    print(f"картинок {len(keys)} из {total} слов; "
          f"{SPRITE.name} {len(SPRITE.read_bytes()) // 1024} КБ, "
          f"страница {len(page.encode()) // 1024} КБ")


if __name__ == "__main__":
    main()
