# -*- coding: utf-8 -*-
"""Картинки к словам темы «Еда» — 26 штук."""
from art_wkit import *

W = {}

W["хлеб"] = (shadow(rx=24) + P("M20 78 a30 22 0 0 1 60 0 Z", SAND2)
             + rect(30, 62, 5, 5, DARK, 2) + rect(46, 58, 5, 5, DARK, 2)
             + rect(60, 63, 5, 5, DARK, 2))
W["вода"] = (shadow(rx=16) + P("M34 40 h32 l-4 42 h-24 Z", BLUE)
             + rect(32, 34, 36, 7, WHITE, 2)
             + P("M36 52 h28 l-2 26 h-24 Z", BLUE2))
W["молоко"] = (shadow(rx=17) + bottle(50, 82, 34, 52, WHITE)
               + rect(38, 58, 24, 18, BLUE) + rect(44, 26, 12, 6, BLUE2, 2))
W["сыр"] = (shadow(rx=25) + P("M18 78 L18 54 L82 40 L82 66 Z", OCHRE)
            + P("M18 54 L82 40 L82 46 L18 60 Z", SAND)
            + circ(34, 66, 4, SAND) + circ(52, 60, 5, SAND) + circ(68, 56, 3.5, SAND))
W["яйцо"] = (shadow(rx=17) + P("M50 22 C68 22 74 48 74 58 a24 24 0 0 1-48 0 "
                               "C26 48 32 22 50 22 Z", WHITE)
             + circ(44, 48, 6, SAND))
W["мясо"] = (shadow(rx=24) + P("M22 74 C18 52 34 38 54 40 C74 42 82 60 74 72 Z", TERRA)
             + P("M30 68 C28 54 40 46 54 48 C68 50 72 62 66 70 Z", RED)
             + rect(70, 56, 14, 8, CREAM, 4))
W["курица (мясо)"] = (shadow(rx=20) + P("M30 78 C24 62 32 46 48 44 C64 42 74 54 70 68 "
                      "C66 80 42 86 30 78 Z", SAND2)
                      + P("M64 50 L82 32 L88 40 L70 56 Z", CREAM)
                      + rect(78, 28, 12, 6, STONE, 3)
                      + circ(44, 60, 5, OCHRE) + circ(56, 66, 4, OCHRE))
W["рыба"] = (shadow(rx=25) + P("M22 58 C34 38 62 38 74 58 C62 78 34 78 22 58 Z", BLUE)
             + P("M74 58 L88 44 L88 72 Z", BLUE2) + circ(34, 54, 4, WHITE)
             + circ(34, 54, 2, DARK))
