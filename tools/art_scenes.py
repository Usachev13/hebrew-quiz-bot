# -*- coding: utf-8 -*-
"""Тринадцать сцен одного придуманного города."""
from art_kit import *

S = {}

def sky(top=SKY, band=True):
    out = rect(-2, -2, W + 4, H + 4, top)
    if band:
        out += rect(-2, 58, W + 4, 24, SKY2)
    return out

# Кладка одна и та же в двенадцати сценах. Если её дублировать, страница
# толстеет на 46 КБ — поэтому она объявлена один раз, а сцены на неё
# ссылаются.
GROUND_DEF = f'<g id="ground">{stones(84, 22, seed=3)}</g>'
GROUND = '<use href="#ground"/>'

# ---------- Приветствия: хамса над воротами города ----------
S["greetings"] = scene(
    sky(),
    birds([(24, 16, 1), (36, 22, .8), (124, 18, .9)]),
    cypress(14, 90, 70, 11, OLIVE), cypress(137, 90, 62, 10, OLIVE2),
    rect(26, 62, 98, 24, SAND2), crenel(26, 62, 98, 8, 6, SAND2),
    windows(31, 70, 9, 1, 5, 7, 6, 0, DARK),
    # хамса: ладонь, три пальца и два больших по бокам
    rect(60, 44, 30, 34, OCHRE, 12),
    rect(63.5, 24, 6.5, 24, OCHRE, 3.2),
    rect(71.5, 18, 6.5, 30, OCHRE, 3.2),
    rect(79.5, 22, 6.5, 26, OCHRE, 3.2),
    '<g transform="rotate(-32 57 52)">' + rect(54, 38, 6.5, 22, OCHRE, 3.2) + '</g>',
    '<g transform="rotate(32 93 52)">' + rect(89.5, 38, 6.5, 22, OCHRE, 3.2) + '</g>',
    P("M75 52 q11 8 0 16 q-11-8 0-16 Z", CREAM), circ(75, 60, 3.6, DARK),
    rect(69, 82, 12, 4, TERRA, 2),
    GROUND)

# ---------- Семья: три фигуры у дома ----------
S["family"] = scene(
    sky(),
    birds([(30, 14, .9), (118, 20, .8)]),
    circ(126, 22, 11, OCHRE),
    cypress(12, 88, 62, 10, OLIVE2), cypress(140, 88, 54, 9, OLIVE),
    rect(40, 34, 70, 52, SAND), dome(75, 34, 35, SAND2),
    arch_win(75, 52, 16, 20, CREAM),
    windows(46, 54, 2, 1, 7, 8, 7, 0, DARK),
    windows(97, 54, 2, 1, 7, 8, 7, 0, DARK),
    rect(24, 60, 18, 26, TAUPE), rect(108, 64, 18, 22, STONE),
    GROUND,
    P("M28 104 V72 a13 13 0 0 1 26 0 v32 Z", TERRA), circ(41, 60, 10.5, SAND2),
    P("M92 104 V74 a12 12 0 0 1 24 0 v30 Z", OLIVE), circ(104, 64, 9.5, SAND),
    P("M64 104 V80 a9 9 0 0 1 18 0 v24 Z", OCHRE), circ(73, 72, 7.5, CREAM))

# ---------- Еда: стол с посудой ----------
S["food"] = scene(
    sky(),
    rect(-6, 20, W + 12, 5, BROWN),
    *[rect(12 + i * 24, 25, 15, 11, TERRA if i % 2 else CREAM, 1) for i in range(6)],
    rect(-6, 76, W + 12, 7, BROWN),
    # чаша супа стоит на столе, а не висит под ним
    P("M38 56 Q59 82 80 56 Z", TERRA), rect(35, 52, 48, 5, SAND2, 2.5),
    circ(50, 47, 3.2, OLIVE), circ(60, 45, 3.2, OCHRE), circ(69, 47, 3.2, OLIVE2),
    # кувшин
    P("M96 76 V52 a7 7 0 0 1 5-7 h6 a7 7 0 0 1 5 7 v24 Z", OCHRE),
    rect(98, 38, 14, 7, OCHRE, 3), P("M112 54 q10 5 0 12 Z", OCHRE),
    # хлеб и виноград
    P("M10 76 a15 10 0 0 1 30 0 Z", SAND2),
    rect(15, 68, 3.4, 3.4, DARK, 1.4), rect(24, 66, 3.4, 3.4, DARK, 1.4),
    rect(31, 69, 3.4, 3.4, DARK, 1.4),
    rect(118, 70, 28, 6, CREAM, 2),
    circ(124, 66, 4, OLIVE), circ(133, 65, 4, OLIVE2), circ(141, 67, 3.8, OLIVE),
    circ(128, 59, 4, TERRA), circ(137, 59, 3.8, TERRA),
    GROUND)

