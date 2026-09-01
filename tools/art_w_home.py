# -*- coding: utf-8 -*-
"""Дом (18), одежда (10), погода (10)."""
from art_wkit import *

W = {}

# ---------------------------------------------------------------- дом
W["дом"] = (shadow(rx=28) + house(24, 46, 52, 32, SAND2, "gable")
            + rect(42, 60, 16, 18, DARK) + windows(30, 52, 1, 1, 9, 9, 0, 0, CREAM)
            + windows(61, 52, 1, 1, 9, 9, 0, 0, CREAM))
W["квартира"] = (shadow(rx=28) + rect(22, 26, 56, 52, SAND)
                 + windows(28, 32, 3, 3, 12, 12, 3, 3, BLUE)
                 + rect(44, 66, 12, 12, DARK))
W["комната"] = (shadow(rx=30)
                + P("M14 26 L86 26 L86 62 L14 62 Z", CREAM)
                + P("M14 62 L86 62 L94 82 L6 82 Z", SAND2)
                + rect(24, 34, 20, 20, BLUE) + rect(23, 33, 22, 22, "none").replace(
                    'fill="none"', f'fill="none" stroke="{TAUPE}" stroke-width="3"')
                + rect(56, 46, 22, 16, TERRA, 3)
                + rect(60, 30, 14, 16, TAUPE, 2))
W["кухня"] = (shadow(rx=28) + rect(18, 54, 64, 24, SAND2)
              + rect(18, 50, 64, 5, TAUPE) + rect(24, 26, 20, 22, CREAM)
              + rect(52, 30, 28, 18, STONE) + circ(30, 60, 5, DARK) + circ(44, 60, 5, DARK)
              + jar(66, 50, 14, 12, TERRA))
W["туалет"] = (shadow(rx=20) + P("M34 78 V56 h30 v10 a12 12 0 0 1-12 12 Z", WHITE)
               + rect(30, 30, 22, 26, WHITE, 3) + rect(30, 52, 22, 5, STONE))
W["гостиная"] = (shadow(rx=30) + rect(16, 52, 68, 24, TERRA, 4)
                 + rect(16, 40, 12, 14, TERRA, 3) + rect(72, 40, 12, 14, TERRA, 3)
                 + rect(34, 44, 14, 10, CREAM, 2) + rect(52, 44, 14, 10, CREAM, 2)
                 + rect(38, 76, 24, 4, BROWN, 2))
W["спальня"] = (shadow(rx=30)
                + P("M10 24 L90 24 L90 58 L10 58 Z", CREAM)
                + rect(20, 30, 18, 18, BLUE)
                + rect(14, 60, 56, 16, SAND2, 3)
                + rect(14, 44, 7, 32, BROWN, 2)
                + rect(22, 52, 20, 10, WHITE, 3) + rect(42, 56, 26, 8, BLUE, 3)
                + rect(74, 62, 12, 14, BROWN, 2) + dome(80, 62, 9, OCHRE))
W["стол"] = (shadow(rx=28) + rect(16, 46, 68, 8, SAND2, 2)
             + rect(22, 54, 7, 26, BROWN) + rect(71, 54, 7, 26, BROWN))
W["стул"] = (shadow(rx=18) + rect(32, 52, 36, 8, SAND2, 2)
             + rect(60, 22, 8, 32, BROWN, 2)
             + rect(34, 60, 6, 20, BROWN) + rect(60, 60, 6, 20, BROWN))
W["кровать"] = (shadow(rx=30) + rect(14, 56, 72, 18, SAND2, 3)
                + rect(14, 34, 8, 40, BROWN, 2) + rect(78, 48, 8, 26, BROWN, 2)
                + rect(22, 46, 24, 12, WHITE, 3) + rect(46, 52, 32, 8, BLUE, 3))
W["дверь"] = (shadow(rx=20) + rect(30, 20, 40, 60, SAND2, 2)
              + rect(35, 26, 30, 22, SAND) + rect(35, 52, 30, 22, SAND)
              + circ(62, 52, 3.5, OCHRE))
W["окно"] = (shadow(rx=22) + rect(24, 22, 52, 52, BLUE)
             + rect(24, 22, 52, 52, "none").replace('fill="none"',
                 f'fill="none" stroke="{SAND2}" stroke-width="6"')
             + rect(47, 22, 6, 52, SAND2) + rect(24, 45, 52, 6, SAND2))
W["шкаф"] = (shadow(rx=22) + rect(26, 20, 48, 60, SAND2)
             + rect(49, 20, 3, 60, BROWN)
             + circ(45, 50, 2.6, OCHRE) + circ(56, 50, 2.6, OCHRE)
             + rect(30, 26, 15, 18, SAND) + rect(56, 26, 15, 18, SAND))
