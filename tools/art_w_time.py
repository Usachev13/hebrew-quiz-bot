# -*- coding: utf-8 -*-
"""Время (21), покупки (14), работа и учёба (14)."""
import math
from art_wkit import *

W = {}

def _sun(cx, cy, r, c=OCHRE, rays=8, r1=None, r2=None):
    r1 = r1 or r + 6; r2 = r2 or r + 14
    out = circ(cx, cy, r, c)
    for i in range(rays):
        a = i * (2 * math.pi / rays)
        out += P(f"M{cx+r1*math.cos(a):.1f} {cy+r1*math.sin(a):.1f} "
                 f"L{cx+r2*math.cos(a):.1f} {cy+r2*math.sin(a):.1f} Z", "none").replace(
            'fill="none"', f'fill="none" stroke="{c}" stroke-width="4" '
            'stroke-linecap="round"')
    return out

def _clock(h, m, r=30, cx=50, cy=50):
    ha = math.radians((h % 12) * 30 + m * 0.5 - 90)
    ma = math.radians(m * 6 - 90)
    return (circ(cx, cy, r, CREAM) + circ(cx, cy, r, "none").replace('fill="none"',
                f'fill="none" stroke="{TAUPE}" stroke-width="4"')
            + P(f"M{cx} {cy} L{cx+r*0.5*math.cos(ha):.1f} {cy+r*0.5*math.sin(ha):.1f} Z",
                "none").replace('fill="none"',
                f'fill="none" stroke="{DARK}" stroke-width="4.5" stroke-linecap="round"')
            + P(f"M{cx} {cy} L{cx+r*0.78*math.cos(ma):.1f} {cy+r*0.78*math.sin(ma):.1f} Z",
                "none").replace('fill="none"',
                f'fill="none" stroke="{DARK}" stroke-width="3" stroke-linecap="round"')
            + circ(cx, cy, 3, TERRA))

def _cal(mark=None, rows=3, cols=5, top=RED):
    out = rect(14, 24, 72, 58, CREAM, 4) + rect(14, 24, 72, 14, top, 4)
    out += rect(28, 18, 6, 12, BROWN, 3) + rect(66, 18, 6, 12, BROWN, 3)
    for r in range(rows):
        for c in range(cols):
            x, y = 21 + c * 13, 44 + r * 12
            on = mark is not None and (r * cols + c) == mark
            out += rect(x, y, 9, 8, TERRA if on else STONE, 2)
    return out

# ---------------------------------------------------------------- время
W["день"] = (rect(4, 60, 92, 18, SAND) + _sun(50, 40, 18))
W["ночь"] = (rect(4, 16, 92, 62, "#2A4A72", 5)
             + P("M62 28 a16 16 0 1 0 12 26 a19 19 0 0 1-12-26 Z", CREAM)
             + circ(26, 34, 2, CREAM) + circ(40, 26, 1.6, CREAM)
             + circ(22, 54, 1.6, CREAM) + circ(46, 46, 2, CREAM)
             + rect(4, 66, 92, 12, "#1C3E68"))
W["утро"] = (rect(4, 56, 92, 22, SAND) + rect(4, 20, 92, 36, "#F0D9B8", 3)
             + circ(50, 56, 20, OCHRE)
             + "".join(P(f"M{50+26*math.cos(a):.1f} {56+26*math.sin(a):.1f} "
                         f"L{50+34*math.cos(a):.1f} {56+34*math.sin(a):.1f} Z", "none")
                       .replace('fill="none"', f'fill="none" stroke="{OCHRE}" '
                                'stroke-width="4" stroke-linecap="round"')
                       for a in (3.53, 3.93, 4.32, 4.71, 5.10, 5.50, 5.89)))
W["вечер"] = (rect(4, 18, 92, 40, "#8A5F72", 4) + rect(4, 56, 92, 22, TAUPE)
              + circ(50, 56, 20, TERRA)
              + rect(14, 44, 10, 12, DARK) + rect(76, 40, 10, 16, DARK))
W["полдень"] = (rect(4, 62, 92, 16, SAND) + _sun(50, 26, 16)
                + P("M42 62 h16 l-4 -14 h-8 Z", TAUPE))
W["неделя"] = (_cal(rows=1, cols=7, top=BLUE2).replace('width="9"', 'width="8"')
               .replace('x="21"', 'x="18"') + rect(18, 44, 60, 2, GAP))
W["месяц"] = _cal(rows=4)
W["год"] = (_cal(rows=3) + rect(30, 6, 40, 14, OCHRE, 3)
            + rect(36, 10, 28, 6, CREAM, 2))
W["час"] = _clock(3, 0)
W["минута"] = (_clock(12, 1) + circ(50, 50, 34, "none").replace('fill="none"',
                   f'fill="none" stroke="{TERRA}" stroke-width="2" '
                   'stroke-dasharray="3 5"'))
