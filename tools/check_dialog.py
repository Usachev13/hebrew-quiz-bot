# -*- coding: utf-8 -*-
"""
Проверка разговора.

Что здесь проверяется
---------------------
Разговор — единственное место в проекте, где иврит порождает машина, а
не берётся из выверенных данных. Проверить ПРАВИЛЬНОСТЬ того, что она
скажет, нельзя ни здесь, ни вообще: это работа носителя, и реплики для
этого пишутся в базу.

Но можно проверить всё остальное, и это не мелочь:

1. Разбор ответа. Модель отвечает JSON'ом, и делает это не всегда
   аккуратно: оборачивает в ```json```, добавляет фразу перед. Упасть
   на этом нельзя — у человека посреди беседы пропадёт собеседник.
2. Отношение к сомнительным огласовкам. Если модель прислала запись,
   нарушающую формальные правила, огласовки снимаются, а транскрипция
   не показывается. Это главное обещание модуля: лучше без подсказки,
   чем с неверной.
3. Предел на сутки. Считать его надо ДО обращения к модели, иначе мы
   платим за сообщение, которое не покажем.

К модели эта проверка не ходит: ответы подменяются. Иначе она стоила бы
денег при каждом запуске и зависела бы от сети.
"""

import os
import sys
import tempfile

