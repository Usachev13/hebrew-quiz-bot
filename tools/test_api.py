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

print("раунд")
r = post("/api/round", mode="plural", cat="", format="choice")
qs = r["questions"]
ok(bool(qs), f"раунд собрался: {len(qs)} вопросов, подпись «{r['label']}»")
ok(all("много" in q["ru"] for q in qs), f"вопрос: {qs[0]['ru']}")
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

print("прогресс пишется под устойчивым ключом")
ok(q0["id"].startswith("plural:"), f"ключ: {q0['id']}")
import db as _db
h = _db.card_history(777, q0["id"], "plural")
ok(h is not None, f"ответ записан в базу: {h}")

print("\nсбоев:", fail)
sys.exit(1 if fail else 0)
