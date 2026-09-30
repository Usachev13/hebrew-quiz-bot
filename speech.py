# -*- coding: utf-8 -*-
"""
Голос ученика: распознавание и сверка с ожидаемой фразой.

Что это даёт и чего не даёт
---------------------------
Даёт: печатную расшифровку того, что услышал распознаватель, и разбор
расхождений со ожидаемой фразой — какое слово пропущено, какое лишнее,
какое сказано другим.

НЕ даёт оценки произношения. Отдельная услуга Azure, которая считает
точность по фонемам и беглость, поддерживает 33 локали, и иврита среди
них нет — проверено по их же таблице языков. Поэтому вердикт у нас
звучит «фраза узнаётся», а не «произношение верное»: распознаватель
опирается на языковую модель и дотягивает кривое произношение до
ожидаемого слова, то есть склонен хвалить.

Ударение он не слышит вовсе. Это уже проверено на нашей озвучке: в
verify_audio то же ограничение записано, «тапуах» возвращается
одинаково, куда бы ударение ни падало.

Формат
------
Telegram присылает голосовые в ogg/opus — ровно в том, в котором мы сами
синтезируем и который Azure принимает. Перекодировать не нужно.
"""

import difflib
import os

import requests

from matching import _normalize          # то же сравнение, что у набора руками

AZURE_KEY = os.environ.get("AZURE_SPEECH_KEY", "")
AZURE_REGION = os.environ.get("AZURE_SPEECH_REGION", "uaenorth")
STT_URL = (f"https://{AZURE_REGION}.stt.speech.microsoft.com"
           "/speech/recognition/conversation/cognitiveservices/v1")
# Больше — уже не голосовое сообщение, а подкаст: не тратим ни время, ни
# минуты распознавания.
MAX_VOICE_SECONDS = 30


class NoKey(RuntimeError):
    """Ключа распознавания нет — функцию просто нельзя предлагать."""


def available():
    return bool(AZURE_KEY)


def download(api_url, file_id, token):
    """Забирает файл голосового у Telegram."""
    meta = requests.get(f"{api_url}/getFile",
                        params={"file_id": file_id}, timeout=30).json()
    if not meta.get("ok"):
        raise RuntimeError(f"getFile: {meta}")
    path = meta["result"]["file_path"]
    r = requests.get(f"https://api.telegram.org/file/bot{token}/{path}",
                     timeout=60)
    r.raise_for_status()
    return r.content


WAV = "audio/wav; codecs=audio/pcm; samplerate=16000"
OGG = "audio/ogg; codecs=opus"