W["холодильник"] = (shadow(rx=20) + rect(30, 16, 40, 64, WHITE, 3)
                    + rect(30, 38, 40, 3, STONE)
                    + rect(62, 24, 4, 10, STONE, 2) + rect(62, 46, 4, 10, STONE, 2)
                    + rect(38, 52, 12, 12, BLUE, 2))
W["ключ"] = (shadow(rx=22) + circ(30, 50, 15, OCHRE) + circ(30, 50, 6, GAP)
             + rect(44, 46, 40, 8, OCHRE, 2)
             + rect(70, 54, 6, 10, OCHRE, 1) + rect(80, 54, 6, 8, OCHRE, 1))
W["пол"] = (shadow(rx=30)
            + P("M6 82 L26 44 L74 44 L94 82 Z", SAND2)
            + "".join(P(f"M{26 + i * 12} 44 L{16 + i * 19.5} 82 Z", "none").replace(
                'fill="none"', f'fill="none" stroke="{TAUPE}" stroke-width="2.5"')
                for i in range(5))
            + "".join(P(f"M{26 - i * 5} {44 + i * 9.5} H{74 + i * 5} Z", "none").replace(
                'fill="none"', f'fill="none" stroke="{TAUPE}" stroke-width="2.5"')
                for i in range(1, 4))
            + rect(4, 78, 92, 6, BROWN, 2))
W["балкон"] = (shadow(rx=26) + rect(20, 24, 60, 26, SAND)
               + rect(38, 26, 24, 24, BLUE)
               + rect(16, 50, 68, 6, SAND2)
               + "".join(rect(22 + i * 9, 56, 4, 20, TAUPE, 2) for i in range(7))
               + rect(16, 74, 68, 5, SAND2))
W["лестница"] = (shadow(rx=28)
                 + "".join(rect(16 + i * 12, 74 - i * 12, 26, 8, SAND2, 2)
                           for i in range(5)))

# ------------------------------------------------------------- одежда
W["одежда"] = (shadow(rx=28) + rect(12, 24, 76, 3, BROWN)
               + P("M22 30 l-6 4 l3 6 l3 -2 v22 h14 V38 l3 2 l3 -6 Z", TERRA)
               + P("M48 30 h16 l-3 8 h-2 v22 h-6 V38 h-2 Z", BLUE)
               + P("M74 30 l-6 4 l2 6 l3 -2 l-2 22 h12 l-2 -22 l3 2 l2 -6 Z", OCHRE))
W["рубашка"] = (shadow(rx=26) + P("M36 26 L50 32 L64 26 L84 36 L76 52 L68 48 V78 H32 V48 "
                                  "L24 52 L16 36 Z", CREAM)
                + windows(46, 44, 1, 3, 4, 4, 0, 6, STONE))
W["брюки"] = (shadow(rx=24) + P("M30 24 h40 l-4 54 h-12 l-4 -32 l-4 32 h-12 Z", BLUE2)
              + rect(30, 24, 40, 6, BLUE))
W["платье"] = (shadow(rx=26) + P("M38 26 l-12 8 l5 7 l5 -3 l-8 40 h44 l-8 -40 l5 3 l5 -7 "
                                 "l-12 -8 Z", TERRA)
               + P("M42 26 q8 8 16 0", "none").replace('fill="none"',
                   f'fill="none" stroke="{RED}" stroke-width="2.5"'))
W["юбка"] = (shadow(rx=26) + P("M34 32 h32 l12 46 h-56 Z", OCHRE)
             + rect(32, 26, 36, 7, BROWN, 2))
W["обувь"] = (shadow(rx=26)
              + P("M18 74 V52 q0 -6 8 -6 h10 q3 0 5 3 l10 12 q3 4 9 5 l14 3 "
                  "q8 2 8 8 v3 Z", TERRA)
              + rect(16, 72, 66, 6, DARK, 2)
              + P("M28 50 q8 -2 12 4", "none").replace('fill="none"',
                  f'fill="none" stroke="{SAND2}" stroke-width="3" stroke-linecap="round"')
              + circ(40, 62, 3, SAND2) + circ(52, 66, 3, SAND2))
W["куртка"] = (shadow(rx=26) + P("M34 26 L50 32 L66 26 L84 38 L78 54 L70 50 V78 H30 V50 "
                                 "L22 54 L16 38 Z", OLIVE)
               + rect(48, 32, 4, 46, OLIVE2)
               + rect(34, 56, 10, 8, OLIVE2, 2) + rect(56, 56, 10, 8, OLIVE2, 2))
W["шляпа"] = (shadow(rx=28) + P("M30 58 V40 a20 20 0 0 1 40 0 v18 Z", SAND2)
              + rect(14, 56, 72, 8, SAND, 4) + rect(30, 48, 40, 8, TERRA))
