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
    def __init__(self, body, status=200, text=""):
        self._body = body
        self.status_code = status
        self.text = text

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


# ------------------------------------------- порядок букв в ответе
# Показалось, что модель пишет ивритские слова слева направо. Это
# проверяется однозначно: конечные буквы (ם ן ף ץ ך) бывают ТОЛЬКО в
# конце слова, и при перевёрнутом порядке они оказались бы в начале.
# Наши формальные правила это ловят — ниже тому доказательство, чтобы
# догадка больше не возвращалась.
check("перевёрнутый иврит распознаётся",
      any("середине слова" in p for p in hebrew_rules.problems("םולש! המ עמשנ?")),
      hebrew_rules.problems("םולש! המ עמשנ?"))
check("нормальный иврит не объявляется перевёрнутым",
      not hebrew_rules.problems("שָׁלוֹם! מָה נִשְׁמָע?"))
# А то, что выглядело перевёрнутым в терминале, порядок имеет верный:
# дело в двунаправленной раскладке экрана, а не в ответе модели.
check("спорная фраза из живого прогона в порядке",
      not hebrew_rules.problems("שִׁמְךָ דָּנִיֵּאל. מָה תּוֹעֲדוֹת שֶׁלְּךָ?"))


# ------------------------------------------------- перевод обязателен
# Из живого прогона: модель заполнила «ru» только в первой реплике из
# пяти. Ученик получил ивритские фразы без единого слова по-русски —
# то есть ответ, который он не может прочесть.
no_ru = dialog._parse('{"he": "שלום", "ru": "", "fixed": "", "hint": ""}')
check("пустой перевод виден в разборе", no_ru.get("ru") == "")

saved_ask = dialog._ask_anthropic
saved_vocal = nakdan_mod = None
import nakdan as _nak  # noqa: E402
saved_vocal = _nak.vocalize_trusted
_nak.vocalize_trusted = lambda t: t          # сеть здесь не нужна
dialog.ANTHROPIC_KEY = "x"
dialog.OPENAI_KEY = dialog.GOOGLE_KEY = ""
os.environ.pop("DIALOG_PROVIDER", None)


def _fake(main, second):
    """Первый вызов — основной ответ, второй — дозапрос перевода."""
    calls = iter([(main, (10, 5)), (second, (4, 2))])
    return lambda system, turns: next(calls)


# 1. Перевода нет — дозапрос его даёт, и расход обоих запросов учтён.
dialog._ask_anthropic = _fake(
    '{"he": "שלום", "ru": "", "fixed": "", "hint": ""}', "Привет")
try:
    res = dialog.reply([], "שלום")
finally:
    dialog._ask_anthropic = saved_ask
check("пустой перевод добран дозапросом", res.get("ru") == "Привет", res.get("ru"))
check("расход дозапроса учтён", res.get("usage") == (14, 7), res.get("usage"))
check("добранный перевод не помечен как пустой", not res.get("no_ru"))

# 2. Дозапрос вернул иврит — это не перевод. Первый заход подставлял
#    сюда поле «he», и в строке перевода стоял тот же иврит, что выше.
dialog._ask_anthropic = _fake(
    '{"he": "שלום", "ru": "", "fixed": "", "hint": ""}',
    '{"he": "שלום", "ru": ""}')
try:
    res = dialog.reply([], "שלום")
finally:
    dialog._ask_anthropic = saved_ask
check("иврит не выдаётся за перевод", res.get("ru") == "", res.get("ru"))
check("ответ без перевода помечен", res.get("no_ru") is True, res)

# 3. Перевод есть сразу — дозапроса нет.
dialog._ask_anthropic = _fake(
    '{"he": "שלום", "ru": "Привет", "fixed": "", "hint": ""}', "ЛИШНИЙ")
try:
    res = dialog.reply([], "שלום")
finally:
    dialog._ask_anthropic = saved_ask
    _nak.vocalize_trusted = saved_vocal
check("с переводом дозапроса нет", res.get("ru") == "Привет"
      and res.get("usage") == (10, 5), res)