W["сегодня"] = _cal(mark=7)
W["вчера"] = (_cal(mark=6) + P("M84 60 l-10 -8 v16 Z", TAUPE))
W["завтра"] = (_cal(mark=8) + P("M16 60 l10 -8 v16 Z", TAUPE))
W["сейчас"] = (_clock(10, 10, r=26)
               + P("M50 12 v-6 M50 88 v6", "none").replace('fill="none"',
                   f'fill="none" stroke="{TERRA}" stroke-width="4" stroke-linecap="round"'))
W["потом"] = (_clock(2, 0, r=24, cx=42)
              + P("M74 50 h16 M82 40 l10 10 l-10 10", "none").replace('fill="none"',
                  f'fill="none" stroke="{TAUPE}" stroke-width="4.5" '
                  'stroke-linecap="round" stroke-linejoin="round"'))
W["всегда"] = (P("M30 50 c0 -12 12 -12 20 0 c8 12 20 12 20 0 "
                 "c0 -12 -12 -12 -20 0 c-8 12 -20 12 -20 0 Z", "none").replace(
                   'fill="none"', f'fill="none" stroke="{TERRA}" stroke-width="9" '
                   'stroke-linecap="round" stroke-linejoin="round"'))
W["никогда"] = (_clock(4, 20, r=26)
                + P("M28 28 l44 44", "none").replace('fill="none"',
                    f'fill="none" stroke="{GAP}" stroke-width="11" '
                    'stroke-linecap="round"')
                + P("M28 28 l44 44", "none").replace('fill="none"',
                    f'fill="none" stroke="{RED}" stroke-width="7" '
                    'stroke-linecap="round"'))
W["иногда"] = ("".join(circ(20 + i * 15, 50, 7, TERRA if i in (0, 2, 4) else STONE)
                       for i in range(5)))
W["воскресенье"] = (_cal(mark=0, rows=1, cols=7).replace('width="9"', 'width="8"')
                    .replace('x="21"', 'x="18"'))
W["понедельник"] = (_cal(mark=1, rows=1, cols=7).replace('width="9"', 'width="8"')
                    .replace('x="21"', 'x="18"'))
W["суббота"] = (_cal(mark=6, rows=1, cols=7, top=BLUE2).replace('width="9"', 'width="8"')
                .replace('x="21"', 'x="18"')
                + rect(40, 6, 6, 14, CREAM) + rect(54, 6, 6, 14, CREAM)
                + rect(47, 6, 6, 14, CREAM) + rect(36, 18, 28, 4, OCHRE, 2))

# ------------------------------------------------------------- покупки
W["деньги"] = (shadow(rx=28) + rect(12, 34, 62, 30, OLIVE, 3)
               + rect(20, 40, 62, 30, OLIVE2, 3)
               + circ(51, 55, 10, CREAM) + rect(48, 48, 6, 14, OLIVE2, 2))
W["цена"] = (shadow(rx=24) + P("M20 46 L54 22 l24 24 l-34 24 Z", OCHRE)
             + circ(58, 38, 5, CREAM)
             + rect(30, 66, 40, 14, CREAM, 3)
             + rect(36, 70, 8, 6, TERRA, 1) + rect(48, 70, 16, 6, TAUPE, 1))
W["дорогой (по цене)"] = (shadow(rx=26)
                          + "".join(circ(50, 74 - i * 9, 18, OCHRE if i % 2 else SAND2)
                                    for i in range(6))
                          + P("M78 40 v-18 M70 30 l8 -10 l8 10", "none").replace(
                              'fill="none"', f'fill="none" stroke="{TERRA}" '
                              'stroke-width="5" stroke-linecap="round" '
                              'stroke-linejoin="round"'))
W["дешёвый"] = (shadow(rx=26)
                + "".join(circ(50, 74 - i * 9, 18, OCHRE if i % 2 else SAND2)
                          for i in range(2))
                + P("M78 34 v18 M70 44 l8 10 l8 -10", "none").replace(
                    'fill="none"', f'fill="none" stroke="{OLIVE2}" stroke-width="5" '
                    'stroke-linecap="round" stroke-linejoin="round"'))
W["скидка"] = (shadow(rx=26) + P("M18 44 L52 20 l26 26 l-34 24 Z", TERRA)
               + circ(58, 36, 5, CREAM)
               + P("M32 62 l24 -24", "none").replace('fill="none"',
                   f'fill="none" stroke="{CREAM}" stroke-width="4" stroke-linecap="round"')
               + circ(34, 44, 5, CREAM) + circ(52, 60, 5, CREAM))
