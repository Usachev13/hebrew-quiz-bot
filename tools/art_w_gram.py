# -*- coding: utf-8 -*-
"""Грамматические группы: 72 слова.

Здесь картинка чаще показывает не предмет, а отношение: «под» — это мяч
под столом, «третий» — место на пьедестале, «мы» — группа фигур. Для
вопросительных слов и частиц честного изображения нет вовсе, поэтому там
принят условный знак — и это оговорено в комментарии у каждого.
"""
import math
from art_wkit import *

W = {}

def _box(x=30, y=44, w=40, h=22, fill=SAND2):
    return rect(x, y, w, h, fill, 3)

def _ball(cx, cy, r=9, fill=TERRA):
    return circ(cx, cy, r, fill)

def _table(y=52):
    return (rect(14, y, 72, 7, SAND2, 2)
            + rect(20, y + 7, 6, 78 - y - 7, BROWN)
            + rect(74, y + 7, 6, 78 - y - 7, BROWN))

def _dots(n, fill=TERRA, cols=5, r=8, x0=None, y0=34, dx=19, dy=19):
    rows = (n + cols - 1) // cols
    x0 = x0 if x0 is not None else 50 - (min(n, cols) - 1) * dx / 2
    out = ""
    for i in range(n):
        c, rr = i % cols, i // cols
        cx = 50 - (min(n - rr * cols, cols) - 1) * dx / 2 + c * dx
        out += circ(cx, y0 + rr * dy + (rows - 1) * 0 , r, fill)
    return out

def _sign_arrow(text_shape, c=TERRA):
    return text_shape

# ------------------------------------------------------ прилагательные
W["хороший"] = (shadow(rx=24) + circ(50, 50, 28, OLIVE)
                + P("M36 50 l10 12 l20 -24", "none").replace('fill="none"',
                    f'fill="none" stroke="{WHITE}" stroke-width="7" '
                    'stroke-linecap="round" stroke-linejoin="round"'))
W["плохой"] = (shadow(rx=24) + circ(50, 50, 28, RED)
               + P("M38 62 l24 -24 M38 38 l24 24", "none").replace('fill="none"',
                   f'fill="none" stroke="{WHITE}" stroke-width="7" '
                   'stroke-linecap="round"'))
W["красивый"] = (shadow(rx=24) + P("M50 26 C40 12 20 18 20 34 C20 50 50 74 50 74 "
                                   "C50 74 80 50 80 34 C80 18 60 12 50 26 Z", TERRA)
                 + "".join(P(f"M{x} {y-6} Q{x} {y} {x+5} {y} Q{x} {y} {x} {y+6} "
                             f"Q{x} {y} {x-5} {y} Q{x} {y} {x} {y-6} Z", OCHRE)
                           for x, y in ((22, 18), (80, 22), (74, 66))))
W["новый"] = (shadow(rx=24) + rect(26, 34, 48, 40, CREAM, 4)
              + rect(26, 34, 48, 10, TERRA, 4)
              + "".join(P(f"M{x} {y-7} Q{x} {y} {x+6} {y} Q{x} {y} {x} {y+7} "
                          f"Q{x} {y} {x-6} {y} Q{x} {y} {x} {y-7} Z", OCHRE)
                        for x, y in ((20, 24), (82, 30), (50, 16))))
W["старый"] = (shadow(rx=24) + rect(26, 34, 48, 40, TAUPE, 4)
               + rect(26, 34, 48, 10, BROWN, 4)
               + P("M34 48 q8 6 0 12 M60 46 q-8 8 0 14", "none").replace('fill="none"',
                   f'fill="none" stroke="{BROWN}" stroke-width="2.5"')
               + P("M26 60 l14 -6 l10 8 l12 -10 l12 8", "none").replace('fill="none"',
                   f'fill="none" stroke="{STONE}" stroke-width="2.5"'))
W["большой"] = (shadow(rx=28) + circ(38, 54, 26, TERRA) + circ(78, 70, 9, SAND2))
W["маленький"] = (shadow(rx=28) + circ(38, 54, 26, SAND2) + circ(78, 70, 9, TERRA))
W["древний"] = (shadow(rx=28) + rect(10, 70, 80, 8, SAND)
                + "".join(rect(16 + i * 20, 34, 12, 36, STONE) for i in range(3))
                + rect(12, 26, 76, 8, STONE)
                + P("M42 24 l-6 -10 h12 Z", TAUPE))
