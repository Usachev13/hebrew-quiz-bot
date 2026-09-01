# -*- coding: utf-8 -*-
"""Здоровье (17), эмоции (11), приветствия (12)."""
from art_wkit import *

W = {}

def _face(cx=50, cy=46, r=26, skin=SKIN, hair=HAIR_D):
    return (circ(cx, cy, r, skin)
            + P(f"M{cx-r} {cy-r*0.12} a{r} {r} 0 0 1 {r*2} 0 "
                f"a{r} {r*0.5} 0 0 0 -{r*2} 0 Z", hair))

def _eyes(cx=50, cy=44, dx=10, r=3.2, c=DARK):
    return circ(cx-dx, cy, r, c) + circ(cx+dx, cy, r, c)

# ------------------------------------------------------------ здоровье
W["врач"] = (shadow(rx=22) + figure(50, 80, 58, WHITE, HAIR_D)
             + rect(44, 46, 12, 26, WHITE)
             + rect(46, 52, 8, 3, RED) + rect(49, 49, 3, 9, RED)
             + P("M40 42 q10 16 20 0", "none").replace('fill="none"',
                 f'fill="none" stroke="{STONE}" stroke-width="2.5"')
             + circ(50, 60, 4, STONE))
W["больной"] = (shadow(rx=22) + rect(12, 58, 76, 18, SAND2, 3)
                + rect(12, 40, 8, 36, BROWN, 2)
                + circ(34, 50, 12, SKIN)
                + P("M22 50 a12 12 0 0 1 24 0 a12 6 0 0 0 -24 0 Z", HAIR_D)
                + rect(46, 56, 34, 10, WHITE, 3)
                + P("M28 54 q6 4 12 0", "none").replace('fill="none"',
                    f'fill="none" stroke="{DARK}" stroke-width="2"')
                + rect(30, 30, 22, 7, RED, 3))
W["здоровый"] = (shadow(rx=24)
                 + circ(50, 26, 12, SKIN)
                 + P("M38 26 a12 12 0 0 1 24 0 a12 6 0 0 0 -24 0 Z", HAIR_D)
                 + P("M36 80 V50 a14 14 0 0 1 28 0 v30 Z", OLIVE)
                 + P("M36 54 L18 30 M64 54 L82 30", "none").replace('fill="none"',
                     f'fill="none" stroke="{SKIN}" stroke-width="9" stroke-linecap="round"')
                 + P("M70 66 l7 8 l14 -18", "none").replace('fill="none"',
                     f'fill="none" stroke="{OLIVE2}" stroke-width="6" '
                     'stroke-linecap="round" stroke-linejoin="round"'))
W["боль"] = (shadow(rx=22) + _face() + _eyes(cy=42, r=2.6)
             + P("M40 58 q10 -8 20 0", "none").replace('fill="none"',
                 f'fill="none" stroke="{DARK}" stroke-width="3" stroke-linecap="round"')
             + "".join(P(f"M{74 + i*4} {20 + i*6} l6 4 l-6 4", "none").replace(
                 'fill="none"', f'fill="none" stroke="{RED}" stroke-width="3" '
                 'stroke-linecap="round"') for i in range(3)))
W["голова"] = (shadow(rx=22) + _face(cy=48, r=28)
               + _eyes(cy=46, dx=11) + P("M38 62 q12 8 24 0", "none").replace(
                   'fill="none"', f'fill="none" stroke="{DARK}" stroke-width="2.5" '
                   'stroke-linecap="round"')
               + P("M50 48 v8 h4", "none").replace('fill="none"',
                   f'fill="none" stroke="{TAUPE}" stroke-width="2"'))
W["рука"] = (shadow(rx=20) + P("M38 82 V50 q0 -6 6 -6 q6 0 6 6 v-6 q0 -7 6 -7 "
                               "q6 0 6 7 v2 q0 -6 6 -6 q6 0 6 6 v20 q0 14 -14 16 Z", SKIN)
             + P("M38 60 q-10 -4 -12 4 q-2 8 8 10", "none").replace('fill="none"',
                 f'fill="none" stroke="{SKIN}" stroke-width="9" stroke-linecap="round"'))
W["нога"] = (shadow(cx=58, rx=22)
             + P("M34 12 h26 q6 0 5 8 l-6 26 q-1 6 -6 10 l-8 8 q-4 4 -4 10 v8 h-14 "
                 "v-12 q0 -8 5 -14 l8 -10 q3 -4 2 -10 l-6 -18 q-2 -6 -2 -6 Z", SKIN)
             + P("M27 74 h30 a7 7 0 0 1 0 10 H27 Z", SKIN)
             + rect(25, 82, 34, 5, TERRA, 2))
