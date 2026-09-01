# -*- coding: utf-8 -*-
"""Сцены для девяти разделов грамматики.

Формат тот же, что у тем: 150×104, потому что плитка грамматики стоит в
той же сетке и рисуется той же функцией. Раньше у них не было ничего, и
верх плитки просто пустовал.

Грамматика абстрактна, поэтому каждая сцена показывает не понятие, а
вопрос, на который часть речи отвечает: какой — сосуды разного размера,
сколько — камни по росту, который — ступени, где — кувшин на столе, под
ним и рядом.
"""
from art_kit import (P, rect, circ, dome, cypress, windows, crenel, arch_win,
                 gabled, tower, stones, SAND, SAND2, OCHRE, TAUPE, STONE,
                 BROWN, DARK, OLIVE, OLIVE2, CREAM, TERRA, SKY, SKY2, W, H)

GROUND = '<use href="#ground"/>'
S = {}

def sky(band=True):
    out = rect(-2, -2, W + 4, H + 4, SKY)
    if band:
        out += rect(-2, 58, W + 4, 24, SKY2)
    return out

def jar(x, base, w, h, fill):
    return (P(f"M{x} {base} V{base-h} a{w/3} {w/3} 0 0 1 {w/3} {-w/3} "
              f"h{w/3} a{w/3} {w/3} 0 0 1 {w/3} {w/3} v{h} Z", fill)
            + rect(x + w/4, base - h - w/3 - 6, w/2, 6, fill, 2))

# какой? — сосуды разного роста
S["adjectives"] = (sky() + jar(22, 86, 30, 30, TERRA) + jar(60, 86, 24, 22, OCHRE)
                   + jar(96, 86, 34, 40, SAND2) + GROUND)

# как? — фигура в движении и следы скорости
S["adverbs"] = (sky()
    + "".join(rect(10 + i * 4, 40 + i * 12, 26 - i * 4, 5, TAUPE, 2.5)
              for i in range(3))
    + circ(78, 32, 10, SAND2)
    + P("M64 74 L76 42 L92 46 L86 74 Z", TERRA)
    + P("M64 74 L54 86 L64 86 L72 76 Z", TERRA)
    + P("M86 74 L96 86 L106 86 L94 72 Z", TERRA)
    + P("M76 50 L100 44 L104 52 L78 58 Z", OCHRE)
    + GROUND)

# я, ты — двое лицом друг к другу
S["personal_pronouns"] = (sky()
    + circ(46, 40, 11, SAND2) + P("M30 86 V60 a16 16 0 0 1 32 0 v26 Z", TERRA)
    + circ(104, 42, 10, SAND) + P("M90 86 V62 a14 14 0 0 1 28 0 v24 Z", OLIVE)
    + GROUND)

# меня, его — один впереди, другой позади
S["object_pronouns"] = (sky()
    + circ(96, 40, 9, SAND) + P("M84 86 V60 a12 12 0 0 1 24 0 v26 Z", TAUPE)
    + circ(52, 46, 12, SAND2) + P("M32 86 V66 a20 20 0 0 1 40 0 v20 Z", TERRA)
    + rect(70, 56, 26, 5, OCHRE, 2) + P("M96 58.5 L86 52 L86 65 Z", OCHRE)
    + GROUND)

# сколько? — камни по росту
S["cardinals"] = (sky()
    + "".join(rect(20 + i * 24, 86 - (16 + i * 14), 20, 16 + i * 14,
                   [STONE, SAND2, OCHRE, TERRA][i], 3) for i in range(4))
    + GROUND)

# который? — ступени пьедестала
S["ordinals"] = (sky()
    + rect(56, 34, 38, 52, OCHRE) + rect(18, 52, 38, 34, SAND2)
    + rect(94, 60, 38, 26, TAUPE)
    + circ(75, 24, 9, TERRA)
    + GROUND)

# вопросительные — указатель на много сторон
S["question_words"] = (sky()
    + rect(72, 24, 7, 62, BROWN)
    + P("M20 34 L74 34 L74 44 L20 44 L12 39 Z", TERRA)
    + P("M130 50 L76 50 L76 60 L130 60 L138 55 Z", OCHRE)
    + P("M26 66 L74 66 L74 76 L26 76 L18 71 Z", SAND2)
    + GROUND)

# частицы — россыпь мелких камешков
S["particles"] = (sky()
    + "".join(circ(x, y, r, c) for x, y, r, c in
              ((32, 70, 7, TERRA), (52, 76, 5, OCHRE), (70, 66, 8, SAND2),
               (90, 74, 5, TAUPE), (108, 68, 7, OLIVE), (124, 76, 4, STONE),
               (44, 58, 4, SAND), (100, 56, 5, TERRA)))
    + GROUND)

# где? — на столе, под столом, рядом
S["place_prepositions"] = (sky()
    + rect(14, 54, 108, 7, BROWN)
    + rect(22, 61, 6, 25, BROWN) + rect(108, 61, 6, 25, BROWN)
    + jar(52, 54, 24, 20, OCHRE)
    + jar(34, 86, 20, 16, SAND2)
    + jar(124, 86, 22, 26, TERRA)
    + GROUND)


def build():
    return "\n".join(
        f'<g id="sk-{k}" stroke="#FAF5EA" stroke-width="1" '
        f'stroke-linejoin="round">{v}</g>' for k, v in S.items())


if __name__ == "__main__":
    from pathlib import Path
    Path("gram.svgfrag").write_text(build(), encoding="utf-8")
    print("сцен грамматики:", len(S))