W["особенный"] = (shadow(rx=24) + P("M50 16 l9 20 l22 3 l-16 15 l4 22 l-19 -11 "
                                    "l-19 11 l4 -22 l-16 -15 l22 -3 Z", OCHRE)
                  + circ(50, 46, 8, CREAM))
W["интересный"] = (shadow(rx=24) + circ(44, 44, 24, "none").replace('fill="none"',
                       f'fill="none" stroke="{BLUE2}" stroke-width="7"')
                   + P("M62 62 l18 18", "none").replace('fill="none"',
                       f'fill="none" stroke="{BLUE2}" stroke-width="9" '
                       'stroke-linecap="round"')
                   + P("M36 38 q0 -8 8 -8 q8 0 8 8 q0 7 -8 8 v4", "none").replace(
                       'fill="none"', f'fill="none" stroke="{BLUE}" stroke-width="4" '
                       'stroke-linecap="round"')
                   + circ(44, 56, 3, BLUE))

# ------------------------------------------------------------- наречия
W["много"] = (shadow(rx=30) + "".join(circ(22 + (i % 5) * 14, 40 + (i // 5) * 16, 7,
                                          [TERRA, OCHRE, OLIVE, SAND2, STONE][i % 5])
                                      for i in range(15)))
W["тихо"] = (shadow(rx=24) + circ(50, 42, 24, SKIN)
             + P("M26 40 a24 24 0 0 1 48 0 a24 12 0 0 0 -48 0 Z", HAIR_D)
             + circ(41, 42, 3, DARK) + circ(59, 42, 3, DARK)
             # Палец поперёк губ: сам жест и есть слово.
             + P("M50 76 V52", "none").replace('fill="none"',
                 f'fill="none" stroke="{SKIN}" stroke-width="10" stroke-linecap="round"')
             + P("M50 76 q-14 2 -16 -8", "none").replace('fill="none"',
                 f'fill="none" stroke="{SKIN}" stroke-width="12" stroke-linecap="round"')
             + P("M18 24 l8 6 M82 24 l-8 6", "none").replace('fill="none"',
                 f'fill="none" stroke="{STONE}" stroke-width="3" stroke-linecap="round"'))
W["быстро"] = (shadow(rx=28) + P("M28 66 V54 l10 -2 l8 -10 h24 l8 10 l10 2 v12 Z", TERRA)
               + circ(42, 68, 7, DARK) + circ(74, 68, 7, DARK)
               + "".join(rect(2, 40 + i * 9, 22 - i * 4, 5, TAUPE, 2.5) for i in range(3)))
W["медленно"] = (shadow(rx=26) + P("M22 68 q0 -16 18 -16 h20 q18 0 18 16 Z", OLIVE)
                 + P("M60 52 q6 -14 18 -10 q8 4 4 12", "none").replace('fill="none"',
                     f'fill="none" stroke="{OLIVE2}" stroke-width="7" '
                     'stroke-linecap="round"')
                 + circ(80, 50, 5, OLIVE2)
                 + P("M22 68 q-8 4 -12 -2", "none").replace('fill="none"',
                     f'fill="none" stroke="{OLIVE}" stroke-width="6" '
                     'stroke-linecap="round"'))
W["тяжело"] = (shadow(rx=28) + rect(24, 44, 52, 20, DARK, 4)
               + rect(14, 38, 12, 32, DARK, 3) + rect(74, 38, 12, 32, DARK, 3)
               + rect(6, 44, 10, 20, BROWN, 3) + rect(84, 44, 10, 20, BROWN, 3)
               + P("M34 30 l-6 -8 M66 30 l6 -8", "none").replace('fill="none"',
                   f'fill="none" stroke="{TERRA}" stroke-width="4" '
                   'stroke-linecap="round"'))

# --------------------------------------------------- местоимения (я, ты)
def _me(cx, base, h, c, hair=HAIR_D, skirt=False, back=False):
    return figure(cx, base, h, c, hair, skirt=skirt, long_hair=skirt, back=back)

W["я"] = (shadow(rx=22) + _me(50, 82, 60, TERRA)
          # Ладонь на груди — жест «я». Одна фигура без него читается
          # просто как «человек».
          + P("M62 52 q-12 6 -22 0", "none").replace('fill="none"',
              f'fill="none" stroke="{SKIN}" stroke-width="8" stroke-linecap="round"')
          + circ(40, 52, 5.5, SKIN)
          + "".join(P(f"M{x} {y-5} Q{x} {y} {x+4} {y} Q{x} {y} {x} {y+5} "
                      f"Q{x} {y} {x-4} {y} Q{x} {y} {x} {y-5} Z", OCHRE)
                    for x, y in ((20, 24), (80, 30))))
W["ты (муж.)"] = (shadow(rx=26) + _me(66, 80, 54, BLUE2)
                  + P("M22 44 h22", "none").replace('fill="none"',
                      f'fill="none" stroke="{SKIN}" stroke-width="8" '
                      'stroke-linecap="round"')
                  + P("M44 44 l-8 -6 M44 44 l-8 6", "none").replace('fill="none"',
                      f'fill="none" stroke="{TAUPE}" stroke-width="4" '
                      'stroke-linecap="round"'))
W["ты (жен.)"] = (shadow(rx=26) + _me(66, 80, 52, TERRA, skirt=True)
                  + P("M22 44 h22", "none").replace('fill="none"',
                      f'fill="none" stroke="{SKIN}" stroke-width="8" '
                      'stroke-linecap="round"')
                  + P("M44 44 l-8 -6 M44 44 l-8 6", "none").replace('fill="none"',
                      f'fill="none" stroke="{TAUPE}" stroke-width="4" '
                      'stroke-linecap="round"'))
W["он"] = (shadow(rx=24) + _me(70, 80, 52, BLUE2)
           + P("M14 50 h30 M36 42 l10 8 l-10 8", "none").replace('fill="none"',
               f'fill="none" stroke="{TAUPE}" stroke-width="4.5" '
               'stroke-linecap="round" stroke-linejoin="round"'))
W["она"] = (shadow(rx=24) + _me(70, 80, 50, TERRA, skirt=True)
            + P("M14 50 h30 M36 42 l10 8 l-10 8", "none").replace('fill="none"',
                f'fill="none" stroke="{TAUPE}" stroke-width="4.5" '
                'stroke-linecap="round" stroke-linejoin="round"'))
W["мы"] = (shadow(rx=30) + _me(28, 80, 50, TERRA, skirt=True)
           + _me(52, 80, 54, BLUE2) + _me(76, 80, 48, OLIVE)
           + P("M40 34 q10 -8 20 0", "none").replace('fill="none"',
               f'fill="none" stroke="{OCHRE}" stroke-width="4" stroke-linecap="round"'))
W["вы (муж.)"] = (shadow(rx=30) + _me(62, 80, 52, BLUE2) + _me(84, 80, 48, OLIVE)
                  + P("M12 46 h24 M28 38 l10 8 l-10 8", "none").replace('fill="none"',
                      f'fill="none" stroke="{TAUPE}" stroke-width="4.5" '
                      'stroke-linecap="round" stroke-linejoin="round"'))
W["вы (жен.)"] = (shadow(rx=30) + _me(62, 80, 50, TERRA, skirt=True)
                  + _me(84, 80, 46, OCHRE, HAIR_L, skirt=True)
                  + P("M12 46 h24 M28 38 l10 8 l-10 8", "none").replace('fill="none"',
                      f'fill="none" stroke="{TAUPE}" stroke-width="4.5" '
                      'stroke-linecap="round" stroke-linejoin="round"'))
W["они (муж.)"] = (shadow(rx=30) + _me(58, 80, 46, BLUE2, back=True)
                   + _me(80, 80, 42, OLIVE, back=True)
                   + P("M10 52 h26 M28 44 l10 8 l-10 8", "none").replace('fill="none"',
                       f'fill="none" stroke="{TAUPE}" stroke-width="4" '
                       'stroke-linecap="round" stroke-linejoin="round"'))
W["они (жен.)"] = (shadow(rx=30) + _me(58, 80, 44, TERRA, skirt=True, back=True)
                   + _me(80, 80, 40, OCHRE, HAIR_L, skirt=True, back=True)
                   + P("M10 52 h26 M28 44 l10 8 l-10 8", "none").replace('fill="none"',
                       f'fill="none" stroke="{TAUPE}" stroke-width="4" '
                       'stroke-linecap="round" stroke-linejoin="round"'))

# ------------------------------------------ местоимения (меня, его) — «эт»
def _at_arrow(x1, x2, y=32, c=TERRA):
    """Стрелка «на кого направлено действие» — то самое эт."""
    d = 1 if x2 > x1 else -1
    return (P(f"M{x1} {y} H{x2 - 8 * d}", "none").replace('fill="none"',
                f'fill="none" stroke="{c}" stroke-width="4.5" stroke-linecap="round"')
            + P(f"M{x2 - 8 * d} {y - 6} L{x2} {y} L{x2 - 8 * d} {y + 6} Z", c))

W["меня (эт)"] = (shadow(rx=28) + _me(70, 80, 50, BLUE2) + _me(26, 80, 54, TERRA)
                  + _at_arrow(58, 34))
W["его (эт)"] = (shadow(rx=28) + _me(26, 80, 54, TERRA) + _me(74, 80, 50, BLUE2)
                 + _at_arrow(40, 64))
W["её (эт)"] = (shadow(rx=28) + _me(26, 80, 54, BLUE2)
                + _me(74, 80, 48, OCHRE, HAIR_L, skirt=True)
                + _at_arrow(40, 64))
W["нас (эт)"] = (shadow(rx=30) + _me(78, 80, 50, BLUE2)
                 + _me(20, 80, 50, TERRA, skirt=True) + _me(42, 80, 46, OLIVE)
                 + _at_arrow(66, 52))
W["вас (эт)"] = (shadow(rx=30) + _me(20, 80, 52, TERRA)
                 + _me(60, 80, 48, BLUE2) + _me(82, 80, 44, OLIVE)
                 + _at_arrow(34, 48))
W["их (эт)"] = (shadow(rx=30) + _me(18, 80, 52, TERRA)
                + _me(62, 80, 46, OCHRE, HAIR_L) + _me(84, 80, 44, OLIVE)
                + _at_arrow(32, 50))

# --------------------------------------------------------- числительные
for _n, _w in ((1, "один"), (2, "два"), (3, "три"), (4, "четыре"), (5, "пять")):
    W[_w] = shadow(rx=26) + _dots(_n, y0=50)
W["десять"] = shadow(rx=30) + _dots(10, r=7, y0=38, dx=17, dy=22)
W["двадцать"] = (shadow(rx=30) + "".join(circ(18 + (i % 5) * 16, 34 + (i // 5) * 15, 6,
                                              TERRA if i < 10 else OCHRE)
                                         for i in range(20)))
W["сто"] = (shadow(rx=30) + "".join(rect(16 + (i % 10) * 7, 32 + (i // 10) * 7, 5, 5,
                                         TERRA if i % 2 else OCHRE, 1)
                                    for i in range(100)))
W["тысяча"] = (shadow(rx=30) + rect(14, 30, 72, 46, TERRA, 4)
               + "".join(rect(18 + (i % 12) * 6, 34 + (i // 12) * 6, 4, 4, OCHRE, 1)
                         for i in range(84))
               + rect(14, 30, 72, 46, "none").replace('fill="none"',
                   f'fill="none" stroke="{BROWN}" stroke-width="3"'))

# ------------------------------------------------------------ порядковые
def _podium(place):
    """Пьедестал: у «первого» подсвечена верхняя ступень и так далее."""
    hs = [(30, 46, 22, 32), (12, 56, 18, 22), (56, 62, 18, 16),
          (74, 68, 18, 10), (0, 0, 0, 0)]
    out = ""
    for i, (x, y, w, h) in enumerate(hs[:4]):
        out += rect(x, y, w, h, TERRA if i + 1 == place else SAND2, 2)
    return out

W["первый"] = shadow(rx=30) + _podium(1) + circ(41, 34, 9, OCHRE)
W["второй"] = shadow(rx=30) + _podium(2) + circ(21, 44, 8, OCHRE)
W["третий"] = shadow(rx=30) + _podium(3) + circ(65, 50, 8, OCHRE)
W["пятый"] = (shadow(rx=30) + "".join(rect(10 + i * 17, 74 - (i + 2) * 4, 13,
                                           (i + 2) * 4, TERRA if i == 4 else SAND2, 2)
                                      for i in range(5)))
W["десятый"] = (shadow(rx=30) + "".join(rect(6 + i * 9, 74 - (i + 2) * 3, 7,
                                             (i + 2) * 3, TERRA if i == 9 else SAND2, 1.5)
                                        for i in range(10)))

# ------------------------------------------------------- предлоги места
W["на (сверху)"] = shadow(rx=30) + _table() + _ball(50, 44)
W["под"] = shadow(rx=30) + _table() + _ball(50, 68)
W["над"] = (shadow(rx=30) + _table() + _ball(50, 26)
            + P("M50 38 v8", "none").replace('fill="none"',
                f'fill="none" stroke="{TAUPE}" stroke-width="3" stroke-dasharray="3 4"'))
W["рядом"] = (shadow(rx=30) + rect(24, 40, 26, 26, SAND2, 3) + _ball(66, 56))
W["между"] = (shadow(rx=30) + rect(12, 38, 22, 30, SAND2, 3)
              + rect(66, 38, 22, 30, SAND2, 3) + _ball(50, 54))
W["внутри"] = (shadow(rx=30) + rect(24, 34, 52, 40, "none").replace('fill="none"',
                   f'fill="none" stroke="{SAND2}" stroke-width="7"')
               + _ball(50, 54))
W["снаружи"] = (shadow(rx=30) + rect(14, 34, 44, 40, "none").replace('fill="none"',
                    f'fill="none" stroke="{SAND2}" stroke-width="7"')
                + _ball(78, 54))
W["перед (до)"] = (shadow(rx=30) + rect(48, 36, 30, 34, SAND2, 3) + _ball(26, 58)
                   + P("M26 44 v-8 M20 40 l6 -6 l6 6", "none").replace('fill="none"',
                       f'fill="none" stroke="{TAUPE}" stroke-width="0"'))
W["после"] = (shadow(rx=30) + rect(22, 36, 30, 34, SAND2, 3) + _ball(74, 58))
W["здесь"] = (shadow(rx=24) + P("M50 82 C34 62 26 52 26 40 a24 24 0 0 1 48 0 "
                                "c0 12 -8 22 -24 42 Z", TERRA)
              + circ(50, 40, 10, CREAM))
W["там"] = (shadow(rx=28) + P("M74 76 C64 60 58 52 58 44 a16 16 0 0 1 32 0 "
                              "c0 8 -6 16 -16 32 Z", TAUPE)
            + circ(74, 44, 6, CREAM)
            + P("M12 60 h28 M32 52 l10 8 l-10 8", "none").replace('fill="none"',
                f'fill="none" stroke="{TERRA}" stroke-width="4.5" '
                'stroke-linecap="round" stroke-linejoin="round"'))

# ------------------------------------------------- вопросительные слова
# Честного изображения у вопроса нет: «что» и «кто» — не предметы.
# Поэтому здесь принят один общий знак — вопросительный, — а различает
# слова то, к чему он относится: к вещи, к человеку, к месту, ко времени.
def _q(cx=50, cy=34, r=15, c=BLUE2):
    return (circ(cx, cy, r, c)
            + P(f"M{cx-6} {cy-4} q0 -7 6 -7 q6 0 6 7 q0 5 -6 6 v3", "none").replace(
                'fill="none"', f'fill="none" stroke="{WHITE}" stroke-width="3.5" '
                'stroke-linecap="round"')
            + circ(cx, cy + 9, 2.4, WHITE))

W["что"] = shadow(rx=26) + _box(28, 52, 44, 26, SAND2) + _q(50, 26)
W["кто"] = shadow(rx=26) + figure(50, 82, 42, TERRA, HAIR_D) + _q(78, 26, 13)
W["где"] = (shadow(rx=26) + P("M50 82 C36 64 30 56 30 46 a20 20 0 0 1 40 0 "
                              "c0 10 -6 18 -20 36 Z", TAUPE) + _q(76, 24, 13))
W["куда"] = (shadow(rx=26) + P("M18 62 h40 M48 50 l14 12 l-14 12", "none").replace(
                 'fill="none"', f'fill="none" stroke="{TAUPE}" stroke-width="7" '
                 'stroke-linecap="round" stroke-linejoin="round"') + _q(72, 26, 14))
W["откуда"] = (shadow(rx=26) + P("M82 62 H42 M52 50 l-14 12 l14 12", "none").replace(
                   'fill="none"', f'fill="none" stroke="{TAUPE}" stroke-width="7" '
                   'stroke-linecap="round" stroke-linejoin="round"') + _q(28, 26, 14))
W["какой"] = (shadow(rx=28) + rect(16, 50, 24, 26, TERRA, 3)
              + rect(60, 50, 24, 26, OLIVE, 3) + _q(50, 26, 14))
W["какая"] = (shadow(rx=28) + circ(28, 62, 14, TERRA) + circ(72, 62, 14, OCHRE)
              + _q(50, 26, 14))
W["какие"] = (shadow(rx=28) + circ(22, 66, 10, TERRA) + rect(40, 56, 20, 20, OLIVE, 3)
              + circ(78, 66, 10, OCHRE) + _q(50, 24, 13))
W["когда"] = (shadow(rx=26) + circ(38, 56, 22, CREAM)
              + circ(38, 56, 22, "none").replace('fill="none"',
                  f'fill="none" stroke="{TAUPE}" stroke-width="3.5"')
              + P("M38 56 V42 M38 56 l10 6", "none").replace('fill="none"',
                  f'fill="none" stroke="{DARK}" stroke-width="3.5" '
                  'stroke-linecap="round"') + _q(76, 26, 13))
W["почему"] = (shadow(rx=26) + _q(50, 46, 26)
               + P("M14 20 l8 8 M86 20 l-8 8", "none").replace('fill="none"',
                   f'fill="none" stroke="{OCHRE}" stroke-width="4" '
                   'stroke-linecap="round"'))

# ------------------------------------------------------------- частицы
# Служебные слова тоже не предметы. Здесь знак прямо называет действие:
# есть — полная полка, нет — пустая, каждый — все отмечены, но — развилка.
W["есть / имеется"] = (shadow(rx=28) + rect(14, 58, 72, 6, BROWN, 2)
                       + rect(22, 40, 16, 18, TERRA, 2) + rect(42, 34, 16, 24, OCHRE, 2)
                       + rect(62, 44, 16, 14, OLIVE, 2)
                       + circ(80, 26, 11, OLIVE)
                       + P("M75 26 l4 5 l7 -9", "none").replace('fill="none"',
                           f'fill="none" stroke="{WHITE}" stroke-width="3.5" '
                           'stroke-linecap="round" stroke-linejoin="round"'))
W["нет / не имеется"] = (shadow(rx=28) + rect(14, 58, 72, 6, BROWN, 2)
                         + rect(14, 30, 72, 28, "none").replace('fill="none"',
                             f'fill="none" stroke="{STONE}" stroke-width="3" '
                             'stroke-dasharray="6 5"')
                         + circ(80, 26, 11, RED)
                         + P("M76 22 l8 8 M84 22 l-8 8", "none").replace('fill="none"',
                             f'fill="none" stroke="{WHITE}" stroke-width="3.5" '
                             'stroke-linecap="round"'))
W["весь / каждый"] = (shadow(rx=30) + "".join(
    circ(24 + (i % 3) * 26, 36 + (i // 3) * 26, 11, OLIVE) for i in range(9))
    + "".join(P(f"M{20 + (i % 3) * 26} {36 + (i // 3) * 26} l3 4 l6 -7", "none").replace(
        'fill="none"', f'fill="none" stroke="{WHITE}" stroke-width="2.6" '
        'stroke-linecap="round" stroke-linejoin="round"') for i in range(9)))
W["но"] = (shadow(rx=28) + P("M50 80 V52", "none").replace('fill="none"',
               f'fill="none" stroke="{TAUPE}" stroke-width="7" stroke-linecap="round"')
           + P("M50 52 L24 28 M50 52 L76 28", "none").replace('fill="none"',
               f'fill="none" stroke="{TAUPE}" stroke-width="7" stroke-linecap="round"')
           + circ(24, 24, 9, OLIVE) + circ(76, 24, 9, TERRA))
W["что-нибудь"] = (shadow(rx=28) + rect(28, 40, 44, 38, SAND2, 4)
                   + rect(28, 40, 44, 10, TAUPE, 4)
                   + P("M42 62 q0 -8 8 -8 q8 0 8 8 q0 6 -8 7 v3", "none").replace(
                       'fill="none"', f'fill="none" stroke="{BROWN}" stroke-width="4" '
                       'stroke-linecap="round"')
                   + circ(50, 74, 3, BROWN))
W["кто-нибудь"] = (shadow(rx=26) + figure(50, 82, 46, STONE, HAIR_G)
                   + circ(50, 82 - 46 + 9.2, 9.6, STONE)
                   + P("M44 34 q0 -8 6 -8 q6 0 6 8 q0 6 -6 7 v3", "none").replace(
                       'fill="none"', f'fill="none" stroke="{GAP}" stroke-width="3.5" '
                       'stroke-linecap="round"')
                   + circ(50, 50, 2.6, GAP))