W["глаз"] = (shadow(rx=22) + P("M12 50 q38 -30 76 0 q-38 30 -76 0 Z", WHITE)
             + circ(50, 50, 15, BLUE) + circ(50, 50, 7, DARK)
             + circ(45, 45, 4, WHITE))
W["ухо"] = (shadow(rx=18) + P("M62 20 q-30 0 -30 30 q0 22 14 32 q10 6 12 -4 "
                              "q2 -10 -4 -14 q-8 -6 -2 -14 q6 -8 14 -6 q12 4 12 -10 "
                              "q0 -14 -16 -14 Z", SKIN)
             + P("M52 42 q-8 6 -2 14", "none").replace('fill="none"',
                 f'fill="none" stroke="{TAUPE}" stroke-width="2.5" stroke-linecap="round"'))
W["рот"] = (shadow(rx=24) + P("M14 50 q36 -26 72 0 q-36 26 -72 0 Z", RED)
            + P("M14 50 h72", "none").replace('fill="none"',
                f'fill="none" stroke="{WHITE}" stroke-width="4"')
            + P("M22 46 q28 -14 56 0 Z", WHITE))
W["нос"] = (shadow(rx=18) + P("M50 16 q-6 24 -12 38 q-4 10 4 12 h16 q8 -2 4 -12 "
                              "q-6 -14 -12 -38 Z", SKIN)
            + circ(42, 62, 3.4, TAUPE) + circ(58, 62, 3.4, TAUPE))
W["зуб"] = (shadow(rx=20) + P("M26 22 h48 q7 0 7 9 v18 q0 17 -9 30 q-5 7 -9 -2 "
                              "l-7 -17 l-7 17 q-4 9 -9 2 q-9 -13 -9 -30 V31 q0 -9 7 -9 Z",
                              STONE)
            + P("M30 26 h40 q4 0 4 6 v15 q0 15 -7 26 q-4 6 -7 -2 l-6 -15 l-6 15 "
                "q-3 8 -7 2 q-7 -11 -7 -26 V32 q0 -6 4 -6 Z", WHITE)
            + P("M36 34 q14 -5 28 0", "none").replace('fill="none"',
                f'fill="none" stroke="{STONE}" stroke-width="2.5"'))
W["живот"] = (shadow(rx=24) + P("M50 14 q-28 0 -28 30 q0 30 28 36 q28 -6 28 -36 "
                                "q0 -30 -28 -30 Z", SKIN)
              + P("M34 40 q16 8 32 0 M32 54 q18 8 36 0", "none").replace('fill="none"',
                  f'fill="none" stroke="{TAUPE}" stroke-width="2.5" '
                  'stroke-linecap="round"')
              + circ(50, 60, 4.5, TAUPE))
W["спина"] = (shadow(rx=24) + P("M32 20 h36 q8 0 8 10 l-4 46 q-1 8 -8 8 H36 q-7 0 -8 -8 "
                                "l-4 -46 q0 -10 8 -10 Z", SKIN)
              + rect(48, 24, 4, 56, TAUPE, 2)
              + "".join(rect(44, 30 + i * 10, 12, 3, TAUPE, 1.5) for i in range(5)))
W["сердце"] = (shadow(rx=24) + P("M50 82 C24 60 14 48 14 36 a16 16 0 0 1 36 -8 "
                                 "a16 16 0 0 1 36 8 c0 12 -10 24 -36 46 Z", RED)
               + P("M22 44 h14 l6 -10 l8 20 l6 -12 l4 2 h18", "none").replace(
                   'fill="none"', f'fill="none" stroke="{WHITE}" stroke-width="3" '
                   'stroke-linecap="round" stroke-linejoin="round"'))
W["лекарство"] = (shadow(rx=26)
                  + f'<g transform="rotate(-35 36 50)">'
                  + rect(16, 40, 40, 20, TERRA, 10)
                  + rect(16, 40, 20, 20, CREAM, 10) + '</g>'
                  + rect(60, 44, 26, 34, WHITE, 3)
                  + rect(64, 36, 18, 9, STONE, 2)
                  + rect(66, 56, 14, 4, TERRA, 2) + rect(66, 64, 14, 4, TERRA, 2))
