#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Прогон сценки с настоящей моделью — посмотреть, держит ли она роль и
честно ли отмечает задачи.

Реплики ученика заданы заранее (по одной на задачу плюс одна по-русски —
она НЕ должна засчитаться). Печатается, что ответил собеседник и какие
задачи он засчитал.

    python3 tools/scene_try.py            # макколет
    python3 tools/scene_try.py cafe
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
sys.path.insert(0, str(HERE.parent))

import dialog  # noqa: E402
import scenes  # noqa: E402

SCRIPTS = {
    "makolet": ["хочу хлеб", "שלום, אני רוצה לחם וחלב", "כמה זה עולה?",
                "אני משלם בכרטיס"],
    "cafe": ["кофе пожалуйста", "אפשר קפה?", "ועוגה, בבקשה",
             "אפשר חשבון?"],
}


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "makolet"
    scene = scenes.BY_KEY[key]
    if not dialog.available():
        print(dialog.why_unavailable())
        return 1
    print(f"=== {scenes.title(scene)} ({dialog.provider()}) ===")
    for i, g in enumerate(scene["goals"]):
        print(f"  задача {i + 1}: {g['ru']}")
    history = []
    res = dialog.reply([], scenes.START, scene=scene)
    history.append(("bot", res["he"]))
    print(f"\n  собеседник: {res['he']}\n              {res['ru']}")
    done = set()
    for said in SCRIPTS.get(key, SCRIPTS["makolet"]):
        res = dialog.reply(history, said, scene=scene)
        history += [("user", said), ("bot", res["he"])]
        done |= set(res["goals_done"])
        print(f"\n  > {said}")
        print(f"  собеседник: {res['he']}\n              {res['ru']}")
        if res["hint"]:
            print(f"  подсказка: {res['hint']}")
        print(f"  засчитано этой репликой: {[g + 1 for g in res['goals_done']] or '—'}")
    print(f"\nВсего сделано: {len(done)} из {len(scene['goals'])}. "
          "Реплика по-русски засчитываться не должна.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