# ---------- Дом ----------
S["home"] = scene(
    sky(),
    birds([(34, 14, .9), (46, 20, .7)]),
    circ(124, 22, 13, OCHRE),
    rect(4, 52, 22, 34, STONE), dome(15, 52, 11, TAUPE),
    windows(9, 62, 2, 2, 5, 5, 5, 5, DARK),
    cypress(34, 88, 58, 10, OLIVE2),
    rect(46, 44, 56, 42, SAND), dome(74, 44, 28, SAND2),
    rect(102, 58, 26, 28, TAUPE), dome(115, 58, 13, CREAM),
    arch_win(74, 86, 18, 24, DARK),
    windows(52, 54, 2, 1, 7, 8, 7, 0, CREAM),
    windows(86, 54, 1, 1, 7, 8, 0, 0, CREAM),
    windows(106, 68, 2, 1, 6, 7, 7, 0, DARK),
    rect(130, 68, 18, 18, SAND2),
    GROUND)

# ---------- Город: сам образец ----------
S["city"] = scene(
    sky(),
    birds([(40, 12, 1), (54, 18, .8), (112, 14, .9)]),
    circ(124, 20, 10, OCHRE),
    cypress(10, 88, 70, 11, OLIVE), cypress(142, 88, 64, 10, OLIVE2),
    tower(28, 86, 17, 46, SAND2, "dome"),
    tower(98, 86, 14, 52, TAUPE, "cone"),
    rect(46, 52, 36, 34, SAND), dome(64, 52, 18, OCHRE),
    rect(82, 56, 18, 30, CREAM), gabled(112, 50, 22, 36, 13, SAND2),
    rect(22, 68, 108, 18, TAUPE), crenel(22, 68, 108, 10, 5, TAUPE),
    windows(28, 74, 9, 1, 5, 6, 6, 0, DARK),
    windows(52, 58, 2, 1, 5, 6, 8, 0, DARK),
    windows(86, 62, 2, 1, 4, 5, 6, 0, DARK),
    arch_win(64, 86, 13, 17, DARK),
    GROUND)

# ---------- Транспорт: автобус на дороге ----------
S["transport"] = scene(
    sky(),
    birds([(28, 12, .8), (118, 16, .9)]),
    rect(6, 22, 26, 24, TAUPE), rect(36, 16, 20, 30, SAND2),
    rect(60, 24, 30, 22, STONE), rect(94, 14, 22, 32, SAND),
    rect(120, 22, 26, 24, TAUPE),
    windows(10, 28, 3, 2, 5, 5, 4, 4, DARK),
    windows(40, 22, 2, 3, 5, 5, 5, 4, DARK),
    windows(64, 30, 4, 1, 5, 6, 4, 0, DARK),
    windows(98, 20, 2, 3, 5, 5, 5, 4, DARK),
    windows(124, 28, 3, 2, 5, 5, 4, 4, DARK),
    rect(-6, 46, W + 12, 6, SAND2),
    rect(22, 52, 106, 30, OCHRE, 6),
    windows(28, 58, 5, 1, 15, 13, 3, 0, CREAM),
    rect(108, 58, 16, 13, CREAM, 1),
    rect(24, 74, 102, 4, TERRA),
    circ(46, 82, 9, DARK), circ(46, 82, 3.8, STONE),
    circ(106, 82, 9, DARK), circ(106, 82, 3.8, STONE),
    rect(-6, 88, W + 12, 18, TAUPE),
    *[rect(2 + i * 22, 95, 13, 3, CREAM, 1.5) for i in range(7)])

