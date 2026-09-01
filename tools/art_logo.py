# -*- coding: utf-8 -*-
"""Логотип бота в том же плоском языке, что и приложение.

Главное ограничение — не красота, а размер: аватарка в списке чатов
показывается примерно на сорока пикселях. Всё, что мельче крупного
пятна, там исчезает. Поэтому фигур мало, они крупные, и проверяется
знак сразу в трёх размерах.
"""
from art_kit import P, rect, circ, dome, cypress, crenel, arch_win
import art_hebtext as hebtext

S = 512          # рисуем в квадрате, Telegram сам обрежет в круг
BG    = "#F1E7D2"
SAND  = "#DCC69E"
SAND2 = "#CBAA7C"
OCHRE = "#C29F5E"
TAUPE = "#AE9878"
TERRA = "#B0703C"
OLIVE = "#6E7A5A"
DARK  = "#6B4F3A"


# Алеф в жирном начертании неизбежно читается косым крестом: его
# главная диагональ и два плеча складываются в X, и на аватарке это уже
# не буква. Три попытки — разная толщина, разная длина плеч, разные их
# углы — дали один и тот же результат. Поэтому знак строится не на
# букве.


def _bet(cx, cy, k, fill):
    """Бет — вторая буква, но единственная из простых, чей силуэт не с
    чем спутать: горизонтальное основание, стойка справа и короткая
    полка сверху."""
    def p(x, y):
        return f"{cx + x * k:.1f} {cy + y * k:.1f}"
    top = P(f"M{p(-40,-64)} L{p(46,-64)} L{p(46,-36)} L{p(-40,-36)} Z", fill)
    right = P(f"M{p(18,-36)} L{p(46,-36)} L{p(46,40)} L{p(18,40)} Z", fill)
    base = P(f"M{p(-56,40)} L{p(60,40)} L{p(60,68)} L{p(-56,68)} Z", fill)
    return top + right + base


NAME_HE = "אני לומד עברית"


def _scene(inner, ground=0.74, arch_top=0.40, arch_bottom=0.80):
    """Ворота, солнце, кипарисы. ground сдвигает землю вверх, когда под
    рисунком нужно место для надписи."""
    g, gd = ground, ground + 0.115
    b = [rect(0, 0, S, S, BG)]
    b.append(circ(S*0.78, S*(g - 0.48), S*0.115, OCHRE))
    b.append(P(f"M0 {S*g} Q{S*0.32} {S*(g-0.06)} {S*0.58} {S*(g-0.01)} "
               f"Q{S*0.82} {S*(g+0.03)} {S} {S*(g-0.02)} V{S} H0 Z", SAND))
    b.append(P(f"M0 {S*gd} Q{S*0.36} {S*(gd-0.055)} {S*0.64} {S*gd} "
               f"Q{S*0.86} {S*(gd+0.035)} {S} {S*(gd-0.005)} V{S} H0 Z", TAUPE))
    b.append(cypress(S*0.115, S*(g+0.09), S*0.32, S*0.055, OLIVE, DARK))
    b.append(cypress(S*0.895, S*(g+0.09), S*0.26, S*0.048, OLIVE, DARK))
    b.append(P(f"M{S*0.235} {S*arch_bottom} V{S*arch_top} "
               f"A{S*0.265} {S*0.265} 0 0 1 {S*0.765} {S*arch_top} "
               f"V{S*arch_bottom} Z", TERRA))
    b.append(inner)
    return "".join(b)


def _doorway(arch_bottom=0.80, top=0.53):
    return P(f"M{S*0.375} {S*arch_bottom} V{S*top} "
             f"A{S*0.125} {S*0.125} 0 0 1 {S*0.625} {S*top} V{S*arch_bottom} Z", BG)


def logo_gate():
    """Только знак. Для аватарки: на сорока пикселях надпись всё равно
    превращается в полоску, и ставить её туда — самообман."""
    return _scene(_doorway())


def logo_bet():
    return _scene(_bet(S*0.50, S*0.545, S*0.0030, BG))


def logo_wordmark():
    """Знак с названием. Сцена поджата кверху, снизу — светлая полка с
    надписью: на ней контраст выше, чем на песке."""
    body = _scene(_doorway(arch_bottom=0.635, top=0.415),
                  ground=0.585, arch_top=0.25, arch_bottom=0.635)
    body += rect(0, S*0.755, S, S*0.245, BG)
    body += hebtext.centered(NAME_HE, S*0.115, S*0.5, S*0.915, DARK)
    return body


def logo_wide(W=1200, H=400):
    """Горизонтальный вариант: знак слева, название справа.

    Ширину надписи считаем, а не подбираем: на глаз она наезжала на знак.
    """
    k = H / S
    pad = H * 0.16
    mark_w = H
    mark = f'<g transform="translate(0 0) scale({k:.4f})">{logo_gate()}</g>'

    he_size = H * 0.30
    he_w = hebtext.measure(NAME_HE, he_size)
    right = W - pad
    # Если надпись не влезает между знаком и краем — уменьшаем её, а не
    # сдвигаем на знак.
    room = right - (mark_w + pad)
    if he_w > room:
        he_size *= room / he_w
        he_w = hebtext.measure(NAME_HE, he_size)
    he = hebtext.text_paths(NAME_HE, he_size, right, H * 0.56, DARK)[0]

    lat_size = he_size * 0.36
    lat_body, lat_w = hebtext.text_paths_ltr("Ani Lomed Ivrit", lat_size,
                                             right, H * 0.80, TAUPE)
    lat = hebtext.text_paths_ltr("Ani Lomed Ivrit", lat_size,
                                 right - lat_w, H * 0.80, TAUPE)[0]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="{BG}"/>'
            f'<g stroke="{BG}" stroke-width="2" stroke-linejoin="round">{mark}</g>'
            f'{he}{lat}</svg>')


logo = logo_gate


def svg(size=S, round_=False, art=None):
    clip = (f'<clipPath id="r"><rect width="{S}" height="{S}" rx="{S*0.22}"/></clipPath>'
            if round_ else "")
    body = (art or logo)()
    g = f'<g clip-path="url(#r)">{body}</g>' if round_ else body
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" '
            f'width="{size}" height="{size}"><defs>{clip}</defs>'
            f'<g stroke="#F7F2E6" stroke-width="2" stroke-linejoin="round">{g}</g></svg>')


if __name__ == "__main__":
    from pathlib import Path
    Path("logo.svg").write_text(svg(round_=True), encoding="utf-8")
    print("logo.svg")