W["больничная касса"] = (shadow(rx=28) + rect(18, 30, 64, 46, CREAM, 4)
                         + rect(18, 30, 64, 12, OLIVE, 4)
                         + rect(44, 48, 12, 22, OLIVE) + rect(38, 54, 24, 10, OLIVE)
                         + rect(24, 34, 20, 4, WHITE, 2))

# -------------------------------------------------------------- эмоции
W["радость"] = (shadow(rx=26) + _face() + _eyes(cy=42, r=3)
                + P("M34 54 q16 16 32 0", "none").replace('fill="none"',
                    f'fill="none" stroke="{DARK}" stroke-width="3.5" '
                    'stroke-linecap="round"')
                + "".join(P(f"M{x} {y-6} Q{x} {y} {x+5} {y} Q{x} {y} {x} {y+6} "
                            f"Q{x} {y} {x-5} {y} Q{x} {y} {x} {y-6} Z", OCHRE)
                          for x, y in ((16, 22), (84, 26), (80, 68))))
W["грусть"] = (shadow(rx=26) + _face() + _eyes(cy=42, r=3)
               + P("M34 62 q16 -14 32 0", "none").replace('fill="none"',
                   f'fill="none" stroke="{DARK}" stroke-width="3.5" '
                   'stroke-linecap="round"')
               + P("M40 50 q3 8 0 10 q-6 -2 0 -10 Z", BLUE))
W["любовь"] = (shadow(rx=26) + P("M50 80 C26 60 16 48 16 37 a15 15 0 0 1 34 -7 "
                                 "a15 15 0 0 1 34 7 c0 11 -10 23 -34 43 Z", RED)
               + P("M34 34 q6 -6 12 -2", "none").replace('fill="none"',
                   f'fill="none" stroke="{WHITE}" stroke-width="4" stroke-linecap="round"'))
W["страх"] = (shadow(rx=26) + _face()
              + circ(40, 42, 5, WHITE) + circ(60, 42, 5, WHITE)
              + circ(40, 42, 2.4, DARK) + circ(60, 42, 2.4, DARK)
              + P("M44 60 a6 8 0 0 1 12 0 a6 8 0 0 1 -12 0 Z", DARK)
              + P("M20 22 l6 8 M80 22 l-6 8", "none").replace('fill="none"',
                  f'fill="none" stroke="{STONE}" stroke-width="3" stroke-linecap="round"'))
W["счастливый"] = (shadow(rx=26) + _face(hair=HAIR_L)
                   + P("M36 40 q5 -5 10 0 M54 40 q5 -5 10 0", "none").replace(
                       'fill="none"', f'fill="none" stroke="{DARK}" stroke-width="3" '
                       'stroke-linecap="round"')
                   + P("M32 52 q18 20 36 0 Z", DARK)
                   + circ(30, 56, 5, RED) + circ(70, 56, 5, RED))
W["сердитый"] = (shadow(rx=26) + _face()
                 + P("M34 36 l14 6 M66 36 l-14 6", "none").replace('fill="none"',
                     f'fill="none" stroke="{DARK}" stroke-width="3.5" '
                     'stroke-linecap="round"')
                 + _eyes(cy=48, r=3)
                 + P("M36 64 q14 -10 28 0", "none").replace('fill="none"',
                     f'fill="none" stroke="{DARK}" stroke-width="3.5" '
                     'stroke-linecap="round"')
                 + P("M14 20 l8 6 M86 20 l-8 6", "none").replace('fill="none"',
                     f'fill="none" stroke="{RED}" stroke-width="3.5" '
                     'stroke-linecap="round"'))
W["голодный"] = (shadow(rx=26) + _face(cx=38, cy=44, r=22) + _eyes(cx=38, cy=42, dx=8)
                 + P("M30 56 a8 6 0 0 0 16 0 Z", DARK)
                 + plate(cx=76, cy=74, w=34) + circ(76, 64, 9, TAUPE)
                 + P("M56 40 q10 6 14 16", "none").replace('fill="none"',
                     f'fill="none" stroke="{TAUPE}" stroke-width="2.5" '
                     'stroke-dasharray="3 4"'))
W["испытывающий жажду"] = (shadow(rx=26) + _face(cx=36, cy=44, r=22)
                           + _eyes(cx=36, cy=42, dx=8)
                           + P("M28 56 a8 7 0 0 0 16 0 Z", DARK)
                           + P("M36 60 q3 8 0 12 q-5 -2 0 -12 Z", BLUE)
                           + P("M66 40 h22 l-4 36 h-14 Z", BLUE)
                           + rect(64, 34, 26, 6, WHITE, 2))
