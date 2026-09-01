# -*- coding: utf-8 -*-
"""Три крупных рисунка: ночной город в шапке, сцена в блоке
«Продолжить» и фон страницы.

Все в том же плоском языке, что и карточки тем, но каждый под свою
подложку: шапка синяя, карточка бумажная, фон почти невидим.
"""
from art_kit import P, rect, circ, dome, cypress, windows, crenel, arch_win, gabled, tower
from art_kit import SAND, SAND2, OCHRE, TAUPE, STONE, BROWN, DARK, OLIVE, OLIVE2, CREAM, TERRA, SKY, SKY2

# ---------------------------------------------------------------- шапка
# Синий градиент шапки — от #3A6EA0 к #234A76. Силуэты берём темнее его,
# окна тёплые: ночной город узнаётся именно по разнице температур.
FAR   = "#3B6E9C"
MID   = "#2A5583"
NEAR  = "#1C3E68"
LIGHT = "#F0D294"
MOON  = "#F4E7C6"


def _lights(x, y, n, gap, w=2.4, h=3, op=".85"):
    return "".join(
        f'<rect x="{round(x+i*gap,1)}" y="{y}" width="{w}" height="{h}" '
        f'rx=".8" fill="{LIGHT}" opacity="{op}"/>' for i in range(n))


def night_city():
    """Ночной силуэт: три плана вглубь, чтобы шапка не выглядела наклейкой."""
    b = []
    b.append(circ(272, 26, 13, MOON))
    b.append(f'<circle cx="278" cy="20" r="11" fill="#2C5A8C"/>')   # серп
    for x, y, r in ((36, 20, 1.3), (72, 34, 1), (120, 16, 1.4), (168, 28, 1),
                    (206, 18, 1.2), (240, 40, 1), (300, 52, 1.1), (94, 52, 1)):
        b.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{MOON}" opacity=".55"/>')

    # дальний план
    b.append(f'<g opacity=".45" fill="{FAR}">')
    b.append(rect(0, 82, 44, 48, FAR) + dome(22, 82, 22, FAR))
    b.append(rect(52, 90, 38, 40, FAR) + dome(71, 90, 19, FAR))
    b.append(rect(120, 86, 30, 44, FAR))
    b.append(rect(190, 92, 44, 38, FAR) + dome(212, 92, 22, FAR))
    b.append(rect(268, 88, 52, 42, FAR))
    b.append("</g>")

    # средний план
    b.append(rect(-4, 100, 60, 30, MID) + dome(26, 100, 30, MID))
    b.append(tower(96, 130, 16, 46, MID, "cone"))
    b.append(rect(150, 104, 56, 26, MID) + dome(178, 104, 28, MID))
    b.append(rect(236, 98, 40, 32, MID))
    b.append(gabled(288, 106, 34, 24, 14, MID))
    b.append(_lights(160, 112, 5, 9))
    b.append(_lights(242, 106, 4, 9))

    # передний план — стена с зубцами, как в старом городе
    b.append(rect(-4, 114, 328, 20, NEAR))
    b.append(crenel(-4, 114, 328, 17, 5, NEAR))
    b.append(_lights(6, 120, 16, 20, 3, 4, ".9"))
    b.append(cypress(66, 130, 40, 7, NEAR, NEAR))
    b.append(cypress(224, 130, 34, 6, NEAR, NEAR))
    b.append(arch_win(130, 134, 14, 18, "#12294A"))
    return "".join(b)


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
