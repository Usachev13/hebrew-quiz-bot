# -*- coding: utf-8 -*-
"""Три крупных рисунка: ночной город в шапке, сцена в блоке
«Продолжить» и фон страницы.

Все в том же плоском языке, что и карточки тем, но каждый под свою
подложку: шапка синяя, карточка бумажная, фон почти невидим.
"""
from art_kit import P, rect, circ, dome, cypress, windows, crenel, arch_win, gabled, tower
from art_kit import SAND, SAND2, OCHRE, TAUPE, STONE, BROWN, DARK, OLIVE, OLIVE2, CREAM, TERRA, SKY, SKY2

# ---------------------------------------------------------------- шапка
# Рисунок намеренно шире карточки: 420×164 при её пропорции от 1.76 до
# 2.43 на разных телефонах. При slice масштаб берётся по большей нехватке;
# раз наша пропорция 2.56 больше любой из них, он всегда считается по
# высоте, и срезаются только края. Стена обязана стоять ровно под полосой
# недели, а срез снизу увёл бы её.
NW, NH = 420, 164
SHIFT = 45
WALL_TOP = 116

# Небо каждого времени суток затемнено ровно настолько, чтобы белый текст
# прошёл 4.5:1. Небо дня пришлось притушить на 16 % — иначе подпись
# «Готов продолжить?» давала 2.9:1 и переставала читаться.
# (верх, середина, дальний план, средний план, стена, светило, окна)
TIMES = {
    "dawn":  ("#3B4A7C", "#6B5F92", "#5A6494", "#3F4874", "#2B3358",
              "#F0B183", 4),
    "day":   ("#2A6BA6", "#346D9E", "#6BA3D0", "#4C86B4", "#2E5C8A",
              "#FBF0C8", 0),
    "dusk":  ("#3A3A6B", "#7E4A68", "#7C5478", "#54405E", "#33253F",
              "#EE8C4E", 10),
    "night": ("#2A4A72", "#1F3A5E", "#3B6E9C", "#2A5583", "#1C3E68",
              "#F4E7C6", 18),
}
LIGHT = "#F0D294"


def _lights(x, y, n, gap, w=2.6, h=3.4, op=".85"):
    return "".join(
        f'<rect x="{round(x+i*gap,1)}" y="{y}" width="{w}" height="{h}" '
        f'rx=".9" fill="{LIGHT}" opacity="{op}"/>' for i in range(n))


def _celestial(part, glow):
    """Солнце или луна. Рисуется поверх дальнего плана, но под средним:
    так оно висит в небе, а не приклеено к крышам. Место выбрано не на
    глаз — выше поставить негде: слева аватар, посередине имя, справа
    кольцо серии, а на узком телефоне свободного неба по краям вовсе не
    остаётся."""
    if part == "night":
        return (f'<circle cx="151" cy="84" r="24" fill="{glow}" opacity=".10"/>'
                f'<path d="M151 70 a14 14 0 1 0 10.5 23 a16.5 16.5 0 0 1-10.5-23 Z" '
                f'fill="{glow}"/>')
    y = {"dawn": 92, "day": 82, "dusk": 96}[part]
    r = {"dawn": 15, "day": 14, "dusk": 17}[part]
    out = f'<circle cx="151" cy="{y}" r="{r+11}" fill="{glow}" opacity=".14"/>'
    if part == "day":
        # Лучи только у полудня: на рассвете и закате солнце у горизонта
        # и лучей не даёт.
        for i in range(8):
            import math
            a = math.radians(i * 45)
            x1, y1 = 151 + (r + 5) * math.cos(a), y + (r + 5) * math.sin(a)
            x2, y2 = 151 + (r + 11) * math.cos(a), y + (r + 11) * math.sin(a)
            out += (f'<path d="M{x1:.1f} {y1:.1f} L{x2:.1f} {y2:.1f}" '
                    f'stroke="{glow}" stroke-width="3" stroke-linecap="round" '
                    f'opacity=".7"/>')
    return out + circ(151, y, r, glow)


def _town(part, far, mid, glow, lit, stars):
    """Небо и два дальних плана. Рисуются в системе 330 и сдвигаются."""
    b = []
    if stars:
        for x, y, r in ((22, 16, 1.3), (58, 34, 1), (104, 14, 1.5), (150, 30, 1),
                        (192, 18, 1.2), (232, 40, 1), (286, 22, 1.3), (312, 46, 1),
                        (78, 56, 1.1), (256, 60, 1), (-24, 28, 1.1), (352, 32, 1.2)):
            b.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#F4E7C6" '
                     f'opacity="{min(.5, stars/40):.2f}"/>')

    b.append('<g opacity=".38">')
    for r in (rect(-50, 84, 44, 32, far), rect(-6, 76, 52, 40, far),
              dome(20, 76, 26, far), rect(58, 82, 44, 34, far),
              rect(112, 72, 38, 44, far), dome(131, 72, 19, far),
              rect(164, 80, 50, 36, far), rect(226, 74, 42, 42, far),
              dome(247, 74, 21, far), rect(280, 82, 56, 34, far),
              rect(340, 78, 46, 38, far), dome(363, 78, 23, far)):
        b.append(r)
    b.append("</g>")

    b.append(_celestial(part, glow))

    b.append('<g opacity=".72">')
    for r in (rect(-46, 96, 40, 20, mid), rect(-6, 92, 56, 24, mid),
              dome(22, 92, 28, mid), tower(84, 116, 15, 42, mid, "cone"),
              rect(126, 94, 52, 22, mid), dome(152, 94, 26, mid),
              rect(196, 88, 36, 28, mid), gabled(248, 96, 32, 20, 13, mid),
              rect(292, 90, 44, 26, mid), tower(346, 116, 14, 38, mid, "dome")):
        b.append(r)
    b.append("</g>")
    if lit:
        for x, y, n, gap in ((132, 102, 5, 9), (202, 96, 3, 9), (300, 98, 4, 9),
                             (8, 100, 3, 10), (254, 106, 3, 8), (-40, 102, 2, 9)):
            b.append(_lights(x, y, n, gap, op=f"{min(.7, lit/26):.2f}"))
    return "".join(b)


