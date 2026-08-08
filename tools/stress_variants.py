# -*- coding: utf-8 -*-
"""
Какую разметку ударения Azure понимает.

Контрольный образец («zuzuzu») показал, что тег <phoneme> для иврита
читается. Значит ударение уезжает из-за самой записи: где ставить знак ˈ
относительно границ слогов — вопрос, на который документация отвечает
неоднозначно, а модели ведут себя по-разному.

Скрипт озвучивает ОДНО слово несколькими способами записи, включая два
контрольных с заведомо неправильным ударением. По ним сразу видно,
слушает ли синтезатор позицию знака вообще:

    python3 tools/stress_variants.py

Потом в боте /variants.
"""

import json
import os
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import audio  # noqa: E402
from generate_audio import missing_key  # noqa: E402
from stress_test import synth_ssml  # noqa: E402
from translit import to_ktiv_male  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

VARIANTS_DIR = os.path.join(audio.AUDIO_DIR, "variants")

# תַּפּוּחַ — «тапУах», ударение на втором слоге из трёх.
WORD = "תַּפּוּחַ"
CORRECT = "та-ПУ-ах"

# (метка, транскрипция, пояснение)
ENCODINGS = [
    ("a", "taˈpu.aχ",   "как сейчас: точки между слогами, ˈ вместо точки"),
    ("b", "taˈpuaχ",    "без точек, только знак ударения"),
    ("c", "ta.ˈpu.aχ",  "точки везде, ˈ дополнительно"),
    ("d", "ta.pu.ˈaχ",  "КОНТРОЛЬ: ударение на последний слог"),
    ("e", "ˈta.pu.aχ",  "КОНТРОЛЬ: ударение на первый слог"),
]


def main():
    problem = missing_key()
    if problem:
        print(problem)
        return 1

    if os.path.isdir(VARIANTS_DIR):
        for f in os.listdir(VARIANTS_DIR):
            os.remove(os.path.join(VARIANTS_DIR, f))
    os.makedirs(VARIANTS_DIR, exist_ok=True)

    plain = to_ktiv_male(WORD)
    manifest = {}
    made = failed = 0

    print(f"Слово: {WORD} (должно звучать «{CORRECT}»)\n")
    for tag, ipa, note in ENCODINGS:
        name = f"{tag}.ogg"
        caption = f"{tag.upper()}) {ipa}\n{note}"
        try:
            with open(os.path.join(VARIANTS_DIR, name), "wb") as f:
                f.write(synth_ssml(
                    f"<phoneme alphabet='ipa' ph='{escape(ipa)}'>{escape(plain)}</phoneme>"
                ))
            manifest[name] = caption
            made += 1
            print(f"  ✓ {tag}) {ipa} — {note}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {tag}) {ipa}: {str(e)[:100]}")

    if manifest:
        with open(os.path.join(VARIANTS_DIR, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\nГотово: {made}, ошибок {failed}.")
    print("Отправь боту /variants и скажи, в каком варианте слышно «та-ПУ-ах».")
    print("Если D и E звучат по-разному — позиция знака учитывается,")
    print("и тогда правильным окажется один из A, B, C.")
    return 0 if made else 1


if __name__ == "__main__":
    sys.exit(main())
