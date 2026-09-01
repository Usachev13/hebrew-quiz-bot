# -*- coding: utf-8 -*-
"""Логотип бота в том же плоском языке, что и приложение.

Главное ограничение — не красота, а размер: аватарка в списке чатов
показывается примерно на сорока пикселях. Всё, что мельче крупного
пятна, там исчезает. Поэтому фигур мало, они крупные, и проверяется
знак сразу в трёх размерах.
"""
from art_kit import P, rect, circ, dome, cypress, crenel, arch_win

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


def _scene(inner):
    b = [rect(0, 0, S, S, BG)]
    b.append(circ(S*0.78, S*0.26, S*0.115, OCHRE))
    b.append(P(f"M0 {S*0.74} Q{S*0.32} {S*0.68} {S*0.58} {S*0.73} "
               f"Q{S*0.82} {S*0.77} {S} {S*0.72} V{S} H0 Z", SAND))
    b.append(P(f"M0 {S*0.855} Q{S*0.36} {S*0.80} {S*0.64} {S*0.855} "
               f"Q{S*0.86} {S*0.89} {S} {S*0.85} V{S} H0 Z", TAUPE))
    b.append(cypress(S*0.115, S*0.83, S*0.32, S*0.055, OLIVE, DARK))
    b.append(cypress(S*0.895, S*0.83, S*0.26, S*0.048, OLIVE, DARK))
    b.append(P(f"M{S*0.235} {S*0.80} V{S*0.40} "
               f"A{S*0.265} {S*0.265} 0 0 1 {S*0.765} {S*0.40} V{S*0.80} Z", TERRA))
    b.append(inner)
    return "".join(b)


def logo_gate():
    """Ворота: в проёме — арка входа. Ни одной мелкой детали, знак
    держится на двух пятнах и просвете между ними."""
    return _scene(P(f"M{S*0.375} {S*0.80} V{S*0.53} "
                    f"A{S*0.125} {S*0.125} 0 0 1 {S*0.625} {S*0.53} V{S*0.80} Z", BG))


def logo_bet():
    """Ворота с буквой бет в проёме."""
    return _scene(_bet(S*0.50, S*0.545, S*0.0030, BG))


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
