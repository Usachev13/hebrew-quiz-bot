# -*- coding: utf-8 -*-
"""Кубики для картинок к отдельным словам.

Отличие от сцен тем: там пейзаж, тут предмет. Поэтому composition
другая — вещь по центру, лёгкая тень под ней, никакого фона-неба.
Кубики нужны, чтобы 257 картинок не превратились в 257 разных почерков:
кувшин в «еде» и кувшин в «доме» должны быть одним кувшином.

Холст 100×100. Полезная зона 12…88: по краям картинку подрезают.
"""
from art_kit import P, rect, circ, dome

SAND  = "#DCC69E"
SAND2 = "#CBAA7C"
OCHRE = "#C29F5E"
TAUPE = "#AE9878"
STONE = "#C6BBA6"
BROWN = "#8C7455"
DARK  = "#6B4F3A"
OLIVE = "#6E7A5A"
OLIVE2 = "#586348"
CREAM = "#E9E0CC"
TERRA = "#B0703C"
RED   = "#B5544A"
BLUE  = "#7FA6CC"
BLUE2 = "#4E7CA6"
WHITE = "#F4EFE2"
GAP   = "#FAF5EA"


def shadow(cx=50, cy=86, rx=26, ry=5):
    """Тень-эллипс: без неё предмет висит в пустоте."""
    return (f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
            f'fill="{TAUPE}" opacity=".35"/>')


def plate(cx=50, cy=78, w=54, fill=CREAM):
    return P(f"M{cx-w/2} {cy} h{w} a{w/2} {w/6} 0 0 1 -{w} 0 Z", fill)


def jar(cx, base, w, h, fill, neck=True):
    r = w / 3
    body = P(f"M{cx-w/2} {base} V{base-h} a{r} {r} 0 0 1 {r} {-r} "
             f"h{w-2*r} a{r} {r} 0 0 1 {r} {r} v{h} Z", fill)
    if neck:
        body += rect(cx - w/5, base - h - r - 5, 2*w/5, 5, fill, 2)
    return body


def cup(cx, base, w, h, fill, handle=True):
    out = P(f"M{cx-w/2} {base-h} h{w} l-{w*0.12} {h} h-{w*0.76} Z", fill)
    if handle:
        out += P(f"M{cx+w/2-1} {base-h+4} q{w*0.42} {h*0.16} 0 {h*0.5} "
                 f"l-3 -2 q{w*0.3} {-h*0.14} 0 {-h*0.42} Z", fill)
    return out


def bottle(cx, base, w, h, fill):
    return (P(f"M{cx-w/2} {base} V{base-h*0.62} q0 -{h*0.14} {w*0.28} -{h*0.2} "
              f"V{base-h} h{w*0.44} v{h*0.18} q{w*0.28} {h*0.06} {w*0.28} {h*0.2} "
              f"V{base} Z", fill))


def leaf(cx, cy, w, h, fill, tilt=0):
    return (f'<g transform="rotate({tilt} {cx} {cy})">'
            + P(f"M{cx} {cy+h/2} C{cx-w} {cy+h*0.1} {cx-w*0.55} {cy-h/2} {cx} {cy-h/2} "
                f"C{cx+w*0.55} {cy-h/2} {cx+w} {cy+h*0.1} {cx} {cy+h/2} Z", fill)
            + '</g>')


def person(cx, base, h, body_c, head_c=SAND2, head_r=None):
    """Фигура: голова кругом, тело куполом. Рост задаёт всё остальное."""
    hr = head_r or h * 0.22
    top = base - h
    return (circ(cx, top + hr, hr, head_c)
            + P(f"M{cx-h*0.28} {base} V{base-h*0.52} "
                f"a{h*0.28} {h*0.28} 0 0 1 {h*0.56} 0 v{h*0.52} Z", body_c))


def house(x, y, w, h, fill, roof=None, roof_c=None):
    out = rect(x, y, w, h, fill)
    if roof == "dome":
        out += dome(x + w/2, y, w/2, roof_c or fill)
    elif roof == "gable":
        out = P(f"M{x} {y+h} V{y} L{x+w/2} {y-h*0.42} L{x+w} {y} v{h} Z", fill)
    return out


def windows(x, y, cols, rows, sw, sh, gx, gy, fill=DARK):
    out = ""
    for r in range(rows):
        for c in range(cols):
            out += rect(round(x + c*(sw+gx), 1), round(y + r*(sh+gy), 1), sw, sh, fill)
    return out


def wrap(key, body):
    """Просвет между фигурами — как во всём остальном рисунке."""
    return (f'<g id="w-{key}" stroke="{GAP}" stroke-width="1.1" '
            f'stroke-linejoin="round">{body}</g>')


# ---------------------------------------------------------------- люди

HAIR_D = "#6B4F3A"      # тёмные волосы
HAIR_L = "#C29F5E"      # светлые
HAIR_G = "#9A9184"      # седые
SKIN = "#E0C49B"


def figure(cx, base, h, body_c, hair=HAIR_D, skirt=False, beard=False,
           long_hair=False, skin=SKIN, back=False):
    """Человек. Отличаются ростом, цветом одежды и причёской — этого
    хватает, чтобы мама, папа, сын и дочь не слились в одну фигуру."""
    hr = h * 0.20
    top = base - h
    cy = top + hr
    out = ""
    if long_hair:
        out += P(f"M{cx-hr*1.15} {cy} a{hr*1.15} {hr*1.15} 0 0 1 {hr*2.3} 0 "
                 f"v{h*0.30} h-{hr*0.55} v-{h*0.16} h-{hr*1.2} v{h*0.16} "
                 f"h-{hr*0.55} Z", hair)
    # back=True — фигура отвёрнута: затылок целиком в цвете волос. Так
    # «они» отличаются от «вы», где люди повёрнуты к говорящему.
    out += circ(cx, cy, hr, hair if back else skin)
    if not back:
        out += P(f"M{cx-hr} {cy-hr*0.12} a{hr} {hr} 0 0 1 {hr*2} 0 "
                 f"a{hr} {hr*0.5} 0 0 0 -{hr*2} 0 Z", hair)
    if beard:
        out += P(f"M{cx-hr*0.75} {cy+hr*0.35} a{hr*0.75} {hr*0.9} 0 0 0 "
                 f"{hr*1.5} 0 q-{hr*0.75} {hr*0.9} -{hr*1.5} 0 Z", HAIR_G)
    if skirt:
        out += P(f"M{cx} {top+hr*2} l-{h*0.14} {h*0.34} l-{h*0.16} {h*0.44} "
                 f"h{h*0.60} l-{h*0.16} -{h*0.44} Z", body_c)
    else:
        out += P(f"M{cx-h*0.24} {base} V{base-h*0.50} "
                 f"a{h*0.24} {h*0.24} 0 0 1 {h*0.48} 0 v{h*0.50} Z", body_c)
    return out


def sign(cx, cy, w, h, fill, text_c=None):
    """Табличка на столбике — для «имени», «остановки», «цены»."""
    return (rect(cx-2.5, cy, 5, 82-cy-4, BROWN)
            + rect(cx-w/2, cy-h, w, h, fill, 3))