# ---------- Время: башня с часами ----------
S["time"] = scene(
    rect(-2, -2, W + 4, H + 4, SKY),
    rect(-2, -2, 75, H + 4, SKY2),
    circ(28, 26, 11, OCHRE),
    P("M124 16 a12 12 0 1 0 9 20 a14 14 0 0 1-9-20 Z", CREAM),
    circ(104, 14, 1.8, CREAM), circ(112, 30, 1.4, CREAM), circ(96, 30, 1.2, CREAM),
    cypress(14, 88, 50, 9, OLIVE2), cypress(138, 88, 46, 9, OLIVE),
    rect(60, 32, 30, 54, SAND2), P("M58 32 L75 16 L92 32 Z", TERRA),
    circ(75, 48, 12, CREAM), circ(75, 48, 9.5, SAND),
    P("M75 48 V41 M75 48 l6 4", "none").replace('fill="none"',
        'fill="none" stroke="#6B4F3A" stroke-width="1.8" stroke-linecap="round"'),
    rect(36, 62, 24, 24, TAUPE), rect(90, 66, 24, 20, SAND),
    windows(40, 68, 2, 1, 6, 7, 6, 0, DARK), windows(95, 72, 2, 1, 6, 6, 6, 0, DARK),
    GROUND)

# ---------- Погода: солнце, облака, дождь ----------
S["weather"] = scene(
    sky(band=False),
    circ(30, 26, 17, OCHRE),
    *[rect(x, y, 3, 8, OCHRE, 1.5) for x, y in
      ((28.5, 2), (28.5, 46), (8, 24), (49, 24))],
    P("M74 42 a14 14 0 0 1 3-27 a19 19 0 0 1 36-3 a12 12 0 0 1 2 30 Z", CREAM),
    P("M20 62 a11 11 0 0 1 2-21 a15 15 0 0 1 28-2 a10 10 0 0 1 2 23 Z", STONE),
    *[rect(x, y, 2.6, 10, STONE, 1.3) for x, y in
      ((26, 66), (38, 70), (50, 66), (86, 48), (98, 52), (110, 48), (122, 52),
       (62, 70), (74, 66))],
    rect(6, 80, 40, 8, SAND2), rect(50, 74, 34, 14, TAUPE),
    rect(88, 78, 30, 10, SAND), rect(122, 72, 24, 16, STONE),
    windows(94, 82, 2, 1, 5, 4, 6, 0, DARK),
    windows(128, 78, 2, 1, 5, 5, 6, 0, DARK),
    GROUND)

# ---------- Здоровье: сердце и травы ----------
S["health"] = scene(
    sky(),
    birds([(26, 16, .8), (122, 14, .9)]),
    rect(-6, 66, W + 12, 22, SKY2),
    P("M75 84 C46 62 35 51 35 38 a17 17 0 0 1 40-8 a17 17 0 0 1 40 8 "
      "c0 13-11 24-40 46 Z", TERRA),
    rect(74, 34, 2.4, 36, CREAM, 1.2),
    P("M75 54 q-14 0-14-12 q14 0 14 12 Z", CREAM),
    P("M75 44 q14 0 14-12 q-14 0-14 12 Z", CREAM),
    # травы по бокам
    rect(20, 62, 12, 24, OCHRE, 2), P("M26 62 q-9-5-7-15 q9 4 7 15 Z", OLIVE),
    P("M26 60 q9-6 8-16 q-10 5-8 16 Z", OLIVE2),
    rect(118, 62, 12, 24, SAND2, 2), P("M124 62 q-9-5-7-15 q9 4 7 15 Z", OLIVE2),
    P("M124 60 q9-6 8-16 q-10 5-8 16 Z", OLIVE),
    circ(10, 40, 5, OCHRE), circ(142, 44, 5, OCHRE),
    GROUND)

# ---------- Покупки: рынок под навесом ----------
S["shopping"] = scene(
    sky(),
    rect(16, 30, 118, 6, BROWN),
    *[rect(16 + i * 14.75, 36, 14.75, 12, TERRA if i % 2 == 0 else CREAM)
      for i in range(8)],
    rect(20, 56, 30, 30, SAND2), rect(56, 60, 34, 26, TAUPE),
    rect(96, 54, 32, 32, SAND),
    windows(24, 62, 3, 2, 6, 6, 3, 4, OCHRE),
    circ(62, 66, 5, TERRA), circ(74, 66, 5, OLIVE), circ(84, 68, 4.4, OCHRE),
    circ(66, 76, 5, OCHRE), circ(78, 77, 4.6, TERRA),
    rect(100, 60, 24, 5, CREAM), rect(100, 69, 24, 5, CREAM),
    rect(100, 78, 24, 5, CREAM),
    GROUND)

