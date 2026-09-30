# -*- coding: utf-8 -*-
"""Проверка новых режимов через настоящий API, с подписанным initData.

Сюда добавляется каждый новый режим: множественное число, сокращения.
Смысл в том, чтобы пройти весь путь — меню, раунд, ответ, разбор — так,
как его проходит приложение, а не по отдельным функциям. Я не вижу
отрисованную страницу, и это ближайшее к ней, что у меня есть.
"""
import hashlib, hmac, json, os, tempfile, time, urllib.parse, sys

TOKEN = "123:TEST"
os.environ["TELEGRAM_TOKEN"] = TOKEN
os.environ["BOT_DB_PATH"] = tempfile.mkstemp(suffix=".db")[1]
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import webapp, quiz, db, grammar

def init_data(uid=777, lang="ru"):
    fields = {"auth_date": str(int(time.time())),
              "user": json.dumps({"id": uid, "first_name": "Т",
                                  "language_code": lang}, ensure_ascii=False)}
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    check = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(fields)

db.init_db()
from flask import Flask
app = Flask(__name__)
app.register_blueprint(webapp.api)
c = app.test_client()

def post(path, **body):
    body["init_data"] = init_data(lang=body.pop("lang", "ru"))
    r = c.post(path, json=body)
    assert r.status_code == 200, (path, r.status_code, r.data[:200])
    return r.get_json()

fail = 0
def ok(cond, msg):
    global fail
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond: fail += 1

print("меню")
m = post("/api/menu")
item = next((i for i in m["grammar"] if i["key"] == "plural"), None)
ok(item is not None, "число есть в разделе «Грамматика»")
ok(item and item.get("mode") == "plural", f"режим приезжает отдельным полем: {item and item.get('mode')}")
ok(item and item["count"] == 119, f"карточек: {item and item.get('count')}")

print("инструкция «Как учиться»")
ok(m.get("guide_seen") is False, f"новичку инструкция не показана: {m.get('guide_seen')}")
ok(post("/api/guide_seen").get("ok") is True, "отметка принята")
ok(post("/api/menu").get("guide_seen") is True, "после отметки сама больше не открывается")

print("«Заговорить»: проверка голоса")
import base64, speech, dialog as _dialog, hebrew_rules
say_id = phrases_first = next(iter(__import__("phrases").PHRASES.items()))
_ph_id = __import__("phrases").card_id(say_id[0], 0)
_ph = __import__("phrases").by_id(_ph_id)
_target = hebrew_rules.strip_niqqud(__import__("phrases").spoken(_ph, False, lang="ru"))
WAV = base64.b64encode(b"RIFF....WAVEfake").decode()
def say_check(**kw):
    kw["init_data"] = init_data()
    return c.post("/api/say_check", json=kw)
speech.available = lambda: False
ok(say_check(id=_ph_id, audio=WAV).status_code == 409, "нет распознавания — 409, приложение останется на самопроверке")
speech.available = lambda: True
_calls = []
_dialog.available = lambda: True
def _judge(ru, target, heard, lang="ru"):
    _calls.append(heard); return {"ok": True, "comment": ""}
_dialog.judge = _judge
speech.recognize = lambda data, lang="he-IL", content_type=None: (_target, 0.9)
r = say_check(id=_ph_id, audio=WAV).get_json()
ok(r["verdict"] == "match" and r["ok"], f"сказано как в образце — верно: {r['verdict']}")
ok(not _calls, "при совпадении модель не зовём (не платим)")
speech.recognize = lambda data, lang="he-IL", content_type=None: ("משהו אחר לגמרי", 0.9)
r = say_check(id=_ph_id, audio=WAV).get_json()
ok(_calls and r["verdict"] == "meaning" and r["ok"] and r["by"] == "model",
   f"слова другие — решает модель: {r['verdict']}")
_dialog.judge = lambda *a, **k: None
r = say_check(id=_ph_id, audio=WAV).get_json()
ok(r["verdict"] == "different" and not r["ok"], f"модели нет — вердикт по словам: {r['verdict']}")
speech.recognize = lambda data, lang="he-IL", content_type=None: ("", 0.0)
r = say_check(id=_ph_id, audio=WAV).get_json()
ok(r["verdict"] == "silence", "тишина — просим сказать ещё раз")
ok(say_check(id=_ph_id, audio="не base64!").status_code == 400, "мусор вместо звука — 400")
ok(post("/api/menu").get("speech_check") is True, "меню говорит приложению, что проверка есть")