W["рис"] = (shadow(rx=24) + P("M22 62 h56 a28 20 0 0 1-56 0 Z", CREAM)
            + P("M26 58 a24 16 0 0 1 48 0 Z", WHITE)
            + "".join(rect(32 + (i % 6) * 7, 46 + (i // 6) * 5, 5, 2.6, STONE, 1.3)
                      for i in range(16))
            + rect(20, 56, 60, 5, TAUPE, 2))
W["суп"] = (shadow(rx=25) + P("M20 60 h60 a30 22 0 0 1-60 0 Z", TERRA)
            + rect(17, 55, 66, 6, SAND2, 3)
            + circ(36, 52, 4, OLIVE) + circ(50, 50, 4, OCHRE) + circ(62, 52, 4, OLIVE2)
            + P("M40 34 q-6 -8 0 -14 M60 34 q-6 -8 0 -14", "none").replace(
                'fill="none"', f'fill="none" stroke="{TAUPE}" stroke-width="3" '
                'stroke-linecap="round"'))
W["салат"] = (shadow(rx=25) + plate(w=62)
              + leaf(38, 58, 18, 26, OLIVE, -25) + leaf(58, 56, 18, 26, OLIVE2, 20)
              + circ(48, 66, 6, RED) + circ(64, 68, 5, TERRA))
W["овощи"] = (shadow(rx=26) + circ(30, 64, 14, RED) + P("M30 50 l-4 -8 h8 Z", OLIVE)
              + P("M50 78 C42 70 44 52 50 44 C56 52 58 70 50 78 Z", OLIVE)
              + circ(72, 62, 13, OCHRE) + P("M72 49 l-3 -7 h6 Z", OLIVE2))
W["фрукты"] = (shadow(rx=26) + circ(32, 62, 15, TERRA) + P("M32 47 l2 -8 l7 3 Z", OLIVE)
               + circ(56, 66, 13, OCHRE) + circ(74, 58, 11, OLIVE))
W["яблоко"] = (shadow(rx=19) + P("M50 34 C62 26 78 34 80 52 C82 70 66 82 50 82 "
                                 "C34 82 18 70 20 52 C22 34 38 26 50 34 Z", TERRA)
               + P("M50 34 L52 18 M52 22 C62 14 72 18 70 26 C64 32 54 30 52 22 Z", OLIVE))
W["апельсин"] = (shadow(rx=19) + circ(50, 58, 24, OCHRE)
                 + P("M50 34 L50 82 M28 58 L72 58", "none").replace(
                     'fill="none"', f'fill="none" stroke="{SAND}" stroke-width="2.5"')
                 + P("M50 34 l4 -12 l10 4 Z", OLIVE))
W["помидор"] = (shadow(rx=19) + circ(50, 60, 22, RED)
                + P("M50 38 l-10 -8 h20 Z", OLIVE) + circ(50, 38, 5, OLIVE2))
W["огурец"] = (shadow(rx=22) + P("M28 76 C20 60 30 34 52 30 C70 27 78 40 72 54 "
                                 "C64 72 42 84 28 76 Z", OLIVE)
               + P("M36 70 C30 58 38 40 54 37", "none").replace(
                   'fill="none"', f'fill="none" stroke="{OLIVE2}" stroke-width="3" '
                   'stroke-linecap="round"'))
W["сливочное масло"] = (shadow(rx=24) + plate(w=58)
                        + P("M28 62 L28 46 L64 40 L64 56 Z", OCHRE)
                        + P("M28 46 L64 40 L72 46 L36 52 Z", SAND)
                        + P("M64 40 L72 46 L72 62 L64 56 Z", SAND2)
                        + rect(30, 60, 40, 4, CREAM, 2))
W["сахар"] = (shadow(rx=22) + rect(24, 52, 24, 24, WHITE, 3)
              + rect(52, 52, 24, 24, CREAM, 3) + rect(38, 30, 24, 22, WHITE, 3))
W["соль"] = (shadow(rx=15) + P("M36 80 V44 q0 -8 14 -8 q14 0 14 8 v36 Z", WHITE)
             + dome(50, 36, 14, STONE)
             + circ(45, 30, 2, DARK) + circ(52, 28, 2, DARK) + circ(56, 32, 2, DARK))
W["кофе"] = (shadow(rx=20) + cup(48, 78, 40, 34, DARK)
             + rect(28, 42, 40, 6, TERRA, 2)
             + P("M42 32 q-6 -8 0 -14 M56 32 q-6 -8 0 -14", "none").replace(
                 'fill="none"', f'fill="none" stroke="{TAUPE}" stroke-width="3" '
                 'stroke-linecap="round"'))
W["чай"] = (shadow(rx=20) + P("M30 44 h38 l-5 34 h-28 Z", TERRA)
            + P("M28 40 h42 l-2 6 h-38 Z", CREAM)
            + P("M34 52 h30 l-4 24 h-22 Z", OCHRE)
            + P("M66 34 L76 20 L82 26 L70 38 Z", OLIVE))
W["вино"] = (shadow(rx=15) + P("M34 26 h32 l-4 22 a12 12 0 0 1-24 0 Z", TERRA)
             + rect(48, 48, 4, 24, STONE) + rect(36, 72, 28, 5, STONE, 2)
             + P("M36 34 h28 l-2 10 h-24 Z", RED))
W["завтрак"] = (shadow(rx=26) + circ(80, 24, 12, OCHRE)
                + P("M64 24 h32", "none").replace('fill="none"',
                    f'fill="none" stroke="{SAND}" stroke-width="3"')
                + plate(cx=42, w=48)
                + P("M42 44 a11 11 0 0 1 0 22 a11 11 0 0 1 0 -22 Z", WHITE)
                + circ(42, 55, 6, OCHRE)
                + cup(78, 76, 24, 20, WHITE, False))
W["обед"] = (shadow(rx=26) + circ(50, 20, 13, OCHRE)
             + "".join(P(f"M{50 + 18 * __import__('math').cos(a)} "
                         f"{20 + 18 * __import__('math').sin(a)} "
                         f"L{50 + 24 * __import__('math').cos(a)} "
                         f"{20 + 24 * __import__('math').sin(a)} Z", "none").replace(
                 'fill="none"', f'fill="none" stroke="{OCHRE}" stroke-width="2.5" '
                 'stroke-linecap="round"')
                 for a in [i * 0.785 for i in range(8)])
             + plate(cx=50, cy=78, w=56)
             + circ(50, 66, 15, TERRA) + circ(50, 66, 8, SAND2)
             + rect(14, 52, 4, 26, STONE, 2) + rect(82, 52, 4, 26, STONE, 2))
W["ужин"] = (shadow(rx=26)
             + P("M76 12 a13 13 0 1 0 10 21 a15 15 0 0 1-10-21 Z", CREAM)
             + circ(30, 20, 1.6, CREAM) + circ(58, 14, 1.4, CREAM)
             + plate(cx=44, cy=78, w=52)
             + circ(44, 66, 13, SAND2) + circ(44, 66, 6, TERRA)
             + P("M74 46 h8 l-2 32 h-4 Z", CREAM) + circ(78, 44, 4, OCHRE))
