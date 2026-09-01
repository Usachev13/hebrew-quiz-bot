# -*- coding: utf-8 -*-
"""Фоны кнопок — тот же плоский язык, но нарочно скупой.

На карточке темы деталей много, потому что она занимает пол-экрана и на
неё смотрят. Кнопка — это строка со словами, и рисунок здесь работает
как метка на полях: три-пять фигур, всё справа, слева чистое поле под
текст. Больше — и надпись начнёт спорить с картинкой.
"""
from art_kit import (P, rect, circ, dome, cypress, windows, crenel, arch_win,
                 gabled, tower, SAND, SAND2, OCHRE, TAUPE, STONE, BROWN,
                 DARK, OLIVE, OLIVE2, CREAM, TERRA)

TW, TH = 340, 88          # пропорция строки-кнопки
LEFT = 150                # левее этой границы не рисуем: там текст

T = {}

# Алфавит — скрижали
T["alphabet"] = (
    rect(196, 22, 44, 62, SAND2) + dome(218, 22, 22, SAND2)
    + rect(248, 26, 44, 58, SAND) + dome(270, 26, 22, SAND)
    + "".join(rect(204, 34 + i * 11, 28, 4, TAUPE, 2) for i in range(4))
    + "".join(rect(256, 38 + i * 11, 28, 4, TAUPE, 2) for i in range(4))
    + circ(312, 26, 13, OCHRE)
    + cypress(172, 84, 46, 8, OLIVE2))

# По темам — горстка домов
T["topics"] = (
    cypress(166, 84, 52, 9, OLIVE)
    + rect(186, 46, 40, 38, SAND) + dome(206, 46, 20, SAND2)
    + rect(230, 54, 34, 30, TAUPE) + gabled(268, 50, 34, 34, 14, SAND2)
    + rect(306, 58, 32, 26, STONE)
    + windows(192, 58, 2, 1, 7, 8, 8, 0, DARK)
    + windows(238, 64, 2, 1, 6, 7, 8, 0, DARK)
    + arch_win(285, 84, 12, 16, DARK))

# Грамматика — развёрнутый свиток
T["grammar"] = (
    rect(180, 20, 132, 56, CREAM)
    + rect(172, 16, 14, 64, OCHRE, 6) + rect(306, 16, 14, 64, OCHRE, 6)
    + "".join(rect(196, 28 + i * 11, 96 - i * 14, 4, TAUPE, 2) for i in range(4))
    + circ(330, 30, 9, SAND2))

# Глаголы — дорога к горизонту
T["verbs"] = (
    rect(150, 62, 190, 26, SAND2)
    + P("M198 88 L242 88 L268 58 L256 58 Z", CREAM)
    + "".join(rect(226 - i * 6, 76 - i * 10, 12 - i * 2, 4, SAND, 2) for i in range(3))
    + rect(288, 40, 6, 26, BROWN) + rect(272, 34, 38, 12, TERRA, 2)
    + cypress(174, 66, 46, 8, OLIVE2) + cypress(324, 64, 40, 7, OLIVE)
    + circ(246, 30, 12, OCHRE))

# Слабые места — фонарь над стеной
T["weak"] = (
    rect(150, 62, 190, 26, TAUPE) + crenel(150, 62, 190, 9, 6, TAUPE)
    + rect(262, 34, 5, 30, BROWN)
    + P("M248 34 L281 34 L274 16 L255 16 Z", OCHRE)
    + circ(264.5, 26, 6, CREAM)
    + circ(264.5, 26, 20, OCHRE).replace("/>", ' opacity=".22"/>')
    + cypress(180, 62, 44, 8, OLIVE2)
    + windows(300, 70, 3, 1, 6, 8, 8, 0, DARK))

# Всё вперемешку — разное рядом
T["mix"] = (
    rect(150, 70, 190, 18, SAND2)
    + rect(178, 44, 30, 26, TAUPE) + dome(193, 44, 15, TAUPE)
    + P("M226 70 V50 a7 7 0 0 1 5-7 h6 a7 7 0 0 1 5 7 v20 Z", OCHRE)
    + rect(228, 36, 14, 7, OCHRE, 3)
    + cypress(266, 70, 46, 8, OLIVE)
    + circ(300, 58, 12, TERRA) + circ(322, 62, 8, OLIVE2)
    + circ(312, 30, 10, SAND))

# Выбрать из вариантов — три ниши, одна освещена
T["choice"] = (
    rect(150, 66, 190, 22, TAUPE)
    + "".join(arch_win(186 + i * 46, 66, 30, 44, OCHRE if i == 1 else SAND2)
              for i in range(3))
    + circ(232, 40, 16, CREAM).replace("/>", ' opacity=".35"/>')
    + cypress(312, 66, 44, 8, OLIVE2))

# Написать самому — перо и чернильница
T["type"] = (
    rect(150, 70, 190, 18, SAND2)
    + rect(196, 52, 40, 18, CREAM, 3)
    + P("M254 70 V54 a10 10 0 0 1 20 0 v16 Z", TERRA)
    + rect(256, 46, 16, 8, TERRA, 3)
    + P("M296 22 L308 34 L272 68 L262 70 L264 60 Z", OCHRE)
    + P("M296 22 L308 34 L302 40 L290 28 Z", BROWN)
    + circ(322, 34, 9, SAND))

# Собрать из букв — камни россыпью
T["anagram"] = (
    rect(150, 70, 190, 18, SAND2)
    + rect(180, 48, 26, 22, TAUPE, 3) + rect(212, 40, 26, 30, SAND, 3)
    + rect(244, 52, 26, 18, OCHRE, 3) + rect(276, 44, 26, 26, STONE, 3)
    + rect(196, 22, 26, 22, CREAM, 3) + rect(252, 18, 26, 22, TERRA, 3)
    + rect(308, 50, 24, 20, SAND2, 3))


# Вуаль поперёк кнопки: слева бумага под текстом, справа рисунок дышит.
# Слева вуаль глухая до 60 % ширины — ровно до границы текстовой зоны.
# Плавный спад с самого края казался мягче, но проверка контраста
# показала: на 60 % подпись падала до 3.5:1 над охрой и терракотой, то
# есть переставала читаться. Теперь худший случай в зоне текста 5.07:1.
VEIL = ('<linearGradient id="tile-veil" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#FAF5EA" stop-opacity="1"/>'
        '<stop offset=".60" stop-color="#FAF5EA" stop-opacity="1"/>'
        '<stop offset=".76" stop-color="#FAF5EA" stop-opacity=".52"/>'
        '<stop offset="1" stop-color="#FAF5EA" stop-opacity=".05"/>'
        '</linearGradient>')


def block(k):
    """Просвет между фигурами — как на карточках тем."""
    return (f'<g id="bg-{k}" stroke="#FAF5EA" stroke-width="1" '
            f'stroke-linejoin="round">{T[k]}'
            f'<rect x="0" y="0" width="{TW}" height="{TH}" '
            f'fill="url(#tile-veil)" stroke="none"/></g>')


def build():
    return "\n".join(block(k) for k in T)


if __name__ == "__main__":
    from pathlib import Path
    Path("tiles.svgfrag").write_text(build(), encoding="utf-8")
    print("фонов:", len(T))