print("раунд")
r = post("/api/round", mode="plural", cat="", format="choice")
qs = r["questions"]
ok(bool(qs), f"раунд собрался: {len(qs)} вопросов, подпись «{r['label']}»")
ok(all("множественное" in q["ru"] for q in qs), f"вопрос: {qs[0]['ru']}")
ok(all(q["mode"] == "plural" for q in qs), "все вопросы режима plural")
bad_opts = [q["ru"] for q in qs if len(set(q["options"])) != len(q["options"])]
ok(not bad_opts, f"повторов в вариантах нет (проверено {len(qs)})")
exp = {q["id"]: quiz.ANSWERS["plural"][q["id"]].answer("ru") for q in qs}
ok(all(exp[q["id"]] in q["options"] for q in qs), "верный ответ всегда среди вариантов")
# знакомство: слово в первый раз показывают, а не сразу спрашивают
ok(len(r["intro"]) == len(qs), f"экранов знакомства {len(r['intro'])} на {len(qs)} вопросов")
ok(all(c.get("main") or c.get("he") for c in r["intro"]), "у знакомства есть слово")

print("ответ и разбор")
q0 = qs[0]
a = post("/api/answer", mode="plural", id=q0["id"], answer=exp[q0["id"]], format="choice")
ok(a["correct"] is True, f"верный ответ принят, приговор {a['verdict']}")
ok(a["page"] == "plural", f"ведёт на страницу: {a['page']}")
ok(bool(a["why"]), f"разбор: {(a['why'] or [''])[0][:66]}")
ok(bool(a["reading"]), f"чтение: {a['reading']}")
wrong = next(o for o in q0["options"] if o != exp[q0["id"]])
b = post("/api/answer", mode="plural", id=q0["id"], answer=wrong, format="choice")
ok(b["correct"] is False and b["expected"] == exp[q0["id"]],
   f"ошибка распознана, ждали {b['expected']}")
ok(bool(b["why"]), "при ошибке разбор тоже приходит")

print("страница справочника")
g = post("/api/grammar", id="plural")
ok(g.get("id") == "plural", "страница отдаётся")
ok(len(g.get("smichut", [])) == 16, f"примеров {len(g.get('smichut', []))}")
ok(g.get("train", {}).get("mode") == "plural", f"кнопка ведёт в {g.get('train')}")
ok(all(x["whole"] and x["base"] and x["gloss"] for x in g["smichut"]),
   "ни одной пустой строки в таблице")
ok(grammar_train_ok := all(grammar.page(p_)["train"]["cat"].startswith("binyan:")
   for p_ in grammar.PAGE_OF_BINYAN.values()), "у биньянов кнопка не сломалась")

print("английский")
ge = post("/api/grammar", id="plural", lang="en")
ok(ge["title"] == "One and many", f"заголовок: {ge['title']}")
me = post("/api/menu", lang="en")
ie = next(i for i in me["grammar"] if i["key"] == "plural")
ok(ie["name"] == "one and many", f"подпись: {ie['name']}")
re_ = post("/api/round", mode="plural", cat="", format="choice", lang="en")
ok("plural" in re_["questions"][0]["ru"], f"вопрос: {re_['questions'][0]['ru']}")

print("сокращения")
m2 = post("/api/menu")
ab = next((i for i in m2["grammar"] if i["key"] == "abbrev"), None)
ok(ab is not None and ab.get("mode") == "abbrev", f"раздел есть: {ab and ab.get('name')}")
ra = post("/api/round", mode="abbrev", cat="", format="choice")
qa = ra["questions"]
ok(bool(qa), f"раунд собрался: {len(qa)}")
ok(all("что это" in q["ru"] for q in qa), f"вопрос: {qa[0]['ru']}")
expa = {q["id"]: quiz.ANSWERS["abbrev"][q["id"]].answer("ru") for q in qa}
aa = post("/api/answer", mode="abbrev", id=qa[0]["id"], answer=expa[qa[0]["id"]], format="choice")
ok(aa["correct"] is True, "ответ принят")
ok(aa["reading"] == "", f"транскрипции нет: {aa['reading']!r}")
ok(aa["audio"] is None, f"озвучки нет: {aa['audio']!r}")
ok(bool(aa["why"]), f"разбор: {(aa['why'] or [''])[0][:60]}")

print("собери фразу")
m3 = post("/api/menu")
sy = next((i for i in m3["grammar"] if i["key"] == "syntax"), None)
ok(sy is not None and sy.get("mode") == "syntax", f"раздел есть: {sy and sy.get('name')}")
rs = post("/api/round", mode="syntax", cat="", format="choice")
qs = rs["questions"]
ok(bool(qs), f"раунд собрался: {len(qs)}")
ok(all(len(q["options"]) == 3 for q in qs),
   f"по три варианта: {sorted({len(q['options']) for q in qs})}")