W["счёт (в кафе)"] = (shadow(rx=24) + P("M26 16 h48 v58 l-8 -6 l-8 6 l-8 -6 l-8 6 "
                                        "l-8 -6 l-8 6 Z", CREAM)
                      + rect(34, 26, 32, 4, TAUPE, 2) + rect(34, 36, 24, 4, TAUPE, 2)
                      + rect(34, 46, 28, 4, TAUPE, 2) + rect(34, 58, 18, 5, TERRA, 2))
W["касса"] = (shadow(rx=28) + rect(16, 44, 68, 32, SAND2, 3)
              + rect(24, 22, 40, 22, CREAM, 3) + rect(30, 28, 28, 10, DARK, 2)
              + "".join(rect(24 + i * 14, 52, 10, 8, TAUPE, 2) for i in range(4))
              + "".join(rect(24 + i * 14, 64, 10, 8, TAUPE, 2) for i in range(4)))
W["кредитная карта"] = (shadow(rx=28) + rect(12, 32, 76, 46, BLUE2, 5)
                        + rect(12, 42, 76, 10, DARK)
                        + rect(20, 58, 18, 12, OCHRE, 2)
                        + rect(44, 64, 36, 5, CREAM, 2))
W["сдача"] = (shadow(rx=28) + circ(30, 62, 14, OCHRE) + circ(30, 62, 8, SAND)
              + circ(56, 66, 11, OCHRE) + circ(56, 66, 6, SAND)
              + circ(72, 54, 9, STONE) + circ(72, 54, 5, CREAM)
              + P("M26 30 h30 M46 22 l10 8 l-10 8", "none").replace('fill="none"',
                  f'fill="none" stroke="{TAUPE}" stroke-width="4" '
                  'stroke-linecap="round" stroke-linejoin="round"'))
W["шекель"] = (shadow(rx=24) + circ(50, 50, 30, OCHRE) + circ(50, 50, 24, SAND)
               + P("M36 66 V34 h12 a10 10 0 0 1 10 10 v10", "none").replace(
                   'fill="none"', f'fill="none" stroke="{BROWN}" stroke-width="6" '
                   'stroke-linecap="round" stroke-linejoin="round"')
               + P("M64 34 v32 H52 a10 10 0 0 1 -10 -10 V46", "none").replace(
                   'fill="none"', f'fill="none" stroke="{BROWN}" stroke-width="6" '
                   'stroke-linecap="round" stroke-linejoin="round"'))
W["продавец"] = (shadow(rx=28) + rect(8, 58, 84, 8, SAND2, 2)
                 + rect(14, 66, 6, 14, BROWN) + rect(80, 66, 6, 14, BROWN)
                 + figure(50, 58, 44, TERRA, HAIR_D)
                 + rect(30, 50, 16, 8, CREAM, 2) + rect(58, 50, 14, 8, OCHRE, 2))
W["клиент"] = (shadow(rx=26) + figure(38, 80, 52, BLUE2, HAIR_D)
               + P("M62 50 h26 l-3 30 h-20 Z", SAND2)
               + P("M68 50 v-6 a8 8 0 0 1 14 0 v6", "none").replace('fill="none"',
                   f'fill="none" stroke="{SAND2}" stroke-width="3"'))
W["сумка"] = (shadow(rx=26) + P("M22 36 h56 l5 44 H17 Z", TERRA)
              + P("M38 36 V26 a12 12 0 0 1 24 0 v10", "none").replace('fill="none"',
                  f'fill="none" stroke="{BROWN}" stroke-width="4"'))
W["пакет"] = (shadow(rx=26) + P("M24 34 h52 l4 46 H20 Z", CREAM)
              + P("M38 34 V24 a12 10 0 0 1 24 0 v10", "none").replace('fill="none"',
                  f'fill="none" stroke="{TAUPE}" stroke-width="3.5"')
              + rect(30, 46, 40, 6, OLIVE, 2))

# ------------------------------------------------------- работа и учёба
W["работа"] = (shadow(rx=28) + rect(18, 40, 64, 40, BROWN, 4)
               + rect(38, 30, 24, 10, BROWN, 2) + rect(42, 34, 16, 6, SAND2, 1)
               + rect(18, 56, 64, 6, SAND2)
               + rect(44, 52, 12, 14, OCHRE, 2))
W["офис"] = (shadow(rx=30) + rect(14, 24, 72, 54, SAND)
             + windows(20, 30, 4, 3, 12, 12, 4, 4, BLUE)
             + rect(40, 66, 20, 12, DARK))
W["начальник"] = (shadow(rx=24) + figure(50, 80, 58, DARK, HAIR_D)
                  + rect(42, 44, 16, 6, TERRA, 1)
                  + P("M50 50 l-4 14 h8 Z", TERRA)
                  + P("M34 20 l6 -10 l4 8 l6 -12 l6 12 l4 -8 l6 10 Z", OCHRE))