# ---------- Работа и учёба: стол с книгами ----------
S["work_study"] = scene(
    sky(),
    rect(-6, 20, W + 12, 4, BROWN),
    *[rect(14 + i * 13, 8, 9, 12, [TERRA, OCHRE, OLIVE, SAND2, CREAM][i % 5], 1)
      for i in range(9)],
    rect(-6, 76, W + 12, 7, BROWN),
    P("M38 76 q19-9 37 0 V44 q-18-9-37 0 Z", CREAM),
    P("M75 76 q19-9 37 0 V44 q-18-9-37 0 Z", SAND),
    rect(74, 44, 2.4, 32, BROWN),
    *[rect(45, 51 + i * 6, 24, 2.6, TAUPE, 1.3) for i in range(4)],
    *[rect(81, 51 + i * 6, 24, 2.6, TAUPE, 1.3) for i in range(4)],
    rect(8, 62, 24, 14, TERRA, 1), rect(10, 50, 20, 11, OCHRE, 1),
    rect(12, 40, 16, 9, OLIVE, 1),
    rect(120, 58, 12, 18, SAND2, 2),
    P("M126 58 q-11-5-9-17 q11 5 9 17 Z", OLIVE),
    P("M126 56 q11-7 10-18 q-12 6-10 18 Z", OLIVE2),
    rect(-6, 83, W + 12, 21, SKY2),
    GROUND)

# ---------- Одежда: бельевая верёвка над стеной ----------
S["clothes"] = scene(
    sky(),
    birds([(120, 14, .8)]),
    rect(8, 20, 4, 66, BROWN), rect(138, 20, 4, 66, BROWN),
    rect(8, 20, 134, 2, DARK),
    # платье
    P("M28 26 h6 l-3 5 h-2 Z", DARK),
    P("M31 30 l-9 6 4 5 4-2 -3 27 h16 l-3-27 4 2 4-5-9-6 Z", TERRA),
    # рубашка
    P("M72 26 h6 l-3 5 h-2 Z", DARK),
    P("M75 30 l-11 5 3 7 4-2 v22 h20 V40 l4 2 3-7-11-5 Z", CREAM),
    windows(70, 44, 1, 3, 3, 3, 0, 4, TAUPE),
    # штаны
    P("M114 26 h6 l-3 5 h-2 Z", DARK),
    P("M104 32 h26 l-3 30 h-8 l-2-18 -2 18 h-8 Z", OCHRE),
    rect(20, 70, 36, 16, SAND2), rect(60, 66, 32, 20, TAUPE),
    rect(96, 70, 36, 16, SAND),
    windows(25, 74, 2, 1, 7, 8, 8, 0, DARK),
    windows(66, 72, 2, 1, 6, 7, 8, 0, DARK),
    windows(102, 74, 2, 1, 7, 8, 8, 0, DARK),
    GROUND)

# ---------- Эмоции: три лица ----------
S["emotions"] = scene(
    sky(band=False),
    rect(-2, 70, W + 4, 34, SKY2),
    circ(36, 44, 21, OCHRE),
    circ(30, 40, 2.4, DARK), circ(43, 40, 2.4, DARK),
    P("M28 50 q8 8 16 0 Z", DARK),
    circ(75, 40, 17, TERRA),
    circ(70, 37, 2.1, CREAM), circ(81, 37, 2.1, CREAM),
    rect(68, 46, 15, 2.6, CREAM, 1.3),
    circ(114, 46, 19, OLIVE),
    circ(108, 42, 2.2, CREAM), circ(120, 42, 2.2, CREAM),
    P("M106 55 q8-7 16 0", "none").replace('fill="none"',
        'fill="none" stroke="#E9E0CC" stroke-width="2.6" stroke-linecap="round"'),
    cypress(12, 86, 40, 7, OLIVE2), cypress(140, 86, 38, 7, OLIVE),
    GROUND)


def build():
    return GROUND_DEF + "\n" + "\n".join(wrap(k, v) for k, v in S.items())


if __name__ == "__main__":
    from pathlib import Path
    Path("scenes.svgfrag").write_text(build(), encoding="utf-8")
    print("сцен:", len(S))