W["уставший"] = (shadow(rx=26) + _face()
                 + P("M36 44 h10 M54 44 h10", "none").replace('fill="none"',
                     f'fill="none" stroke="{DARK}" stroke-width="3.5" '
                     'stroke-linecap="round"')
                 + P("M40 60 h20", "none").replace('fill="none"',
                     f'fill="none" stroke="{DARK}" stroke-width="3" stroke-linecap="round"')
                 + P("M74 30 h12 l-12 12 h12", "none").replace('fill="none"',
                     f'fill="none" stroke="{STONE}" stroke-width="3" '
                     'stroke-linejoin="round"'))
W["довольный"] = (shadow(rx=26) + _face()
                  + P("M36 42 h10 M54 42 h10", "none").replace('fill="none"',
                      f'fill="none" stroke="{DARK}" stroke-width="3.5" '
                      'stroke-linecap="round"')
                  + P("M38 56 q12 10 24 0", "none").replace('fill="none"',
                      f'fill="none" stroke="{DARK}" stroke-width="3.5" '
                      'stroke-linecap="round"'))
W["спокойный"] = (shadow(rx=26) + _face()
                  + P("M36 44 q5 4 10 0 M54 44 q5 4 10 0", "none").replace(
                      'fill="none"', f'fill="none" stroke="{DARK}" stroke-width="3" '
                      'stroke-linecap="round"')
                  + P("M40 58 h20", "none").replace('fill="none"',
                      f'fill="none" stroke="{DARK}" stroke-width="3" '
                      'stroke-linecap="round"')
                  + "".join(P(f"M{16 + i*2} {66 + i*6} q10 -5 20 0 t20 0 t20 0", "none")
                            .replace('fill="none"', f'fill="none" stroke="{BLUE}" '
                                     'stroke-width="2.5" opacity=".6"') for i in range(2)))

# ---------------------------------------------------------- приветствия
def _hand_wave(cx=50, base=84, k=1.0):
    return (P(f"M{cx-16*k} {base} V{base-26*k} a{5*k} {5*k} 0 0 1 {10*k} 0 "
              f"v-{10*k} a{5*k} {5*k} 0 0 1 {10*k} 0 v{4*k} "
              f"a{5*k} {5*k} 0 0 1 {10*k} 0 v{32*k} Z", SKIN)
            + P(f"M{cx-16*k} {base-18*k} q-{10*k} -{4*k} -{12*k} {4*k} "
                f"q-{2*k} {8*k} {8*k} {10*k}", "none").replace(
                'fill="none"', f'fill="none" stroke="{SKIN}" stroke-width="{9*k}" '
                'stroke-linecap="round"'))

W["здравствуй / мир"] = (shadow(rx=22) + _hand_wave(52, 82, 1.05)
                         + P("M22 24 l6 6 M78 24 l-6 6 M50 12 v8", "none").replace(
                             'fill="none"', f'fill="none" stroke="{OCHRE}" '
                             'stroke-width="3.5" stroke-linecap="round"'))
W["доброе утро"] = (rect(4, 58, 92, 20, SAND) + circ(50, 58, 22, OCHRE)
                    + "".join(P(f"M{50 + 28 * __import__('math').cos(a):.1f} "
                                f"{58 + 28 * __import__('math').sin(a):.1f} "
                                f"L{50 + 36 * __import__('math').cos(a):.1f} "
                                f"{58 + 36 * __import__('math').sin(a):.1f} Z", "none")
                              .replace('fill="none"', f'fill="none" stroke="{OCHRE}" '
                                       'stroke-width="4" stroke-linecap="round"')
                              for a in (3.53, 3.93, 4.32, 4.71, 5.10, 5.50, 5.89))
                    + rect(4, 58, 92, 4, SAND2))
W["добрый вечер"] = (rect(4, 20, 92, 40, "#8A5F72", 4) + rect(4, 58, 92, 20, TAUPE)
                     + circ(30, 58, 18, TERRA)
                     + rect(60, 40, 12, 18, DARK) + dome(66, 40, 6, DARK)
                     + rect(76, 46, 10, 12, DARK))