W["зарплата"] = (shadow(rx=28) + P("M18 34 h54 l10 10 v30 H18 Z", CREAM)
                 + rect(18, 34, 54, 12, TERRA)
                 + rect(28, 54, 32, 5, TAUPE, 2)
                 + circ(62, 62, 11, OCHRE) + rect(59, 56, 6, 14, SAND, 2))
W["урок"] = (shadow(rx=30) + rect(14, 18, 72, 42, OLIVE2, 3)
             + rect(20, 24, 60, 30, "#3E5540")
             + rect(28, 30, 34, 4, CREAM, 2) + rect(28, 40, 26, 4, CREAM, 2)
             + rect(38, 62, 24, 6, SAND2, 2) + rect(14, 62, 20, 6, SAND2, 2))
W["учитель"] = (shadow(rx=28) + rect(6, 16, 46, 36, OLIVE2, 3)
                + rect(11, 21, 36, 26, "#3E5540")
                + rect(16, 27, 24, 4, CREAM, 2)
                + figure(72, 80, 54, TERRA, HAIR_D)
                + P("M60 46 L44 34", "none").replace('fill="none"',
                    f'fill="none" stroke="{SKIN}" stroke-width="7" stroke-linecap="round"'))
W["ученик"] = (shadow(rx=24) + figure(46, 80, 46, OCHRE, HAIR_D)
               + rect(66, 44, 20, 26, TERRA, 3)
               + P("M70 44 v-4 a6 6 0 0 1 12 0 v4", "none").replace('fill="none"',
                   f'fill="none" stroke="{TERRA}" stroke-width="3"'))
W["студент"] = (shadow(rx=24) + figure(50, 80, 52, BLUE2, HAIR_D)
                + P("M28 30 L50 20 l22 10 l-22 10 Z", DARK)
                + rect(48, 30, 4, 12, DARK) + circ(50, 44, 3, OCHRE))
W["книга"] = (shadow(rx=28) + P("M16 70 q17 -8 34 0 V32 q-17 -8 -34 0 Z", CREAM)
              + P("M50 70 q17 -8 34 0 V32 q-17 -8 -34 0 Z", SAND)
              + rect(48, 32, 4, 38, BROWN)
              + "".join(rect(22, 40 + i * 8, 22, 3, TAUPE, 1.5) for i in range(3))
              + "".join(rect(56, 40 + i * 8, 22, 3, TAUPE, 1.5) for i in range(3)))
W["тетрадь"] = (shadow(rx=24) + rect(24, 20, 52, 60, CREAM, 3)
                + rect(24, 20, 10, 60, TERRA, 3)
                + "".join(rect(38, 30 + i * 9, 30, 3, TAUPE, 1.5) for i in range(5))
                + "".join(circ(29, 30 + i * 14, 2.4, GAP) for i in range(4)))
W["ручка"] = (shadow(rx=22) + f'<g transform="rotate(30 50 50)">'
              + rect(44, 14, 12, 48, BLUE2, 3)
              + P("M44 62 h12 l-6 16 Z", OCHRE)
              + rect(44, 14, 12, 8, DARK, 3) + rect(57, 22, 4, 16, BLUE, 2) + '</g>')
W["вопрос"] = (shadow(rx=24) + circ(50, 50, 30, BLUE2)
               + P("M38 40 q0 -12 12 -12 q12 0 12 12 q0 10 -12 12 v6", "none").replace(
                   'fill="none"', f'fill="none" stroke="{WHITE}" stroke-width="7" '
                   'stroke-linecap="round"')
               + circ(50, 68, 4.5, WHITE))
W["ответ"] = (shadow(rx=24) + circ(50, 50, 30, OLIVE)
              + P("M36 50 v-8 q0 -8 14 -8 q14 0 14 8 v16 q0 8 -14 8 q-14 0 -14 -8",
                  "none").replace('fill="none"',
                  f'fill="none" stroke="{WHITE}" stroke-width="0"')
              + P("M34 52 l12 14 l22 -28", "none").replace('fill="none"',
                  f'fill="none" stroke="{WHITE}" stroke-width="7" '
                  'stroke-linecap="round" stroke-linejoin="round"'))
W["экзамен"] = (shadow(rx=26) + rect(22, 16, 56, 66, CREAM, 3)
                + rect(30, 26, 40, 5, TAUPE, 2)
                + "".join((rect(30, 40 + i * 12, 6, 6, OLIVE if i == 0 else STONE, 1.5)
                           + rect(42, 40 + i * 12, 28, 4, TAUPE, 2)) for i in range(3))
                + circ(68, 72, 12, TERRA) + P("M62 72 l5 6 l9 -12", "none").replace(
                    'fill="none"', f'fill="none" stroke="{WHITE}" stroke-width="4" '
                    'stroke-linecap="round" stroke-linejoin="round"'))