# Строгую схему принимают не все, кто говорит на протоколе OpenAI.
# Отказ (400) — повод спросить без схемы, а не повод оставить человека
# без собеседника.
sent = []


def _schema_refused(url, **kw):
    has_schema = "response_format" in kw.get("json", {})
    sent.append(has_schema)
    if has_schema:
        return FakeResponse({}, status=400, text="response_format not supported")
    return FakeResponse({"choices": [{"message": {"content": GOOD}}],
                         "usage": {"prompt_tokens": 1, "completion_tokens": 1}})


dialog.requests.post = _schema_refused
try:
    text, _u = dialog._ask_openai("п", [{"role": "user", "content": "ש"}])
finally:
    dialog.requests.post = real_post
check("отказ от схемы — повтор без неё", sent == [True, False]
      and dialog._parse(text).get("he", "").startswith("שָׁלוֹם"), sent)

# Строгая схема перечисляет все четыре поля: без неё перевод терялся в
# четырёх репликах из пяти у gpt-4o-mini и в одной у gpt-4o.
check("схема требует все поля",
      set(dialog.RESPONSE_SCHEMA["schema"]["required"]) == {"he", "ru", "fixed", "hint"})
check("подсказка требует перевода всегда",
      "ВСЕГДА" in dialog._system("m", "ru"))
dialog.ANTHROPIC_KEY = ""


# --------------------------------------------- имя модели у Google
# «gemini-2.5-flash» на одном ключе работает, а на другом отвечает 404
# без объяснений. Проверяем, что мы на это отвечаем не голым кодом
# ошибки, а списком доступных имён.
dialog.GOOGLE_KEY = "x"
dialog.requests.post = lambda *a, **k: FakeResponse(
    {}, status=404, text='{"error":{"message":"not supported for v1beta"}}')
dialog.google_models = lambda: ["gemini-flash-latest", "gemini-pro-latest"]
try:
    dialog._ask_google("п", [{"role": "user", "content": "ש"}])
    said = ""
except RuntimeError as e:
    said = str(e)
finally:
    dialog.requests.post = real_post
    dialog.GOOGLE_KEY = ""
# Своими словами чужую ошибку не пересказываем: в сообщении должно быть
# то, что ответила служба. Иначе выходит нелепость первого захода — бот
# заявлял, что модели нет, и следом перечислял её же первой в списке.
check("404 показывает ответ самой службы",
      "not supported for v1beta" in said, said[:160])
check("404 называет и доступные модели",
      "gemini-flash-latest" in said, said[:160])

# Обе версии API пробуются, прежде чем сдаться.
tried = []
dialog.GOOGLE_KEY = "x"
def _count(url, **k):
    tried.append(url)
    return FakeResponse({}, status=404, text="нет")
dialog.requests.post = _count
try:
    dialog._ask_google("п", [{"role": "user", "content": "ש"}])
except RuntimeError:
    pass
finally:
    dialog.requests.post = real_post
    dialog.GOOGLE_KEY = ""
check("пробуются обе версии API",
      len(tried) == len(dialog.GOOGLE_VERSIONS)
      and any("v1beta" in u for u in tried) and any("/v1/" in u for u in tried),
      tried)


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


# ------------------------------------------- холам от огласовщика
# Dicta пишет «о» холамом на букве ПЕРЕД голым вавом: «יֹופִי». Наше
# чтение принимало такой вав за согласную — «йовфи», «новам». Проверяем
# выравнивание на выходе огласовщика.
from translit import translit as _tr  # noqa: E402

for raw, want in (("יֹופִי", "йофи"), ("נֹועַם", "ноам"), ("עֹוד", "од"),
                  # кубуц перед голым вавом — «у», а не «ув»
                  ("מְעֻולָּה", "меула")):
    got = _tr(nakdan.holam_on_vav(raw))
    check(f"холам перед вавом читается как «о»: {raw}", got == want, got)
check("вав с собственной огласовкой не тронут",
      nakdan.holam_on_vav("מְחֹוָה") == "מְחֹוָה")

