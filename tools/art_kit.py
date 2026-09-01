# -*- coding: utf-8 -*-
"""Словарь форм для плоских иллюстраций тем.

Стиль взят с присланного образца (наивный Иерусалим): сплошные заливки
без контура, тонкий светлый просвет между соседними фигурами, земляная
палитра, детали набираются повтором — окна, зубцы стены, камни кладки.

Рисунок 150×104 — пропорция плитки на экране. По краям он подрезается,
поэтому важное держим от края подальше.
"""
import random

# Палитра снята с образца: песчаник, охра, серо-бежевый камень, олива.
SKY    = "#F1E9DA"
SKY2   = "#E7DCC6"
SAND   = "#DCC69E"
SAND2  = "#CBAA7C"
OCHRE  = "#C29F5E"
TAUPE  = "#AE9878"
STONE  = "#C6BBA6"
BROWN  = "#8C7455"
DARK   = "#6B4F3A"
OLIVE  = "#6E7A5A"
OLIVE2 = "#586348"
CREAM  = "#E9E0CC"
TERRA  = "#B0703C"
GAP    = "#FAF5EA"          # цвет просвета между фигурами

W, H = 150, 104


def P(d, fill):
    return f'<path d="{d}" fill="{fill}"/>'


def rect(x, y, w, h, fill, r=0):
    if r:
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"/>'
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>'


def circ(cx, cy, r, fill):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>'


def dome(cx, base, r, fill):
    """Купол — полукруг на прямоугольном основании."""
    return P(f"M{cx-r} {base} v-0 a{r} {r} 0 0 1 {2*r} 0 Z", fill)


def house(x, y, w, h, fill):
    """Коробка дома."""
    return rect(x, y, w, h, fill)


def gabled(x, y, w, h, peak, fill):
    """Дом с двускатной крышей: y — верх стен, peak — высота конька."""
    return P(f"M{x} {y+h} V{y} L{x+w/2} {y-peak} L{x+w} {y} v{h} Z", fill)


def tower(x, ybase, w, h, fill, cap=None):
    """Башня с куполом или шатром."""
    out = rect(x, ybase - h, w, h, fill)
    if cap == "dome":
        out += dome(x + w / 2, ybase - h, w / 2, fill)
    elif cap == "cone":
        out += P(f"M{x} {ybase-h} L{x+w/2} {ybase-h-w*0.9} L{x+w} {ybase-h} Z", fill)
    return out


def crenel(x, y, w, n, th, fill):
    """Зубцы поверху стены — главный источник ритма на образце."""
    step = w / (2 * n - 1)
    out = ""
    for i in range(n):
        out += rect(round(x + i * 2 * step, 2), y - th, round(step, 2), th, fill)
    return out


def windows(x, y, cols, rows, sw, sh, gx, gy, fill):
    out = ""
    for r in range(rows):
        for c in range(cols):
            out += rect(round(x + c * (sw + gx), 2), round(y + r * (sh + gy), 2),
                        sw, sh, fill)
    return out


def arch_win(cx, ybase, w, h, fill):
    """Окно с полукруглым верхом."""
    r = w / 2
    return P(f"M{cx-r} {ybase} V{ybase-h+r} a{r} {r} 0 0 1 {w} 0 V{ybase} Z", fill)


def cypress(x, ybase, h, w, fill, trunk=BROWN):
    """Кипарис — вертикальный лист, как на образце."""
    top = ybase - h
    return (P(f"M{x} {ybase-6} C{x-w} {ybase-h*0.45} {x-w*0.55} {top} {x} {top} "
              f"C{x+w*0.55} {top} {x+w} {ybase-h*0.45} {x} {ybase-6} Z", fill)
            + rect(x - 0.7, ybase - 8, 1.4, 8, trunk))


def stones(y, h, seed=1, x0=-6, x1=W + 6, fill=None):
    """Кладка: ряды камней со сбитыми швами, разной ширины и тона."""
    rng = random.Random(seed)
    tones = [STONE, SAND, CREAM, SAND2, TAUPE, SKY2]
    out, yy, row = "", y, 0
    while yy < y + h:
        xx = x0 + rng.uniform(0, 6)
        while xx < x1:
            w = rng.uniform(5.5, 12.5)
            out += rect(round(xx, 1), round(yy + rng.uniform(-0.5, 0.5), 1),
                        round(w, 1), round(rng.uniform(3.6, 4.8), 1),
                        fill or rng.choice(tones), 1.4)
            xx += w + rng.uniform(1.4, 2.6)
        yy += 5.8
        row += 1
    return out


def birds(pts, fill=BROWN):
    """Птицы в небе — пара галочек, чтобы верх кадра не пустовал."""
    out = ""
    for x, y, k in pts:
        out += P(f"M{x-3*k} {y} q{3*k} {-2.2*k} {3*k} 0 q0 {-2.2*k} {3*k} 0 "
                 f"q{-3*k} {1.2*k} {-3*k} {-0.4*k} q0 {1.6*k} {-3*k} {0.4*k} Z", fill)
    return out


def scene(*parts):
    return "".join(parts)


def wrap(key, body):
    """Просвет между фигурами делаем общей обводкой цвета бумаги —
    именно так разделены соседние пятна на образце."""
    return (f'<g id="sk-{key}" stroke="{GAP}" stroke-width="1" '
            f'stroke-linejoin="round">{body}</g>')
