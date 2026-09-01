# -*- coding: utf-8 -*-
"""Ивритская надпись контурами, а не текстом.

Два довода, и оба практические.

Первый: cairo рисует текст «игрушечным» API без двунаправленной
раскладки. Иврит пишется справа налево, и строка выходит перевёрнутой —
причём заметить это может только тот, кто читает. Расставляя буквы
самостоятельно, мы задаём порядок явно.

Второй: логотип не должен зависеть от шрифтов на чужой машине. Контуры
работают везде одинаково.
"""
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _font():
    f = TTFont(FONT)
    return f, f.getGlyphSet(), f["cmap"].getBestCmap(), f["head"].unitsPerEm


def text_paths(text, size, x_right, y_base, fill):
    """Строка справа налево. x_right — правый край надписи."""
    f, gs, cmap, upm = _font()
    k = size / upm
    hmtx = f["hmtx"]

    # Ширина каждой буквы нужна заранее: мы идём справа налево и перед
    # отрисовкой очередной буквы должны знать, насколько сдвинуться.
    out, x = [], x_right
    for ch in text:
        if ch == " ":
            x -= size * 0.30
            continue
        name = cmap.get(ord(ch))
        if not name:
            continue
        adv = hmtx[name][0] * k
        x -= adv
        pen = SVGPathPen(gs)
        gs[name].draw(pen)
        d = pen.getCommands()
        if d:
            out.append(f'<path d="{d}" fill="{fill}" '
                       f'transform="translate({x:.2f} {y_base:.2f}) '
                       f'scale({k:.5f} {-k:.5f})"/>')
    return "".join(out), x_right - x


def measure(text, size):
    """Ширина строки — чтобы отцентрировать её, а не подбирать вручную."""
    f, _, cmap, upm = _font()
    hmtx, k, w = f["hmtx"], size / upm, 0.0
    for ch in text:
        if ch == " ":
            w += size * 0.30
            continue
        name = cmap.get(ord(ch))
        if name:
            w += hmtx[name][0] * k
    return w


def centered(text, size, cx, y_base, fill):
    w = measure(text, size)
    body, _ = text_paths(text, size, cx + w / 2, y_base, fill)
    return body


def text_paths_ltr(text, size, x_left, y_base, fill):
    """Слева направо — для латиницы.

    Отдельная функция появилась после того, как «Ani Lomed Ivrit»,
    пропущенное через ивритскую раскладку, вышло как «tirvI demoL inA».
    Направление письма — свойство языка, а не настройка вывода.
    """
    f, gs, cmap, upm = _font()
    k = size / upm
    hmtx = f["hmtx"]
    out, x = [], x_left
    for ch in text:
        if ch == " ":
            x += size * 0.30
            continue
        name = cmap.get(ord(ch))
        if not name:
            continue
        pen = SVGPathPen(gs)
        gs[name].draw(pen)
        d = pen.getCommands()
        if d:
            out.append(f'<path d="{d}" fill="{fill}" '
                       f'transform="translate({x:.2f} {y_base:.2f}) '
                       f'scale({k:.5f} {-k:.5f})"/>')
        x += hmtx[name][0] * k
    return "".join(out), x - x_left