# Главное в этом режиме: варианты — искажения ТОЙ ЖЕ фразы, а не чужие
# карточки. Проверяем по данным, а не на глаз.
import syntax as _syn
card0 = quiz.ANSWERS["syntax"][qs[0]["id"]]
ok(set(qs[0]["options"]) == {card0.he} | set(card0.wrong),
   "варианты — искажения этой же фразы")
# И ошибка должна называть правило, а не просто «неверно».
bad = next(o for o in qs[0]["options"] if o != card0.he)
asn = post("/api/answer", mode="syntax", id=qs[0]["id"], answer=bad,
           format="choice")
ok(asn["correct"] is False, "неверный ответ не принят")
rule = _syn.rule_of(card0.he, bad)
ok(bool(asn["why"]) and asn["why"][0] == rule,
   f"разбор называет нарушенное правило: {(asn['why'] or [''])[0][:60]}")

print("аудирование")
# Озвучки в песочнице нет, а пул аудирования зависит от файлов. Подменяем
# проверку наличия — иначе проверить путь нечем, а он самый новый.
import audio as _audio
_audio.has_audio = lambda text, slow=False: True
rl = post("/api/round", mode="listen", cat="", format="choice")
ql = rl["questions"]
ok(bool(ql), f"раунд собрался: {len(ql)}")
ok(all(q["ru"] == "" for q in ql), "текста вопроса нет — задание это звук")
ok(all(q.get("voice") for q in ql), f"ключ озвучки пришёл: {ql[0].get('voice')}")
card = quiz.ANSWERS["vocab"][ql[0]["id"]]
ok(ql[0]["voice"] == _audio.audio_key(card.he), "ключ считается от ивритского слова")
ru = card.prompt("ru")
opts = ql[0]["options"]
ok(ru in opts, f"верный ответ среди вариантов: {ru}")
ok(all(not any('\u0590' <= c <= '\u05ff' for c in o) for o in opts),
   f"варианты по-русски, иврита в них нет: {opts}")
al = post("/api/answer", mode="listen", id=ql[0]["id"], answer=ru, format="choice")
ok(al["correct"] is True, "ответ переводом принят")
ok(al.get("word") == card.he, f"после ответа показываем слово: {al.get('word')}")
ok(al["reading"] and any('\u0430' <= c <= '\u044f' for c in al["reading"]),
   f"чтение от иврита, а не от перевода: {al['reading']}")
wrong = next(o for o in opts if o != ru)
bl = post("/api/answer", mode="listen", id=ql[0]["id"], answer=wrong, format="choice")
ok(bl["correct"] is False and bl["expected"] == ru, f"ошибка распознана, ждали {bl['expected']}")

print("спринт")
sp = post("/api/sprint")
ok(sp["seconds"] == 60, f"минута: {sp['seconds']}")
ok(len(sp["questions"]) == 40, f"вопросов вперёд: {len(sp['questions'])}")
ok(all(q["mode"] == "sprint" for q in sp["questions"]), "режим свой, не vocab")
ok(all("correct" not in q and "answer" not in q for q in sp["questions"]),
   "верного ответа в выдаче нет")
ok(len({q["id"] for q in sp["questions"]}) == 40, "вопросы не повторяются")
ok(sp["best"] == 0, f"рекорда ещё нет: {sp['best']}")
# отвечаем на три верно, на один неверно
right = 0
for q in sp["questions"][:4]:
    card = quiz.ANSWERS["vocab"][q["id"]]
    good = card.answer("ru")
    give = good if right < 3 else next(o for o in q["options"] if o != good)
    r = post("/api/answer", mode="sprint", id=q["id"], answer=give, format="choice")
    ok(r["correct"] == (give == good), f"судит сервер: {give} -> {r['correct']}")
    if r["correct"]: right += 1
ok(right == 3, f"верных {right}")
done = post("/api/sprint_done", score=right)
ok(done["record"] is True and done["best"] == 3, f"рекорд записан: {done}")
again = post("/api/sprint_done", score=2)
ok(again["record"] is False and again["best"] == 3, f"хуже — не рекорд: {again}")
big = post("/api/sprint_done", score=999)
ok(big["score"] == 40, f"счёт больше выдачи обрезан: {big['score']}")
# ответы спринта не должны трогать расписание словаря
import db as _db
st = _db.card_history(777, sp["questions"][0]["id"], "vocab")
ok(st is None, f"расписание словаря не тронуто: {st}")
st2 = _db.card_history(777, sp["questions"][0]["id"], "sprint")
ok(st2 is not None, f"свой режим пишется: {st2}")

print("прогресс пишется под устойчивым ключом")
ok(q0["id"].startswith("plural:"), f"ключ: {q0['id']}")
import db as _db
h = _db.card_history(777, q0["id"], "plural")
ok(h is not None, f"ответ записан в базу: {h}")

print("\nсбоев:", fail)
sys.exit(1 if fail else 0)
