#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сценки: что делает код поверх модели.

Всё здесь найдено на первом живом прогоне (tools/scene_try.py):

1. На последней реплике модель прислала goals_done = [1, 2, 3] вместо
   [3] — все задачи сразу. Теперь ей называются уже выполненные, а код
   отбрасывает повторы сам.
2. На верную ивритскую реплику «אני משלם בכרטיס» пришла подсказка
   «Как сказать „я заплачу картой“?» — человек решил бы, что ошибся.
   Подсказка теперь только на русскую реплику.
3. На русскую реплику продавец сказал «אני רוצה לחם» — фразу
   покупателя. Это правило подсказки; код его проверить не может, но
   текст подсказки проверяем.
4. Русская реплика задачу не засчитывает, что бы ни сказала модель.

Модель подменена: сеть не нужна, ключ не нужен.
"""
import os
import sys
import tempfile

os.environ.setdefault("BOT_DB_PATH", tempfile.mktemp(suffix=".db"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import dialog  # noqa: E402
import nakdan  # noqa: E402
import scenes  # noqa: E402

fail = 0


def ok(cond, msg):
    global fail
    print(("✓ " if cond else "✗ ") + msg)
    fail += 0 if cond else 1


nakdan.vocalize_trusted = lambda t: t
dialog.ANTHROPIC_KEY = "x"
dialog.OPENAI_KEY = dialog.GOOGLE_KEY = ""
os.environ.pop("DIALOG_PROVIDER", None)
seen = []


def answer_with(raw):
    def fake(system, turns):
        seen.append(system)
        return raw, (1, 1)
    dialog._ask_anthropic = fake


SC = scenes.BY_KEY["makolet"]
RAW = ('{"he": "תודה רבה!", "ru": "Спасибо!", "fixed": "", '
       '"hint": "Как сказать «я заплачу картой»?", "goals_done": [1, 2, 3]}')

# 1. повторы задач отбрасываются
answer_with(RAW)
res = dialog.reply([], "אני משלם בכרטיס", scene=SC, scene_done=[0, 1])
ok(res["goals_done"] == [2], f"засчитана только новая задача: {res['goals_done']}")
ok("Уже выполнены: 1, 2" in seen[-1], "модели названы уже выполненные задачи")

# 2. подсказка на верный иврит не показывается
ok(res["hint"] == "", f"на ивритскую реплику подсказки нет: {res['hint']!r}")

# 3. на русскую — показывается, задача не засчитывается
answer_with(RAW)
res = dialog.reply([], "заплачу картой", scene=SC, scene_done=[0, 1])
ok(res["hint"], "на русскую реплику подсказка есть")
ok(res["goals_done"] == [], "русская реплика задачу не засчитывает")

# 4. подсказка сцены говорит, что делать с русской репликой
p = scenes.prompt(SC)
ok("Никогда не произноси его фразу за него" in p and "только в поле hint" in p,
   "подсказка: по-русски — отвечать по роли, фразу ученика не говорить")
ok("Пока не выполнено ничего" in p, "в начале сцены — «пока ничего»")
ok("не говори сам того, что по задачам должен сказать" in p,
   "подсказка: не произносить за ученика его задачи (второй прогон: продавец "
   "спросил «сколько это стоит?»)")

# 5. номера вне списка отбрасываются
answer_with('{"he": "א", "ru": "а", "fixed": "", "hint": "", "goals_done": [0, 7, "x", 2]}')
res = dialog.reply([], "שלום", scene=SC)
ok(res["goals_done"] == [1], f"мусор в номерах отброшен: {res['goals_done']}")

# 6. вне сценки подсказка на русском по-прежнему работает
answer_with('{"he": "שלום", "ru": "Привет", "fixed": "", "hint": "Скажи: שלום"}')
res = dialog.reply([], "привет")
ok(res["hint"] == "Скажи: שלום" and res["goals_done"] == [],
   "свободный разговор: подсказка на русское есть, задач нет")

print()
if fail:
    print(f"Сбоев: {fail}")
    sys.exit(1)
print("Сценки: код поверх модели делает, что обещано.")
