#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Что видит человек в разговоре — по сообщениям, а не по функциям.

Договорённость (как в Chatty):

1. Голосовое → сразу строка со сказанным, без «Вы сказали».
2. Когда модель ответит, ЭТА ЖЕ строка правится: ошибки отмечены прямо
   в словах. Верно сказано — галочка.
3. Ответ собеседника — голосом. Текст только по кнопке «Текст» под
   голосовым, перевод — по кнопке «Перевод» уже под текстом.
4. Транскрипции кириллицей нет нигде.

Сеть подменена: Telegram, распознавание и модель не вызываются. Всё,
что бот отправил бы, складывается в список и проверяется.
"""
import json
import os
import sys
import tempfile

os.environ.setdefault("BOT_DB_PATH", tempfile.mktemp(suffix=".db"))
os.environ.setdefault("TELEGRAM_TOKEN", "1:TEST")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import audio  # noqa: E402
import bot  # noqa: E402
import db  # noqa: E402
import dialog  # noqa: E402

db.init_db()
fail = 0


def ok(cond, msg):
    global fail
    print(("✓ " if cond else "✗ ") + msg)
    fail += 0 if cond else 1


sent = []                       # (метод, полезная нагрузка)


class Resp:
    def __init__(self, n):
        self.n = n

    def json(self):
        return {"ok": True, "result": {"message_id": self.n,
                                       "voice": {"file_id": "F"}}}


def fake_post(url, json=None, data=None, files=None, timeout=None):
    method = url.rsplit("/", 1)[-1]
    body = dict(json or data or {})
    sent.append((method, body))
    return Resp(len(sent))


bot.SESSION.post = fake_post
audio.SESSION.post = fake_post
dialog.available = lambda: True
audio.can_speak = lambda: True
audio.ensure_audio = lambda text, voice=None: __file__   # любой файл
db.voice_enabled = lambda chat_id: True
bot._transcribe = lambda chat_id, voice, lang="ru", with_conf=False: HEARD

CHAT = 555
HE = "נָעִים מְאוֹד, דָּנִיֵּאל!"
RU = "Очень приятно, Даниэль!"


def reply_with(fixed, hint=""):
    def fake(history, said, **kw):
        return {"he": HE, "he_model": HE, "niqqud_by": "model", "ru": RU,
                "no_ru": False, "fixed": fixed,
                "marked": dialog.mark_fix(said, fixed), "hint": hint,
                "ok": True, "usage": (1, 1), "raw": ""}
    dialog.reply = fake


_client = bot.app.test_client()
_uid = [1000]


def cb(data, mid):
    """Нажатие кнопки — через настоящий вебхук, как это делает Telegram."""
    _uid[0] += 1
    _client.post(f"/webhook/{bot.TELEGRAM_TOKEN}", json={
        "update_id": _uid[0],
        "callback_query": {"id": "q", "data": data,
                           "from": {"id": CHAT, "language_code": "ru"},
                           "message": {"message_id": mid,
                                       "chat": {"id": CHAT}}}})


def texts():
    return [b.get("text", "") for m, b in sent]


def cyrillic_reading(text):
    # Транскрипция у нас печаталась в <code>…</code>.
    return "<code>" in text


# --- 1. верно сказано --------------------------------------------------
HEARD = "אני דניאל"
reply_with("")
sent.clear()
bot.handle_voice(CHAT, {"file_id": "x", "duration": 2})
methods = [m for m, _ in sent]
ok(methods[0] == "sendMessage" and sent[0][1]["text"].startswith("🗣 "),
   f"сказанное напечатано сразу: {sent[0][1].get('text')!r}")
ok("Вы сказали" not in sent[0][1]["text"], "без подписи «Вы сказали»")
edits = [b for m, b in sent if m == "editMessageText"]
ok(edits and edits[0]["message_id"] == 1,
   "та же строка потом правится, а не шлётся новая")
ok(edits and edits[0]["text"].endswith("✓"), f"верно — галочка: {edits and edits[0]['text']!r}")
voice = [b for m, b in sent if m == "sendVoice"]
ok(bool(voice), "ответ ушёл голосом")
kb = json.loads(voice[0]["reply_markup"]) if voice else {}
first = kb.get("inline_keyboard", [[{}]])[0][0]
ok(first.get("callback_data", "").startswith("talk_text|"),
   f"под голосовым кнопка «Текст»: {first.get('text')}")
ok(not any(HE in x for x in texts()), "иврит ответа сам не печатается")
ok(not any(RU in x for x in texts()), "перевод сам не печатается")
ok(not any(cyrillic_reading(x) for x in texts()), "транскрипции нет")

# --- 2. «Текст», потом «Перевод» -----------------------------------------
sent.clear()
ref = first["callback_data"].split("|")[1]
cb(f"talk_text|{ref}", 99)
msg = [b for m, b in sent if m == "sendMessage"]
ok(msg and HE in msg[0]["text"] and RU not in msg[0]["text"],
   "«Текст» показывает иврит без перевода")
ok(msg and not cyrillic_reading(msg[0]["text"]), "и без транскрипции")
tr_btn = (msg[0].get("reply_markup") or {}).get("inline_keyboard", [[{}]])[0][0] if msg else {}
ok(tr_btn.get("callback_data") == f"talk_tr|{ref}", "под текстом кнопка «Перевод»")
sent.clear()
cb(f"talk_tr|{ref}", 100)
ed = [b for m, b in sent if m == "editMessageText"]
ok(ed and RU in ed[0]["text"] and ed[0]["message_id"] == 100,
   "«Перевод» дописан в то же сообщение")

# --- 3. ошибка — правка внутри сказанного ---------------------------------
HEARD = "אני גר את תל אביב"
reply_with("אֲנִי גָּר בְּתֵל אָבִיב")
sent.clear()
bot.handle_voice(CHAT, {"file_id": "x", "duration": 2})
edits = [b for m, b in sent if m == "editMessageText"]
t = edits[0]["text"] if edits else ""
ok("<s>" in t and "<b>" in t, f"ошибка отмечена в самой фразе: {t!r}")
ok(not t.endswith("✓"), "при ошибке галочки нет")
ok(sum(1 for m, _ in sent if m == "sendMessage") == 1,
   "отдельного сообщения с поправкой нет — только строка сказанного")

# --- 4. старая кнопка работает на свою реплику -----------------------------
sent.clear()
cb(f"talk_text|{ref}", 101)
ok(any(HE in x for x in texts()), "«Текст» под старым голосовым — своя реплика")

# --- 5. сценка ----------------------------------------------------------------
import scenes  # noqa: E402
calls = []


def scene_reply(goals_done):
    """Подставной собеседник сценки: какие задачи засчитать этой репликой.

    Настоящий dialog._goals тоже прогоняем — в нём правило «по-русски не
    засчитывается», и проверять его в обход было бы нечестно."""
    def fake(history, said, scene=None, **kw):
        calls.append((said, scene and scene["key"], len(history)))
        return {"he": HE, "he_model": HE, "niqqud_by": "model", "ru": RU,
                "no_ru": False, "fixed": "", "marked": "", "hint": "",
                "goals_done": real_goals([g + 1 for g in goals_done], said, scene),
                "ok": True, "usage": (1, 1), "raw": ""}
    dialog.reply = fake


real_goals = dialog._goals
db.dialog_add(CHAT, "user", "שלום")          # хвост свободного разговора
sent.clear(); calls.clear()
scene_reply([])
cb("scenes", 200)
ok(any("scene|makolet" in json.dumps(b.get("reply_markup") or {}) for m, b in sent),
   "«Сценки» — список с макколетом")
sent.clear()
cb("scene|makolet", 201)
intro = next((x for x in texts() if "🎭" in x), "")
ok("В макколете" in intro and "хлеб" in intro, "перед сценой — роль и задачи")
ok(calls and calls[-1][1] == "makolet" and calls[-1][2] == 0,
   "собеседник начинает сам, с чистой историей")
ok(any(m == "sendVoice" for m, _ in sent), "первая реплика — голосом")
ok(db.dialog_today(CHAT) >= 0 and not any(r == "user" and x == scenes.START
   for r, x in db.dialog_history(CHAT)), "служебный «ход» не записан как реплика человека")

kb = json.dumps([json.loads(b["reply_markup"]) for m, b in sent if m == "sendVoice"][-1])
ok("scene_goals" in kb and "talk_voice" not in kb,
   "в сценке кнопки «Задачи» и «Выйти», смены собеседника нет")

# по-русски — не засчитывается, даже если модель считает иначе
scene_reply([0])
sent.clear()
bot.handle_talk(CHAT, "хочу хлеб и молоко")
ok(db.talk_scene(CHAT)["done"] == [], "сказано по-русски — задача не засчитана")

HEARD = "אני רוצה לחם וחלב"
sent.clear()
bot.handle_voice(CHAT, {"file_id": "x", "duration": 2})
ed = [b for m, b in sent if m == "editMessageText"]
ok(ed and "✅" in ed[0]["text"] and "хлеб" in ed[0]["text"],
   "задача отмечена прямо под сказанным")
ok(db.talk_scene(CHAT)["done"] == [0], "и записана в состояние сцены")

scene_reply([1, 2])
HEARD = "כמה זה עולה? אני משלם בכרטיס"
sent.clear()
bot.handle_voice(CHAT, {"file_id": "x", "duration": 2})
ok(db.talk_scene(CHAT) is None, "все задачи сделаны — сцена закрыта")
ok(any("сыграна" in x for x in texts()), "поздравление с очками")
ok(any("scenes" in json.dumps(b.get("reply_markup") or {}) for m, b in sent
       if "сыграна" in b.get("text", "")), "и предложение другой сценки")

# выход посреди сцены
cb("scene|cafe", 202)
cb("scene_exit", 203)
ok(db.talk_scene(CHAT) is None, "«Выйти из сценки» — обратно в свободный разговор")

print()
if fail:
    print(f"Сбоев: {fail}")
    sys.exit(1)
print("Разговор показывается так, как договорились.")