# ------------------------------------------- омографы в подмене
# Подмена «наше важнее машинного» для омографов опасна: в банке и שָׁם
# («там»), и שֵׁם («имя»), и прежняя подмена брала первое попавшееся —
# то есть портила верный ответ. Такие скелеты в подмену не идут.
amb = nakdan.ambiguous_forms()
check("омограф не подменяется", "שם" not in nakdan.known_forms()
      and "שם" in amb, sorted(amb.get("שם", [])))
check("«кофе» и «касса» не подменяют друг друга",
      "קפה" not in nakdan.known_forms() and "קפה" in amb)
check("однозначные промахи Dicta по-прежнему закрыты",
      all(nakdan.strip_niqqud(w) in nakdan.known_forms()
          for w in ("לִקְבֹּעַ", "הַקֻּפָּה", "שְׁנַיִם", "לִפְתֹּחַ")))
check("подмена не трогает верный омограф",
      nakdan.trusted_overlay("מָה אַתָּה עוֹשֶׂה שָׁם?").endswith("שָׁם?"),
      nakdan.trusted_overlay("מָה אַתָּה עוֹשֶׂה שָׁם?"))


# ------------------------------------------- источник огласовок
# В режиме «model» огласовки модели берутся, только если они полные и
# без формальных ошибок; иначе Dicta.
saved_src, saved_voc = dialog.NIQQUD, nakdan.vocalize_trusted
nakdan.vocalize_trusted = lambda t: "ОТ_DICTA"
try:
    dialog.NIQQUD = "model"
    check("полные огласовки модели сохранены",
          dialog._vocalize("שָׁם") == "שָׁם", dialog._vocalize("שָׁם"))
    check("без огласовок — к Dicta",
          dialog._vocalize("שם") == "ОТ_DICTA", dialog._vocalize("שם"))
    check("с формальной ошибкой — к Dicta",
          dialog._vocalize("הוֹלֵך") == "ОТ_DICTA", dialog._vocalize("הוֹלֵך"))
    dialog.NIQQUD = "nakdan"
    check("в режиме nakdan модели не верим",
          dialog._vocalize("שָׁם") == "ОТ_DICTA", dialog._vocalize("שָׁם"))
finally:
    dialog.NIQQUD, nakdan.vocalize_trusted = saved_src, saved_voc
# Сборка по словам: модель огласовала не всё — её слова остаются, а
# пробелы заполняет Dicta. Раньше при одном пропуске выбрасывалось всё.
saved_src, saved_voc = dialog.NIQQUD, nakdan.vocalize_trusted
nakdan.vocalize_trusted = lambda t: {
    "שמי רינה, דניאל": "שְׁמִי רִינָּה, דָּנִיֵּאל"}.get(t, t)
try:
    dialog.NIQQUD = "model"
    got, src = dialog._vocalize_with_source("שְׁמִי רינה, דָּנִיאֵל")
finally:
    dialog.NIQQUD, nakdan.vocalize_trusted = saved_src, saved_voc
check("пропуск модели заполнен Dicta", "רִינָּה" in got, got)
check("огласовки модели в остальных словах сохранены",
      "דָּנִיאֵל" in got and "דָּנִיֵּאל" not in got, got)
check("источник назван смешанным", src == "model+nakdan", src)
check("подсказка просит огласовки только в режиме model",
      "Ставь огласовки" not in dialog._system("m", "ru"))


# Температура ниже умолчания у всех поставщиков: для репетитора
# правильная фраза важнее неожиданной. Проверяем, что она доходит до
# запроса, а не лежит константой.
got_temp = {}


def _grab(url, **kw):
    got_temp["t"] = kw.get("json", {}).get("temperature")
    return FakeResponse({"choices": [{"message": {"content": GOOD}}],
                         "usage": {"prompt_tokens": 1, "completion_tokens": 1}})


dialog.requests.post = _grab
try:
    dialog._ask_openai("п", [{"role": "user", "content": "ש"}])
finally:
    dialog.requests.post = real_post
check("температура уходит в запрос",
      got_temp.get("t") == dialog.TEMPERATURE and dialog.TEMPERATURE < 1,
      got_temp)


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