def recognize(data, lang="he-IL", content_type=OGG):
    """Что услышал распознаватель: (текст, уверенность 0..1).

    Просим подробный формат: кроме текста он отдаёт уверенность, а низкая
    уверенность — слабый, но бесплатный признак того, что сказано
    неразборчиво.
    """
    if not AZURE_KEY:
        raise NoKey("нет AZURE_SPEECH_KEY")
    r = requests.post(
        STT_URL,
        params={"language": lang, "format": "detailed"},
        headers={
            "Ocp-Apim-Subscription-Key": AZURE_KEY,
            # Голосовые Telegram — ogg/opus. Приложение пишет WAV сам:
            # браузеры отдают webm или mp4, а их Azure не принимает.
            "Content-Type": content_type,
            "Accept": "application/json",
        },
        data=data,
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
    body = r.json()
    if body.get("RecognitionStatus") != "Success":
        return "", 0.0
    best = (body.get("NBest") or [{}])[0]
    text = best.get("Display") or body.get("DisplayText", "")
    return text, float(best.get("Confidence") or 0.0)


# Макаф — ивритский дефис. Он склеивает слова на письме («רַב־קַו»), а
# произносятся они раздельно, и распознавание возвращает их двумя
# словами. Без этой замены сверка объявляла «не хватает רב־קו, лишние
# רב и קו» — то есть ругала за то, что человек сказал ровно верно.
MAQAF = "\u05be"
TAIL = ".,!?:;\"'"


def words(text):
    """Слова для СРАВНЕНИЯ: без огласовок, с обычными софитами.

    В таком виде их отдаёт распознавание, и в таком же мы сверяем набранные
    руками ответы.
    """
    cleaned = _normalize((text or "").replace(MAQAF, " "))
    return [w.strip(TAIL) for w in cleaned.split() if w.strip(TAIL)]


# Буквы, которые в современном израильском произношении не звучат.
# Распознавание пишет то, что слышит, и на слух «лит'он» и «литон»
# неразличимы: לִטְעוֹן ему возвращается как לטון. Ругать за это нельзя —
# человек произнёс верно, разошлась запись, а не звук.
#
# ע и א молчат везде. ה молчит только в конце слова: в начале это «ха»
# определённого артикля, и путать הבית с בית мы не станем.
SILENT = "אע"


def sound_key(word):
    """Как слово звучит, а не как пишется.

    Нужен только для поблажки: если написания разошлись, а звучание
    совпало, считаем слово сказанным. Сам разбор показывает исходные
    написания — иначе человек решит, что он сказал «לטונ».
    """
    # Короткие слова — только точное совпадение. Поблажка на них
    # опаснее пользы: без алефа и конечной ה и «אֶת», и «תֵּה»
    # превращаются в «ת», то есть чай сошёл бы за винительный падеж.
    if len(word) <= 2:
        return word
    w = "".join(c for c in word if c not in SILENT)
    while w.endswith("ה") and len(w) > 1:
        w = w[:-1]
    # Полное и неполное написание: קו и קוו, בקשה и בקששה — одно и то же.
    out = []
    for c in w:
        if out and out[-1] == c and c in "וי":
            continue
        out.append(c)
    return "".join(out) or word


def shown(text):
    """Слова для ПОКАЗА: как написаны, без нормализации.

    Сравнивать нормализованное, а показывать нормализованное — разные
    вещи: «שלום» превращается в «שלומ», и человек решит, что он так и
    сказал.
    """
    # Макаф разбираем и здесь, иначе списки «для показа» и «для сравнения»
    # разной длины, и показывать приходится нормализованное: человек
    # видит «לטעונ» и решает, что он так и сказал.
    return [w.strip(TAIL) for w in (text or "").replace(MAQAF, " ").split()
            if w.strip(TAIL)]


def compare(heard, expected):
    """Сверка услышанного с ожидаемым.

    Возвращает:
      verdict — "match" | "close" | "different" | "silence"
      heard   — что услышано (как есть, для показа)
      diff    — список ("=", слово) / ("-", пропущено) / ("+", лишнее)

    «close» — когда отличается одно слово из трёх и более. Для коротких
    фраз такой поблажки нет: в двух словах одно неверное это половина.
    """
    h, e = words(heard), words(expected)
    if not h:
        return {"verdict": "silence", "heard": "", "diff": []}
    # Показываем исходные написания, а сравниваем нормализованные. Списки
    # идут парами; если распознавание вернуло не столько слов, сколько
    # после нормализации (такого быть не должно, но), показываем
    # нормализованные — лучше некрасиво, чем не то слово.
    h_show = shown(heard) if len(shown(heard)) == len(h) else h
    e_show = shown(expected) if len(shown(expected)) == len(e) else e

    # Сравниваем по звучанию, показываем по написанию. Иначе человек,
    # сказавший верно, получает крестик из-за того, как распознавание
    # решило записать услышанное.
    e_key = [sound_key(w) for w in e]
    h_key = [sound_key(w) for w in h]

    diff = []
    sm = difflib.SequenceMatcher(a=e_key, b=h_key, autojunk=False)
    same = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            same += i2 - i1
            diff += [("=", w) for w in e_show[i1:i2]]
        elif tag == "delete":
            diff += [("-", w) for w in e_show[i1:i2]]
        elif tag == "insert":
            diff += [("+", w) for w in h_show[j1:j2]]
        else:                                 # replace
            diff += [("-", w) for w in e_show[i1:i2]]
            diff += [("+", w) for w in h_show[j1:j2]]

    if same == len(e_key) == len(h_key):
        verdict = "match"
    elif len(e_key) >= 3 and same >= len(e_key) - 1:
        verdict = "close"
    else:
        verdict = "different"
    return {"verdict": verdict, "heard": heard.strip(), "diff": diff}
