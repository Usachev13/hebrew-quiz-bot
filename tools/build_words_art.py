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
MAP = HERE.parent / "word_art.py"
START = "<!-- картинки к словам: собираются tools/build_words_art.py -->"
END = "<!-- конец картинок к словам -->"


def collect():
    """Карта «ключ карточки -> номер картинки» и сам спрайт.

    Сами модули art_w_*.py по-прежнему пишутся по-русски: их правят
    руками, и `"хлеб": <рисунок>` читается, а `"food:לחם"` нет.

    А вот в страницу карта уезжает под УСТОЙЧИВЫМ ключом карточки. Пока
    интерфейс был одноязычным, ключом служило русское слово, и это
    работало. С английским сломалось бы молча: приложение искало бы
    картинку по подсказке «bread», не находило и рисовало пустоту —
    все 273 рисунка исчезли бы, не уронив ничего и не написав ни строчки
    в журнал.
    """
    art = {}
    for m in MODULES:
        art.update(m.W)
    order = quiz.POOLS["vocab"]
    known = {c.ru for c in order}
    unknown = [k for k in art if k not in known]
    if unknown:
        raise SystemExit(f"картинки без слов в словаре: {unknown}")
    missing = [c.ru for c in order if c.ru not in art]
    if missing:
        print(f"без картинки осталось {len(missing)}: {missing[:8]}…")
    drawn = [c for c in order if c.ru in art]
    keys = {c.key(): f"i{i}" for i, c in enumerate(drawn)}
    sprite = "\n".join(
        f'<g id="w-{keys[c.key()]}" stroke="#FAF5EA" stroke-width="1.1" '
        f'stroke-linejoin="round">{art[c.ru]}</g>'
        for c in drawn)
    return keys, sprite, len(order)


def main():
    """Спрайт — отдельным файлом, карта — на сервер, страница чистая.

    Картинки внутри страницы весили 21 КБ под сжатием и грузились при
    каждом открытии, хотя нужны лишь когда человек начал раунд и у всех
    одинаковы. Отдельный файл браузер забирает один раз и кэширует.
    Ссылаться на него через <use href="words.svg#..."> нельзя: во многих
    вебвью внешние ссылки в use не работают, поэтому приложение
    подгружает файл текстом и вставляет в свой же документ.

    Карта «слово -> номер картинки» раньше тоже лежала в странице, и
    клиент искал по ней сам. Теперь она уезжает в word_art.py, а номер
    приходит вместе с карточкой. Две причины, и вторая важнее первой:

    1. Со страницы уходит 19 КБ, которые грузились всегда, а нужны были
       только на экране знакомства.
    2. Искать было не по чему. Ключом служило русское слово; с
       английским интерфейсом подсказка стала бы «bread», в карте её
       нет — и все 273 рисунка исчезли бы, не уронив ничего и не
       написав ни строчки в журнал. Теперь номер приходит от того же
       кода, который карточку и собрал, и разойтись им негде.
    """
    keys, sprite, total = collect()
    SPRITE.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" '
        'style="position:absolute" aria-hidden="true"><defs>\n'
        + sprite + "\n</defs></svg>\n", encoding="utf-8")

    MAP.write_text(
        '# -*- coding: utf-8 -*-\n'
        '"""Ключ карточки -> номер её картинки в static/words.svg.\n\n'
        'Файл СОБИРАЕТСЯ автоматически: tools/build_words_art.py.\n'
        'Править руками бессмысленно — перезапишется при первой же\n'
        'пересборке спрайта. Рисунки лежат в tools/art_w_*.py.\n"""\n\n'
        'ART = ' + json.dumps(keys, ensure_ascii=False, indent=4) + '\n',
        encoding="utf-8")

    # Старый блок с картой вырезаем: страница о ней больше не знает.
    page = PAGE.read_text(encoding="utf-8")
    if START in page:
        page = re.sub(re.escape(START) + ".*?" + re.escape(END) + r"\n?",
                      "", page, flags=re.S)
        PAGE.write_text(page, encoding="utf-8")

    print(f"картинок {len(keys)} из {total} слов; "
          f"{SPRITE.name} {len(SPRITE.read_bytes()) // 1024} КБ, "
          f"{MAP.name} {len(MAP.read_bytes()) // 1024} КБ, "
          f"страница {len(page.encode()) // 1024} КБ")


if __name__ == "__main__":
    main()
