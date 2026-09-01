# -*- coding: utf-8 -*-
"""Фоны для кнопок внутри разделов: алфавит и времена глагола.

Времена сделаны нарочно одним пейзажем в разное время суток: закат —
прошедшее, зенит — настоящее, рассвет — будущее. Так они читаются как
шкала, а не как три случайные картинки, и разница видна боковым зрением.
"""
from art_kit import (P, rect, circ, dome, cypress, windows, crenel, arch_win,
                 gabled, tower, SAND, SAND2, OCHRE, TAUPE, STONE, BROWN,
                 DARK, OLIVE, OLIVE2, CREAM, TERRA)

TW, TH = 340, 88
# Вуаль глуха до 60 % ширины, то есть до x = 204. Всё, что левее, не
# видно вовсе — первый заход это и показал: у времён солнце пряталось
# целиком. Рисуем в полосе 214…338, фон-заливки можно вести шире.
X0, X1 = 214, 338
T = {}

# ---------- алфавит ----------

# названия букв — скрижали с подписями
T["alef_names"] = (
    rect(222, 24, 40, 60, SAND2) + dome(242, 24, 20, SAND2)
    + rect(270, 28, 40, 56, SAND) + dome(290, 28, 20, SAND)
    + "".join(rect(230, 36 + i * 11, 24, 4, TAUPE, 2) for i in range(4))
    + "".join(rect(278, 40 + i * 11, 24, 4, TAUPE, 2) for i in range(4))
    + circ(326, 30, 12, OCHRE))

# звуки букв — рог и волны звука
T["alef_sounds"] = (
    rect(150, 70, 190, 18, SAND2)
    + P("M226 56 L236 52 L280 34 L286 66 L236 62 Z", OCHRE)
    + rect(220, 52, 8, 12, BROWN, 2)
    + "".join(P(f"M{298 + i*13} {34 - i*5} q9 15 0 30", "none").replace(
        'fill="none"', f'fill="none" stroke="{TAUPE}" stroke-width="3" '
        f'stroke-linecap="round" opacity="{0.85 - i*0.22}"') for i in range(3))
    + cypress(212, 70, 32, 6, OLIVE2))

# узнать букву по названию — указатель у дороги
T["alef_by_name"] = (
    rect(150, 64, 190, 24, SAND2)
    + rect(274, 26, 6, 38, BROWN)
    + P("M238 30 L276 30 L276 42 L238 42 L230 36 Z", TERRA)
    + P("M316 46 L278 46 L278 58 L316 58 L324 52 Z", OCHRE)
    + cypress(230, 64, 34, 6, OLIVE) + cypress(334, 64, 30, 6, OLIVE2)
    + circ(302, 22, 10, SAND))

# конечные формы — четыре камня и пятый, иной
T["alef_finals"] = (
    rect(150, 70, 190, 18, SAND2)
    + "".join(rect(216 + i * 26, 46, 20, 24, STONE, 3) for i in range(4))
    + rect(310, 36, 22, 34, TERRA, 3)
    + cypress(210, 70, 34, 6, OLIVE2))

# точка меняет звук — два одинаковых кувшина, у одного точка
T["alef_dotted"] = (
    rect(150, 70, 190, 18, SAND2)
    + P("M240 70 V46 a8 8 0 0 1 6-8 h6 a8 8 0 0 1 6 8 v24 Z", SAND)
    + rect(242, 30, 16, 8, SAND, 3)
    + P("M296 70 V46 a8 8 0 0 1 6-8 h6 a8 8 0 0 1 6 8 v24 Z", OCHRE)
    + rect(298, 30, 16, 8, OCHRE, 3)
    + circ(308, 56, 5, DARK)
    + cypress(220, 70, 32, 6, OLIVE2))

# огласовки — точки под перекладиной
T["alef_niqqud"] = (
    rect(150, 74, 190, 14, SAND2)
    + rect(220, 36, 112, 8, TAUPE, 3)
    + "".join(circ(234 + i * 22, 58, 5, OCHRE if i % 2 else TERRA) for i in range(5))
    + circ(328, 24, 8, SAND))

# чтение слогов — два камня сходятся в один
T["alef_syllables"] = (
    rect(150, 70, 190, 18, SAND2)
    + rect(216, 44, 26, 26, SAND, 4) + rect(248, 44, 26, 26, OCHRE, 4)
    + P("M280 57 L292 48 L292 66 Z", TAUPE)
    + rect(298, 40, 36, 30, TERRA, 4))

# ---------- времена глагола ----------

def _land(sun_x, sun_y, sun_c, sky_hi, sky_lo, hill, hill2):
    """Один и тот же вид: холмы, кипарисы, дом. Меняются только солнце
    и температура неба — тогда три времени читаются шкалой."""
    return (rect(150, 0, 190, TH, sky_hi)
            + rect(150, 42, 190, TH - 42, sky_lo)
            + circ(sun_x, sun_y, 15, sun_c)
            + P("M150 62 Q216 46 268 60 Q308 70 340 62 V88 H150 Z", hill)
            + P("M150 76 Q212 64 260 76 Q300 84 340 76 V88 H150 Z", hill2)
            + rect(300, 50, 26, 22, SAND2) + dome(313, 50, 13, SAND2)
            + cypress(226, 76, 40, 7, OLIVE2)
            + cypress(244, 78, 30, 6, OLIVE))


T["inf"] = (                       # инфинитивы — ворота, начало пути
    rect(150, 66, 190, 22, TAUPE)
    + rect(226, 22, 88, 44, SAND2) + crenel(226, 22, 88, 7, 7, SAND2)
    + arch_win(270, 66, 28, 40, DARK)
    + windows(234, 34, 2, 1, 6, 8, 8, 0, DARK)
    + windows(292, 34, 2, 1, 6, 8, 8, 0, DARK)
    + cypress(216, 66, 40, 7, OLIVE) + cypress(330, 66, 34, 6, OLIVE2))

T["past"]    = _land(240, 46, TERRA, "#E3D3B4", "#D8C39E", TAUPE, BROWN)
T["present"] = _land(278, 24, OCHRE, "#F2EADB", "#E7DCC6", SAND2, TAUPE)
T["future"]  = _land(326, 46, "#E8C77A", "#EFE6D2", "#E3D8BE", SAND, SAND2)


def build():
    return "\n".join(
        f'<g id="bg-{k}" stroke="#FAF5EA" stroke-width="1" '
        f'stroke-linejoin="round">{v}'
        f'<rect x="0" y="0" width="{TW}" height="{TH}" '
        f'fill="url(#tile-veil)" stroke="none"/></g>' for k, v in T.items())


if __name__ == "__main__":
    from pathlib import Path
    Path("tiles2.svgfrag").write_text(build(), encoding="utf-8")
    print("фонов:", len(T))
