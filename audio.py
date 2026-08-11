# -*- coding: utf-8 -*-
"""
Озвучка карточек.

Файлы генерируются заранее (см. tools/generate_audio.py) и лежат на
сервере. В рантайме бот ничего не синтезирует: это и бесплатно, и
мгновенно, и не зависит от доступности стороннего API во время урока.

Имя файла — хеш от ивритского текста, чтобы не возиться с огласовками
и направлением письма в именах файлов.
"""

import hashlib
import json
import os

import requests

# Одна сессия на процесс вместо голого requests.post. Без неё каждый
# запрос к Telegram открывает новое TCP-соединение и заново жмёт руки по
# TLS — а на один вопрос их уходит три (вердикт, голосовое, следующий
# вопрос). Сессия держит соединение открытым, и накладные расходы
# платятся один раз.
SESSION = requests.Session()

AUDIO_DIR = os.environ.get(
    "BOT_AUDIO_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio"),
)


def audio_key(text):
    """Стабильное имя файла для ивритского текста."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def audio_path(text, slow=False):
    """Файл озвучки. Медленный вариант хранится отдельно: переключать
    скорость на лету нельзя — файлы сгенерированы заранее."""
    suffix = "_slow" if slow else ""
    return os.path.join(AUDIO_DIR, f"{audio_key(text)}{suffix}.ogg")


def has_audio(text, slow=False):
    p = audio_path(text, slow)
    return os.path.exists(p) and os.path.getsize(p) > 0


def file_key(path):
    """Ключ кэша file_id для конкретного файла.

    Telegram, приняв файл, отдаёт file_id — по нему то же аудио можно
    слать без повторной загрузки. Но file_id привязан к содержимому: если
    карточку переозвучили, старый идентификатор укажет на старое звучание.
    Поэтому в ключ входят размер и время правки — после перегенерации
    ключ меняется сам, и файл заливается заново ровно один раз.
    """
    try:
        st = os.stat(path)
    except OSError:
        return None
    return f"{os.path.basename(path)}:{st.st_size}:{int(st.st_mtime)}"


SAMPLES_DIR = os.path.join(AUDIO_DIR, "samples")

# Текст для сравнения голосов. Хранится с огласовками — как и весь наш
# банк; в синтезатор он уходит в том же виде, что и карточки (см.
# TTS_TEXT_FORM), поэтому образец всегда отражает реальное звучание.
# Подобран из нашей же лексики и так, чтобы звучали спорные места:
# гортанные ח и ע, «р», ש/שׂ, разные типы предложений.
# Текст намеренно набит проблемными словами, а не «красивый»:
#   • сеголатные (ударение на предпоследнем слоге, синтезатор ошибается):
#     בֹּקֶר, יֶלֶד, לֶחֶם, סֵפֶר, דֶּלֶת, כֶּסֶף, חֶדֶר, עֶרֶב
#   • камац катан (читается «о», а не «а»): כָּל
#   • патах гнува (гласная звучит перед буквой): תַּפּוּחַ, לוֹקֵחַ, שָׁבוּעַ
#   • гортанные: חָבֵר, עִבְרִית
SAMPLE_TEXT = (
    "בַּבֹּקֶר הַיֶּלֶד אוֹכֵל לֶחֶם וְתַפּוּחַ. "
    "אַחַר כָּךְ הוּא לוֹקֵחַ סֵפֶר וְיוֹצֵא מֵהַדֶּלֶת. "
    "כָּל שָׁבוּעַ אֲנִי מְשַׁלֵּם כֶּסֶף עַל הַחֶדֶר. "
    "בָּעֶרֶב חָבֵר טוֹב מְדַבֵּר אִתִּי בְּעִבְרִית."
)

SAMPLE_TRANSLATION = (
    "Утром ребёнок ест хлеб и яблоко. "
    "Потом он берёт книгу и выходит из двери. "
    "Каждую неделю я плачу деньги за комнату. "
    "Вечером хороший друг говорит со мной на иврите."
)


STRESS_DIR = os.path.join(AUDIO_DIR, "stress")
VARIANTS_DIR = os.path.join(AUDIO_DIR, "variants")


def voice_samples(directory=None, speed=None):
    """Готовые образцы: [(подпись, путь к файлу), ...].

    speed — отобрать только образцы этой скорости («normal» / «slow»).
    Подписи лежат в manifest.json рядом с файлами: разбирать их из имён
    файлов было бы хрупко, а показать в Telegram надо по-человечески.
    """
    directory = directory or SAMPLES_DIR
    if not os.path.isdir(directory):
        return []

    meta = {}
    manifest = os.path.join(directory, "manifest.json")
    if os.path.exists(manifest):
        try:
            with open(manifest, encoding="utf-8") as f:
                meta = json.load(f)
        except (ValueError, OSError) as e:
            print(f"[voice_samples] не читается manifest.json: {e}")

    out = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".ogg"):
            continue
        path = os.path.join(directory, name)
        if os.path.getsize(path) == 0:
            continue

        info = meta.get(name)
        # В старых манифестах подпись была просто строкой, без скорости
        if isinstance(info, dict):
            caption, item_speed = info.get("caption", name[:-4]), info.get("speed")
        else:
            caption, item_speed = (info or name[:-4]), None

        if speed and item_speed and item_speed != speed:
            continue
        out.append((caption, path))
    return out


def sample_speeds(directory=None):
    """Какие скорости вообще есть среди образцов."""
    directory = directory or SAMPLES_DIR
    manifest = os.path.join(directory, "manifest.json")
    if not os.path.exists(manifest):
        return []
    try:
        with open(manifest, encoding="utf-8") as f:
            meta = json.load(f)
    except (ValueError, OSError):
        return []
    return sorted({v.get("speed") for v in meta.values()
                   if isinstance(v, dict) and v.get("speed")})


def _sent_file_id(response):
    """file_id из ответа Telegram — если отправка удалась."""
    try:
        body = response.json()
    except ValueError:
        return None
    if not body.get("ok"):
        return None
    return (body.get("result") or {}).get("voice", {}).get("file_id")


def send_voice_file(api_url, chat_id, path, caption=None, file_id=None):
    """Отправляет файл голосовым. Возвращает file_id или None.

    file_id — идентификатор уже загруженного файла. Если он есть, аудио
    не заливается вовсе: Telegram берёт его со своей стороны, и вместо
    загрузки уходит короткий запрос. Именно эта загрузка и была причиной
    паузы перед каждым голосовым.

    Возвращённый file_id стоит сохранить: со второго раза то же слово
    отправляется мгновенно.
    """
    data = {"chat_id": str(chat_id)}
    if caption:
        data["caption"] = caption

    if file_id:
        try:
            r = SESSION.post(f"{api_url}/sendVoice",
                             data={**data, "voice": file_id}, timeout=20)
            got = _sent_file_id(r)
            if got:
                return got
            # file_id протух (файл перезалили, бот сменился) — не беда,
            # ниже загрузим обычным путём.
            print(f"[send_voice_file] file_id не принят, гружу файл: {path}")
        except requests.exceptions.RequestException as e:
            print(f"[send_voice_file] по file_id не вышло: {e}")

    try:
        with open(path, "rb") as f:
            r = SESSION.post(
                f"{api_url}/sendVoice",
                data=data,
                files={"voice": (os.path.basename(path), f, "audio/ogg")},
                timeout=20,
            )
        return _sent_file_id(r)
    except (requests.exceptions.RequestException, OSError) as e:
        print(f"[send_voice_file] {e}")
        return None


def send_voice(api_url, chat_id, text, caption=None, slow=False, file_id=None):
    """Отправляет голосовое с произношением. Молча ничего не делает,
    если файла нет — озвучка не должна ломать урок."""
    if slow and not has_audio(text, slow=True):
        slow = False          # медленного варианта нет — отдаём обычный
    if not has_audio(text, slow):
        return None
    return send_voice_file(api_url, chat_id, audio_path(text, slow),
                           caption, file_id)