os.environ.setdefault("BOT_DB_PATH", tempfile.mktemp(suffix=".db"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import db  # noqa: E402
import dialog  # noqa: E402
import hebrew_rules  # noqa: E402

fails = []


def check(title, ok, detail=""):
    if ok:
        print(f"✓ {title}")
    else:
        fails.append(title)
        print(f"  СБОЙ {title}: {detail}")


# ------------------------------------------------------------- разбор
GOOD = '{"he": "שָׁלוֹם! מַה שְׁלוֹמְךָ?", "ru": "Привет! Как дела?", ' \
       '"correction": "", "hint": ""}'
SHAPES = {
    "чистый JSON": GOOD,
    "в блоке кода": "```json\n" + GOOD + "\n```",
    "с приговоркой": "Вот ответ:\n" + GOOD,
    "с переводом строки внутри": GOOD.replace(", ", ",\n  "),
}
for name, raw in SHAPES.items():
    data = dialog._parse(raw)
    check(f"разбирается: {name}",
          data.get("he", "").startswith("שָׁלוֹם"), repr(data)[:120])

# Совсем не JSON — считаем всё сказанное репликой, а не падаем.
data = dialog._parse("שָׁלוֹם")
check("не-JSON не роняет разговор", data.get("he") == "שָׁלוֹם", repr(data))
check("пустой ответ не роняет разговор",
      isinstance(dialog._parse(""), dict) and isinstance(dialog._parse(None), dict))


# ------------------------------------------------------- три провайдера
# Ответ у каждого устроен по-своему, и разбирается своим куском кода.
# Подменяем сам HTTP-вызов и проверяем, что из трёх разных форм ответа
# выходит одно и то же: текст реплики и счёт токенов. Ошибка тут
# означала бы, что разговор работает с одним провайдером и молча ломается
# при переезде на другой.
class FakeResponse:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


SHAPES_BY_PROVIDER = {
    "anthropic": (dialog._ask_anthropic, {
        "content": [{"type": "text", "text": GOOD}],
        "usage": {"input_tokens": 120, "output_tokens": 40}}),
    "openai": (dialog._ask_openai, {
        "choices": [{"message": {"content": GOOD}}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 40}}),
    "google": (dialog._ask_google, {
        "candidates": [{"content": {"parts": [{"text": GOOD}]}}],
        "usageMetadata": {"promptTokenCount": 120, "candidatesTokenCount": 40}}),
}

real_post = dialog.requests.post
for name, (fn, body) in SHAPES_BY_PROVIDER.items():
    dialog.requests.post = lambda *a, **k: FakeResponse(body)
    try:
        text, usage = fn("подсказка", [{"role": "user", "content": "שלום"}])
    finally:
        dialog.requests.post = real_post
    check(f"ответ разобран: {name}",
          dialog._parse(text).get("he", "").startswith("שָׁלוֹם")
          and usage == (120, 40), f"{text[:60]!r} {usage}")

# Пустой ответ (сработал фильтр, оборвалась выдача) не должен ронять
# разговор ни у одного из трёх.
EMPTY = {"anthropic": {"content": []},
         "openai": {"choices": [{"message": {"content": ""}}]},
         "google": {"candidates": []}}
for name, body in EMPTY.items():
    fn = SHAPES_BY_PROVIDER[name][0]
    dialog.requests.post = lambda *a, **k: FakeResponse(body)
    try:
        if name == "openai":
            text, _ = fn("п", [{"role": "user", "content": "ש"}])
        else:
            text, _ = fn("п", [{"role": "user", "content": "ש"}])
        ok = isinstance(dialog._parse(text), dict)
    except Exception as e:                                  # noqa: BLE001
        ok = False
        text = f"исключение: {e}"
    finally:
        dialog.requests.post = real_post
    check(f"пустой ответ не роняет: {name}", ok, str(text)[:60])

# Выбор провайдера — по ключу, и порядок объявлен.
saved = (dialog.ANTHROPIC_KEY, dialog.OPENAI_KEY, dialog.GOOGLE_KEY)
for keys, expected in ((("a", "", ""), "anthropic"), (("", "o", ""), "openai"),
                       (("", "", "g"), "google"), (("a", "o", "g"), "anthropic"),
                       (("", "", ""), "")):
    dialog.ANTHROPIC_KEY, dialog.OPENAI_KEY, dialog.GOOGLE_KEY = keys
    check(f"выбор провайдера {keys} -> {expected or 'ничего'}",
          dialog.provider() == expected, dialog.provider())
check("без ключей разговор недоступен", not dialog.available())

# Явный выбор сильнее наличия ключей. Это не удобство, а защита от
# настоящей ловушки: в .env уже лежал OPENAI_API_KEY от опытов с
# озвучкой, и вписанный рядом бесплатный ключ Google молча не
# срабатывал бы — бот уходил к OpenAI и получал отказ авторизации.
dialog.ANTHROPIC_KEY, dialog.OPENAI_KEY, dialog.GOOGLE_KEY = "", "старый", "новый"
os.environ["DIALOG_PROVIDER"] = "google"
check("явный выбор сильнее порядка", dialog.provider() == "google",
      dialog.provider())
os.environ["DIALOG_PROVIDER"] = "anthropic"
check("назван провайдер без ключа — разговора нет, а не подмена",
      dialog.provider() == "" and "ключа" in dialog.why_unavailable(),
      f"{dialog.provider()!r} / {dialog.why_unavailable()}")
os.environ["DIALOG_PROVIDER"] = "gemini"
check("опечатка в имени названа по имени",
      "такого не знаю" in dialog.why_unavailable(), dialog.why_unavailable())
os.environ.pop("DIALOG_PROVIDER")
check("без указания — первый по порядку", dialog.provider() == "openai")

# Адрес запроса для формата OpenAI берётся из настройки: по этому же
# протоколу говорят Groq, OpenRouter и прочие, и подключаются они сменой
# адреса, а не новым кодом. Проверяем, что адрес действительно
# подставляется, — иначе ключ Groq молча уйдёт в OpenAI и вернётся
# отказом авторизации, а причина будет неочевидна.
saved_base = dialog.OPENAI_BASE
dialog.OPENAI_BASE = "https://api.groq.com/openai/v1"
seen = {}


def _spy(url, **kw):
    seen["url"] = url
    return FakeResponse({"choices": [{"message": {"content": GOOD}}],
                         "usage": {"prompt_tokens": 1, "completion_tokens": 1}})


dialog.requests.post = _spy
try:
    dialog._ask_openai("п", [{"role": "user", "content": "ש"}])
finally:
    dialog.requests.post = real_post
    dialog.OPENAI_BASE = saved_base
check("адрес берётся из настройки",
      seen.get("url") == "https://api.groq.com/openai/v1/chat/completions",
      seen.get("url"))
dialog.ANTHROPIC_KEY, dialog.OPENAI_KEY, dialog.GOOGLE_KEY = saved


# ------------------------------------------- сомнительные огласовки
# Каф без шва — формальная ошибка, значит записи модели верить нельзя.
DIRTY = "הוֹלֵך לַבַּיִת"
clean_text, ok = hebrew_rules.sanitize(DIRTY)
check("сомнительная огласовка снимается", not ok and "ֵ" not in clean_text,
      f"{clean_text!r} ok={ok}")

# Настоящий случай из живого разговора. Модель ответила без огласовок —
# формальные правила такое пропускают, потому что ищут НЕВЕРНЫЕ
# огласовки, а здесь их нет вовсе. Наше чтение выводится ИЗ огласовок, и
# человек увидел «шлвм, нй всдр! т?».
import bot  # noqa: E402

BARE = "שלום, אני בסדר! אתה?"
bare_out, bare_ok = hebrew_rules.sanitize(BARE)
check("ответ без огласовок признан непригодным для чтения",
      not bare_ok, f"{bare_out!r} ok={bare_ok}")
check("но сам текст не испорчен", bare_out == BARE, bare_out)
check("транскрипции по неогласованному тексту нет",
      bot._reading_if_clean(BARE, bare_ok, "ru") == "",
      bot._reading_if_clean(BARE, bare_ok, "ru"))
check("частично огласованное тоже не читаем",
      not hebrew_rules.sanitize("אֲנִי גר בְּתֵל אָבִיב")[1])
check("слово из одной буквы не требует огласовки",
      hebrew_rules.is_vocalized("בְּתֵל אָבִיב"))

# Огласовок у модели больше не просим вовсе: их ставит Nakdan. Просьбу
# модель игнорировала даже с примером — так и вышло «שלום, אני בסדר», из
# которого наша транскрипция сделала «шлвм, нй всдр». Проверяем, что
# требование ушло и из подсказки: оставленное, оно сбивало бы модель на
# собственные огласовки, и в одном ответе смешались бы два источника.
check("огласовок у модели не просим",
      "ОБЯЗАТЕЛЬНЫ" not in dialog._system("m", "ru"),
      "в подсказке осталось требование огласовок")
check("сказано, что их поставит программа",
      "расставит программа" in dialog._system("m", "ru"))

GOOD_HE = "שָׁלוֹם, מַה שְׁלוֹמְךָ?"
kept, ok = hebrew_rules.sanitize(GOOD_HE)
check("хорошая огласовка сохраняется", ok and kept == GOOD_HE, f"{kept!r} ok={ok}")

# И главное: при сомнительной записи транскрипция не показывается.
check("при сомнительной записи транскрипции нет",
      bot._reading_if_clean(DIRTY, False, "ru") == "",
      bot._reading_if_clean(DIRTY, False, "ru"))
check("при хорошей записи транскрипция есть",
      bool(bot._reading_if_clean(GOOD_HE, True, "ru")))


# -------------------------------------------------------------- предел
db.init_db()
CHAT = 424242
check("лимит берётся из настроек", db.dialog_left(CHAT) == db.DIALOG_DAILY_LIMIT,
      db.dialog_left(CHAT))
for i in range(db.DIALOG_DAILY_LIMIT):
    db.dialog_add(CHAT, "user", f"реплика {i}")
check("предел исчерпывается", db.dialog_left(CHAT) == 0, db.dialog_left(CHAT))

# Реплики бота предел не тратят: считаем то, что сказал человек.
before = db.dialog_left(CHAT + 1)
db.dialog_add(CHAT + 1, "bot", "שָׁלוֹם")
check("ответы бота не тратят предел", db.dialog_left(CHAT + 1) == before)

# История возвращается в порядке разговора, иначе модель отвечает невпопад.
db.dialog_reset(CHAT)
for role, text in (("user", "раз"), ("bot", "два"), ("user", "три")):
    db.dialog_add(CHAT, role, text)
hist = db.dialog_history(CHAT)
check("история в порядке разговора",
      [x[1] for x in hist] == ["раз", "два", "три"], hist)

# Сброс не трогает чужие разговоры.
db.dialog_add(CHAT + 2, "user", "чужое")
db.dialog_reset(CHAT)
check("сброс не задевает соседей", len(db.dialog_history(CHAT + 2)) == 1)

# Расход считается по токенам, а не по числу сообщений.
db.dialog_reset(CHAT + 2)
db.dialog_add(CHAT, "bot", "שָׁלוֹם", (100, 20))
db.dialog_add(CHAT, "bot", "טוֹב", (50, 10), clean=False)
spend = db.dialog_spend()
check("расход считается", spend.get("tin") == 150 and spend.get("tout") == 30, spend)
check("нечистые ответы считаются отдельно", spend.get("dirty") == 1, spend)


# ------------------------------------------------------- правка в тексте
# Человек должен увидеть СВОЮ фразу с отмеченными правками, а не
# отдельный «правильный вариант» рядом: рядом лежащее он сравнивает сам
# и обычно не сравнивает.
FIXES = [
    # сказано без огласовок, исправлено с ними — отличается только
    # последнее слово, и только оно должно быть отмечено
    ("אני הולך לבית", "אֲנִי הוֹלֵךְ הַבַּיְתָה", ["<s>לבית</s>", "<b>הַבַּיְתָה</b>"]),
    # два слова слиты в одно
    ("אני הולך ל בית ספר", "אֲנִי הוֹלֵךְ לְבֵית סֵפֶר",
     ["<s>ל בית</s>", "<b>לְבֵית</b>"]),
]
for said, fixed, want in FIXES:
    got = dialog.mark_fix(said, fixed)
    check(f"правка отмечена точечно: «{said[:18]}»",
          all(w in got for w in want), got)
    # И главное: неизменённые слова НЕ зачёркнуты. Первый заход
    # зачёркивал фразу целиком — у человека огласовок нет, у
    # исправленной версии есть, то есть отличалось каждое слово.
    check(f"нетронутые слова не зачёркнуты: «{said[:18]}»",
          got.count("<s>") == 1, got)

check("одни огласовки — не правка",
      dialog.mark_fix("שלום", "שָׁלוֹם") == "", dialog.mark_fix("שלום", "שָׁלוֹם"))
check("нечего исправлять — пусто", dialog.mark_fix("שלום", "") == "")
check("разметка экранируется",
      "&lt;" in dialog.mark_fix("<b>шалом", "שָׁלוֹם אֲנִי"),
      dialog.mark_fix("<b>шалом", "שָׁלוֹם אֲנִי"))


# -------------------------------------------------- пол собеседника
# В иврите пол говорящего слышен в самих словах. Женский голос,
# произносящий мужские формы, — это не мелочь оформления, а урок
# неправильной речи.
import audio  # noqa: E402

check("голоса разные у мужчины и женщины",
      audio.voice_for("m") != audio.voice_for("f"),
      f'{audio.voice_for("m")} / {audio.voice_for("f")}')
check("неизвестный пол не роняет озвучку", bool(audio.voice_for(None)))
for who in ("m", "f"):
    sys_text = dialog._system("m", "ru", who)
    want = "мужском" if who == "m" else "женском"
    check(f"собеседник {who} говорит о себе в {want} роде",
          want in sys_text, sys_text.split(".")[0][:80])
check("пол ученика и пол собеседника — разные вещи",
      dialog._system("f", "ru", "m") != dialog._system("m", "ru", "m"))


# ------------------------------------------- наши формы важнее машинных
# Огласовщик Nakdan силён в контексте, но на короткой фразе ошибается, и
# ошибается на словах, которые у нас выверены. Проба на тридцати фразах:
# «касса» он прочитал как «кофе», «два» — как «годы», а инфинитивы увёл
# не в тот биньян. Поэтому его вывод пропускается через наш банк.
import nakdan  # noqa: E402

known = nakdan.known_forms()
check("банк известных форм собрался", len(known) > 1000, len(known))

# Ровно те слова, на которых он промахнулся, у нас есть и перекроют его.
for ours in ("לִקְבֹּעַ", "לַחֲזֹר", "הַקֻּפָּה", "שְׁנַיִם", "לִפְתֹּחַ"):
    check(f"наша форма перекрывает машинную: {ours}",
          known.get(nakdan.strip_niqqud(ours)) == ours,
          known.get(nakdan.strip_niqqud(ours)))

# И сама подмена: даём «ответ службы», в котором слово испорчено, —
# на выходе должно стоять наше.
real = nakdan.vocalize
nakdan.vocalize = lambda text: "אֶפְשָׁר לְפַתֵּחַ חֶשְׁבּוֹן?"
try:
    got = nakdan.vocalize_trusted("אפשר לפתוח חשבון?")
finally:
    nakdan.vocalize = real
check("испорченное слово заменено нашим", "לִפְתֹּחַ" in got, got)
check("знак препинания не потерялся", got.endswith("?"), got)


# ------------------------------------------------- подсказка собеседнику
system = dialog._system("f", "ru")
check("род собеседника попадает в подсказку", "женщина" in system)
check("подсказка упоминает огласовки", "огласовк" in system.lower())
check("подсказка запрещает транскрипцию", "транскрипц" in system.lower())

print()
print(f"Без ключа модели разговор недоступен и не предлагается: "
      f"available={dialog.available()}")
print("Правильность ивритa собеседника машина не проверяет — реплики "
      "пишутся в базу, чтобы их прочитал носитель.")
if fails:
    print(f"\nСБОЕВ: {len(fails)}")
    sys.exit(1)