W["носки"] = (shadow(rx=26) + P("M28 24 h14 v26 l-12 12 a9 9 0 0 1-13-13 l11 -11 Z", CREAM)
              + P("M56 24 h14 v26 l-12 12 a9 9 0 0 1-13-13 l11 -11 Z", BLUE)
              + rect(28, 24, 14, 6, TERRA) + rect(56, 24, 14, 6, TERRA))
W["очки"] = (shadow(rx=28) + circ(30, 52, 16, "none").replace('fill="none"',
                 f'fill="none" stroke="{DARK}" stroke-width="5"')
             + circ(70, 52, 16, "none").replace('fill="none"',
                 f'fill="none" stroke="{DARK}" stroke-width="5"')
             + rect(46, 50, 8, 4, DARK)
             + circ(30, 52, 13, BLUE) + circ(70, 52, 13, BLUE))

# ------------------------------------------------------------- погода
W["погода"] = (circ(34, 34, 15, OCHRE)
               + P("M36 74 a13 13 0 0 1 3-25 a18 18 0 0 1 34-3 a11 11 0 0 1 2 28 Z", CREAM)
               + "".join(rect(34 + i * 14, 78, 3, 10, BLUE, 1.5) for i in range(3)))
W["солнце"] = (circ(50, 50, 20, OCHRE)
               + "".join(P(f"M{50 + 26 * __import__('math').cos(a):.1f} "
                           f"{50 + 26 * __import__('math').sin(a):.1f} "
                           f"L{50 + 36 * __import__('math').cos(a):.1f} "
                           f"{50 + 36 * __import__('math').sin(a):.1f} Z", "none").replace(
                   'fill="none"', f'fill="none" stroke="{OCHRE}" stroke-width="5" '
                   'stroke-linecap="round"')
                   for a in [i * 0.785 for i in range(8)]))
W["дождь"] = (P("M28 54 a13 13 0 0 1 3-25 a18 18 0 0 1 34-3 a11 11 0 0 1 2 28 Z", STONE)
              + "".join(P(f"M{26 + i * 14} 62 L{22 + i * 14} 82 Z", "none").replace(
                  'fill="none"', f'fill="none" stroke="{BLUE}" stroke-width="4" '
                  'stroke-linecap="round"') for i in range(4)))
W["ветер"] = ("".join(P(f"M14 {32 + i * 16} h{40 + i * 8} a7 7 0 1 0 -7 -7", "none").replace(
                  'fill="none"', f'fill="none" stroke="{STONE}" stroke-width="5" '
                  'stroke-linecap="round"') for i in range(3)))
W["облако"] = P("M26 70 a15 15 0 0 1 3-28 a20 20 0 0 1 38-3 a13 13 0 0 1 2 31 Z", CREAM)
W["жара"] = (circ(50, 40, 18, TERRA)
             + "".join(P(f"M{30 + i * 20} 66 q6 8 0 16", "none").replace(
                 'fill="none"', f'fill="none" stroke="{TERRA}" stroke-width="4" '
                 'stroke-linecap="round"') for i in range(3)))
W["холод"] = ("".join(P(f"M50 50 L{50 + 30 * __import__('math').cos(a):.1f} "
                        f"{50 + 30 * __import__('math').sin(a):.1f} Z", "none").replace(
                  'fill="none"', f'fill="none" stroke="{BLUE}" stroke-width="5" '
                  'stroke-linecap="round"') for a in [i * 1.047 for i in range(6)])
              + circ(50, 50, 7, BLUE2))
W["снег"] = (P("M26 52 a13 13 0 0 1 3-25 a18 18 0 0 1 34-3 a11 11 0 0 1 2 28 Z", WHITE)
             + "".join(circ(26 + i * 14, 66 + (i % 2) * 10, 4.5, BLUE) for i in range(4)))
W["небо"] = (rect(10, 22, 80, 56, BLUE, 6)
             + P("M22 56 a10 10 0 0 1 2-19 a13 13 0 0 1 25-2 a9 9 0 0 1 1 21 Z", WHITE)
             + P("M56 68 a8 8 0 0 1 2-15 a11 11 0 0 1 21-2 a7 7 0 0 1 1 17 Z", CREAM))
W["море"] = (rect(10, 40, 80, 38, BLUE, 4)
             + "".join(P(f"M14 {50 + i * 10} q10 -6 20 0 t20 0 t20 0 t12 0", "none").replace(
                 'fill="none"', f'fill="none" stroke="{WHITE}" stroke-width="3" '
                 'stroke-linecap="round"') for i in range(3))
             + circ(74, 30, 10, OCHRE))