def hero(part):
    """Город в заданное время суток. Композиция одна и та же — меняются
    только цвета и светило, поэтому четыре шапки читаются как одно место
    в разные часы, а не как четыре картинки."""
    top, mid_sky, far, mid, near, glow, lit = TIMES[part]
    b = [f'<g transform="translate({SHIFT} 0)">'
         f'{_town(part, far, mid, glow, lit, lit)}</g>']
    b.append(rect(-4, WALL_TOP, NW + 8, NH - WALL_TOP + 6, near))
    b.append(crenel(-4, WALL_TOP, NW + 8, 22, 6, near))
    b.append(cypress(105, WALL_TOP, 36, 7, near, near))
    b.append(cypress(267, WALL_TOP, 32, 6, near, near))
    b.append(arch_win(211, NH, 15, 18, "#12294A"))
    if lit:
        b.append(_lights(8, 146, 20, 21, 3.4, 4.8, f"{min(.9, .3 + lit/26):.2f}"))
    return "".join(b)


def night_city():
    """Совместимость со старым вызовом."""
    return hero("night")


# ------------------------------------------------------- блок «Продолжить»
def resume_scene():
    """Городские ворота на закате. Важное — справа: слева лежит текст."""
    b = []
    b.append(rect(-2, -2, 304, 194, "#F6EFE0"))
    b.append(rect(-2, 96, 304, 96, "#EFE4CE"))
    b.append(circ(214, 62, 42, "#E8CE97"))
    for x, y, k in ((96, 26, 1.1), (118, 40, .9), (258, 30, 1)):
        b.append(P(f"M{x-3*k} {y} q{3*k} {-2.4*k} {3*k} 0 q0 {-2.4*k} {3*k} 0 "
                   f"q{-3*k} {1.3*k} {-3*k} {-0.4*k} q0 {1.7*k} {-3*k} {0.4*k} Z",
                   "#C0AA82"))
    b.append(cypress(158, 176, 96, 15, "#8E9A78", "#A08A6A"))
    b.append(cypress(292, 176, 84, 13, "#7C8968", "#A08A6A"))
    b.append(tower(178, 176, 26, 76, SAND2, "dome"))
    b.append(rect(206, 118, 52, 58, SAND))
    b.append(dome(232, 118, 26, OCHRE))
    b.append(rect(258, 132, 30, 44, STONE))
    b.append(rect(168, 146, 128, 30, TAUPE))
    b.append(crenel(168, 146, 128, 11, 8, TAUPE))
    b.append(windows(176, 156, 8, 1, 6, 8, 9, 0, DARK))
    b.append(windows(212, 128, 2, 1, 7, 9, 10, 0, DARK))
    b.append(windows(264, 140, 2, 1, 6, 7, 9, 0, DARK))
    b.append(arch_win(232, 176, 20, 26, "#7A5A3E"))
    return "".join(b)


# ---------------------------------------------------------------- фон
def backdrop():
    """Дюны и море под карточками. Контраст намеренно почти нулевой:
    фон должен читаться боковым зрением и не мешать тексту."""
    b = []
    b.append(P("M0 210 C90 178 180 214 280 190 C360 170 400 186 400 186 V300 H0 Z",
               "#D9C9A6"))
    b.append(P("M0 246 C80 222 170 254 260 234 C330 218 400 232 400 232 V300 H0 Z",
               "#CDBB96"))
    b.append(cypress(48, 214, 74, 12, "#9FA88C", "#B5A184"))
    b.append(cypress(74, 220, 56, 10, "#939D80", "#B5A184"))
    b.append(cypress(348, 224, 62, 11, "#9FA88C", "#B5A184"))
    b.append(rect(126, 196, 40, 26, "#CFC0A0") + dome(146, 196, 20, "#C7B694"))
    b.append(rect(174, 204, 30, 18, "#C7B694"))
    b.append(rect(212, 200, 24, 22, "#CFC0A0") + dome(224, 200, 12, "#C7B694"))
    b.append(P("M0 268 C70 256 140 276 210 266 C290 254 340 272 400 264 V300 H0 Z",
               "#BFB08E"))
    b.append(P("M0 284 C80 274 160 292 240 282 C310 274 360 288 400 282 V300 H0 Z",
               "#B3A382"))
    return "".join(b)