W["спокойной ночи"] = (rect(4, 18, 92, 60, "#2A4A72", 5)
                       + P("M66 26 a16 16 0 1 0 12 26 a19 19 0 0 1-12-26 Z", CREAM)
                       + circ(28, 32, 2, CREAM) + circ(42, 26, 1.6, CREAM)
                       + circ(24, 52, 1.6, CREAM) + circ(50, 44, 2, CREAM)
                       + rect(4, 66, 92, 12, "#1C3E68"))
W["спасибо"] = (shadow(rx=24) + P("M32 78 V52 q0 -6 6 -6 h24 q6 0 6 6 v26 Z", SKIN)
                + P("M32 60 q-12 -4 -14 4 q-2 8 8 10", "none").replace('fill="none"',
                    f'fill="none" stroke="{SKIN}" stroke-width="9" stroke-linecap="round"')
                + P("M50 40 C44 32 32 34 32 44 C32 54 50 62 50 62 C50 62 68 54 68 44 "
                    "C68 34 56 32 50 40 Z", RED))
W["пожалуйста"] = (shadow(rx=28)
                   + P("M14 74 V56 q0 -8 8 -8 q8 0 8 8 v-4 q0 -8 8 -8 q8 0 8 8 v22 Z", SKIN)
                   + P("M86 74 V56 q0 -8 -8 -8 q-8 0 -8 8 v-4 q0 -8 -8 -8 q-8 0 -8 8 v22 Z",
                       SAND2)
                   + P("M14 74 h72 a10 8 0 0 1 -10 8 H24 a10 8 0 0 1 -10 -8 Z", SKIN)
                   + circ(50, 32, 11, OCHRE)
                   + P("M50 44 v6", "none").replace('fill="none"',
                       f'fill="none" stroke="{OCHRE}" stroke-width="3"'))
W["извини"] = (shadow(rx=26) + _face(cy=44, r=24)
               + P("M38 40 q5 4 9 0 M53 40 q5 4 9 0", "none").replace('fill="none"',
                   f'fill="none" stroke="{DARK}" stroke-width="3" stroke-linecap="round"')
               + P("M40 58 q10 -6 20 0", "none").replace('fill="none"',
                   f'fill="none" stroke="{DARK}" stroke-width="3" stroke-linecap="round"')
               + P("M74 34 q10 6 6 16", "none").replace('fill="none"',
                   f'fill="none" stroke="{SKIN}" stroke-width="9" stroke-linecap="round"'))
W["до свидания"] = (shadow(rx=24) + _hand_wave(38, 82, 0.9)
                    + P("M62 30 h26 M78 20 l10 10 l-10 10", "none").replace(
                        'fill="none"', f'fill="none" stroke="{TAUPE}" stroke-width="4" '
                        'stroke-linecap="round" stroke-linejoin="round"'))
W["очень приятно"] = (shadow(rx=28)
                      + P("M6 44 h24 l14 8 l-6 12 l-14 -6 H6 Z", SKIN)
                      + P("M94 44 H70 l-14 8 l6 12 l14 -6 h18 Z", SAND2)
                      + P("M36 48 q14 -6 28 0 q4 8 -2 14 q-12 6 -24 0 q-6 -6 -2 -14 Z",
                          SKIN)
                      + "".join(P(f"M{x} {y-5} Q{x} {y} {x+4} {y} Q{x} {y} {x} {y+5} "
                                  f"Q{x} {y} {x-4} {y} Q{x} {y} {x} {y-5} Z", OCHRE)
                                for x, y in ((30, 26), (50, 20), (70, 28))))
W["да"] = (shadow(rx=24) + circ(50, 50, 30, OLIVE)
           + P("M34 52 l12 14 l22 -28", "none").replace('fill="none"',
               f'fill="none" stroke="{WHITE}" stroke-width="7" stroke-linecap="round" '
               'stroke-linejoin="round"'))
W["нет (отрицание)"] = (shadow(rx=24) + circ(50, 50, 30, RED)
                        + P("M38 38 l24 24 M62 38 l-24 24", "none").replace('fill="none"',
                            f'fill="none" stroke="{WHITE}" stroke-width="7" '
                            'stroke-linecap="round"'))
W["может быть"] = (shadow(rx=24) + circ(50, 50, 30, OCHRE)
                   + P("M40 40 q0 -10 10 -10 q10 0 10 10 q0 8 -10 10 v6", "none").replace(
                       'fill="none"', f'fill="none" stroke="{WHITE}" stroke-width="6" '
                       'stroke-linecap="round"')
                   + circ(50, 66, 4, WHITE))
