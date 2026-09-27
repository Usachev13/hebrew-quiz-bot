# -*- coding: utf-8 -*-
"""
Английские подписи к речевым моделям.

Ключ — ситуация и номер, тот же, из которого собирается `say:daily:0`.
Номер хрупок: переставь фразы местами, и переводы молча разъедутся —
человек увидит «Сколько это стоит?» с подписью «Can I have a bag?».

Поэтому рядом с переводом лежит РУССКИЙ ОРИГИНАЛ, каким он был на момент
перевода. Сам по себе он не используется; его сверяет
`tools/check_i18n.py` с phrases.py и падает при первом расхождении.
Это дублирование намеренное: лишняя строка в файле дешевле, чем
неправильная подпись под фразой, которую человек произнесёт вслух.

Менять ключ на что-то устойчивое (иврит, например) сейчас нельзя:
`say:daily:0` уже лежит в прогрессе у пользователей, и смена ключа
обнулила бы им повторения — ровно та беда, от которой мы только что
ушли в карточках.

О переводе
----------
Переводится не русская фраза, а то, что человек хочет сказать. Русское
«Мне кофе, пожалуйста» — это не «To me a coffee», а «A coffee, please»:
короткий заказ. Дословность здесь вредна вдвойне, потому что подпись
объясняет назначение фразы, а не разбирает её по словам.
"""

# ru — оригинал на момент перевода, для сверки; en — сама подпись
PHRASES_EN = {
    ("daily", 0): ("Сколько это стоит?", "How much is it?"),
    ("daily", 1): ("У вас есть {}?", "Do you have {}?"),
    ("daily", 2): ("Я хочу {}, пожалуйста", "I would like {}, please"),
    ("daily", 3): ("Можно пакет?", "Could I have a bag?"),
    ("daily", 4): ("Без пакета, спасибо", "No bag, thank you"),
    ("daily", 5): ("Это всё, спасибо", "That's all, thank you"),
    ("daily", 6): ("Я плачу картой", "I'm paying by card"),
    ("daily", 7): ("Есть скидка?", "Is there a discount?"),
    ("daily", 8): ("Сколько за килограмм?", "How much per kilo?"),
    ("daily", 9): ("Счёт, пожалуйста", "The bill, please"),
    ("daily", 10): ("Можно меню?", "Could I have the menu?"),
    ("daily", 11): ("Мне {}, пожалуйста", "{}, please"),

    ("office", 0): ("У меня запись", "I have an appointment"),
    ("office", 1): ("Мне нужно записаться", "I need to make an appointment"),
    ("office", 2): ("Где очередь?", "Where is the queue?"),
    ("office", 3): ("Я не понимаю", "I don't understand"),
    ("office", 4): ("Можно помедленнее, пожалуйста?", "Could you speak more slowly, please?"),
    ("office", 5): ("Можно повторить?", "Could you say that again?"),
    ("office", 6): ("Кто-нибудь говорит по-русски?", "Does anyone speak English?"),
    ("office", 7): ("Я новый репатриант", "I'm a new immigrant"),
    ("office", 8): ("Какие документы нужны?", "Which documents are needed?"),
    ("office", 9): ("Сколько времени это займёт?", "How long will it take?"),
    ("office", 10): ("Я хочу открыть счёт", "I'd like to open an account"),
    ("office", 11): ("Напишите мне, пожалуйста", "Please write it down for me"),

    ("home", 0): ("Я ищу квартиру", "I'm looking for a flat"),
    ("home", 1): ("Сколько стоит аренда?", "How much is the rent?"),
    ("home", 2): ("Арнона включена?", "Is arnona included?"),
    ("home", 3): ("Есть кондиционер?", "Is there air conditioning?"),
    ("home", 4): ("Когда можно посмотреть?", "When can I see it?"),
    ("home", 5): ("У меня проблема с {}", "I have a problem with {}"),
    ("home", 6): ("Вода не работает", "The water isn't working"),
    ("home", 7): ("Можно прислать мастера?", "Could you send a technician?"),
    ("home", 8): ("Когда он приедет?", "When will he come?"),
    ("home", 9): ("Сколько это будет стоить?", "How much will it cost?"),
    ("home", 10): ("Это срочно", "It's urgent"),
    ("home", 11): ("Я живу на {} этаже", "I live on the {} floor"),

    ("meeting", 0): ("Здравствуйте, меня зовут…", "Hello, my name is…"),
    ("meeting", 1): ("Очень приятно", "Nice to meet you"),
    ("meeting", 2): ("Откуда ты?", "Where are you from?"),
    ("meeting", 3): ("Я из России", "I'm from Russia"),
    ("meeting", 4): ("Я живу в {}", "I live in {}"),
    ("meeting", 5): ("Чем ты занимаешься?", "What do you do?"),
    ("meeting", 6): ("Я учу иврит", "I'm learning Hebrew"),
    ("meeting", 7): ("Я плохо говорю на иврите", "I don't speak Hebrew well"),
    ("meeting", 8): ("У меня {} детей", "I have {} children"),
    ("meeting", 9): ("Извините, как сказать {}?", "Excuse me, how do you say {}?"),
    ("meeting", 10): ("Приятно познакомиться, до свидания",
                      "It was nice meeting you, goodbye"),
    ("meeting", 11): ("Можно твой телефон?", "Could I have your phone number?"),

    # --- дописано вторым заходом вместе с самими фразами ---
    ("daily", 12): ("Слишком дорого", "That's too expensive"),
    ("daily", 13): ("Можно попробовать?", "Can I taste it?"),
    ("daily", 14): ("Где касса?", "Where is the till?"),
    ("daily", 15): ("Полкило, пожалуйста", "Half a kilo, please"),
    ("daily", 16): ("Это свежее?", "Is this fresh?"),
    ("daily", 17): ("Дайте два, пожалуйста", "Two, please"),
    ("daily", 18): ("С собой, пожалуйста", "To take away, please"),
    ("daily", 19): ("Здесь, пожалуйста", "To eat in, please"),

    ("office", 12): ("Вот моё удостоверение", "Here is my ID"),
    ("office", 13): ("Где подписать?", "Where do I sign?"),
    ("office", 14): ("Я не получил письмо", "I didn't get the letter"),
    ("office", 15): ("Кажется, это ошибка", "I think this is a mistake"),
    ("office", 16): ("Можно копию?", "Could I have a copy?"),
    ("office", 17): ("Куда мне идти?", "Where should I go?"),
    ("office", 18): ("Я уже отправил документы", "I've already sent the documents"),
    ("office", 19): ("Когда будет ответ?", "When will there be an answer?"),

    ("home", 12): ("Сколько залог?", "How much is the deposit?"),
    ("home", 13): ("Есть лифт?", "Is there a lift?"),
    ("home", 14): ("Когда можно въехать?", "When can I move in?"),
    ("home", 15): ("Кто платит за воду?", "Who pays for the water?"),
    ("home", 16): ("Можно с животными?", "Are pets allowed?"),
    ("home", 17): ("Есть парковка?", "Is there parking?"),
    ("home", 18): ("На какой срок договор?", "How long is the contract for?"),
    ("home", 19): ("Я хочу посмотреть ещё раз", "I'd like to see it again"),

    ("meeting", 12): ("Сколько тебе лет?", "How old are you?"),
    ("meeting", 13): ("Я женат", "I'm married"),
    ("meeting", 14): ("Где ты учил иврит?", "Where did you learn Hebrew?"),
    ("meeting", 15): ("Давай встретимся", "Let's meet up"),
    ("meeting", 16): ("Я здесь два года", "I've been here two years"),
    ("meeting", 17): ("Мне нравится в Израиле", "I like it in Israel"),
    ("meeting", 18): ("У тебя есть ватсап?", "Are you on WhatsApp?"),
    ("meeting", 19): ("Я тебе напишу", "I'll message you"),

    ("time", 0): ("Во сколько?", "At what time?"),
    ("time", 1): ("Сейчас три часа", "It's three o'clock"),
    ("time", 2): ("Можно в три?", "Could we say three?"),
    ("time", 3): ("Мне подходит", "That works for me"),
    ("time", 4): ("Мне не подходит", "That doesn't work for me"),
    ("time", 5): ("Завтра подойдёт?", "Does tomorrow work?"),
    ("time", 6): ("Я опоздаю на десять минут", "I'll be ten minutes late"),
    ("time", 7): ("Я уже в пути", "I'm on my way"),
    ("time", 8): ("Через час", "In an hour"),
    ("time", 9): ("Когда ты свободен?", "When are you free?"),
    ("time", 10): ("Сегодня я занят", "I'm busy today"),
    ("time", 11): ("Можно перенести?", "Could we reschedule?"),

    ("transport", 0): ("Этот автобус идёт до {}?", "Does this bus go to {}?"),
    ("transport", 1): ("Где остановка?", "Where is the stop?"),
    ("transport", 2): ("Сколько стоит проезд?", "How much is the fare?"),
    ("transport", 3): ("Когда следующий автобус?", "When is the next bus?"),
    ("transport", 4): ("Пополнить Рав-Кав, пожалуйста", "Top up my Rav-Kav, please"),
    ("transport", 5): ("Где мне выходить?", "Where do I get off?"),
    ("transport", 6): ("Скажите, когда выходить", "Tell me when to get off"),
    ("transport", 7): ("Я выхожу на следующей", "I'm getting off at the next stop"),
    ("transport", 8): ("Остановите здесь, пожалуйста", "Stop here, please"),
    ("transport", 9): ("В центр, пожалуйста", "To the centre, please"),
    ("transport", 10): ("Включите счётчик, пожалуйста", "Put the meter on, please"),

    ("health", 0): ("Мне плохо", "I feel unwell"),
    ("health", 1): ("У меня болит здесь", "It hurts here"),
    ("health", 2): ("У меня болит голова", "I have a headache"),
    ("health", 3): ("У меня температура", "I have a temperature"),
    ("health", 4): ("Мне нужен врач", "I need a doctor"),
    ("health", 5): ("У меня аллергия на {}", "I'm allergic to {}"),
    ("health", 6): ("Я принимаю лекарство", "I'm taking medication"),
    ("health", 7): ("Нужен рецепт?", "Do I need a prescription?"),
    ("health", 8): ("Как это принимать?", "How do I take this?"),
    ("health", 9): ("Сколько раз в день?", "How many times a day?"),
    ("health", 10): ("Болит уже неделю", "It's been hurting for a week"),
    ("health", 11): ("У меня есть страховка", "I have insurance"),

    ("emergency", 0): ("Помогите!", "Help!"),
    ("emergency", 1): ("Мне нужна помощь", "I need help"),
    ("emergency", 2): ("Вызовите скорую", "Call an ambulance"),
    ("emergency", 3): ("Вызовите полицию", "Call the police"),
    ("emergency", 4): ("Мне нехорошо", "I don't feel well"),
    ("emergency", 5): ("Здесь авария", "There's been an accident here"),
    ("emergency", 6): ("Я заблудился", "I'm lost"),
    ("emergency", 7): ("Я потерял документы", "I've lost my documents"),
    ("emergency", 8): ("Где ближайшая больница?", "Where is the nearest hospital?"),
    ("emergency", 9): ("Позвоните моей жене", "Call my wife"),
    ("emergency", 10): ("Это срочно, пожалуйста", "This is urgent, please"),
}


# Пояснения. Переведены не все: часть примечаний объясняет русскому
# человеку то, что англоязычному объяснять не нужно, и наоборот.
NOTES_EN = {
    ("daily", 11): "This is how you order briefly in a café, without a verb.",
    ("office", 0): "תּוֹר means both «queue» and «appointment».",
    ("home", 2): ("Arnona is the municipal tax. Listings often exclude it, "
                  "so this is the first question when renting."),
    ("meeting", 2): "The form depends on who you are talking to, not on you.",
    # Фраза записана как «Я из России» и озвучена так же — менять её на
    # «I'm from …» нельзя: диктор произнёс бы предлог без страны.
    # Поэтому объясняем словами, а не переписываем данные.
    ("meeting", 3): ("Replace רוּסְיָה with your own country — "
                     "אַנְגְּלִיָּה (England), אַרְצוֹת הַבְּרִית (the USA), "
                     "צָרְפַת (France)."),
    ("meeting", 5): "The form depends on who you are talking to.",
    ("meeting", 9): "You fill the gap yourself, in your own language.",

    ("daily", 13): "About food at the market. Trying on clothes is a different verb.",
    ("daily", 18): "In a café they ask «here or to take away» — this is the answer.",
    ("daily", 19): "The other answer to the same question, if you're staying.",
    ("office", 12): "Teudat zehut. Asked for at every counter — have it ready.",
    ("office", 14): "First-person past is the same for men and women.",
    ("meeting", 12): "«Ben» to a man, «bat» to a woman — the word itself changes.",
    ("meeting", 13): "A woman says «nesua» — I'm married.",
    ("meeting", 16): "«Shnatayim» is a special form for two years, not «two» + «years».",
    ("time", 1): "Hours are counted in the feminine: shalosh, not shlosha.",
    ("transport", 4): "Rav-Kav is the travel card — you can't board a bus without one.",
    ("transport", 10): "Ask straight away in a taxi, or they'll name a price themselves.",
    ("health", 1): "Literally «it hurts to me». Pointing works too.",
    ("emergency", 0): "A cry for help. Asking someone for a favour is a different phrase.",
    ("emergency", 6): "First-person past is the same for men and women.",
    # Разговорный слой. Переводим не буквально, а по употреблению:
    # «сабаба» это не «вращение», а «fine by me».
    ("street", 0): ("Класс, отлично (согласие на всё)", "Cool, fine by me"),
    ("street", 1): ("Ну же, давай! (поторопить)", "Come on, let's go!"),
    ("street", 2): ("Ну, пока! (при прощании)", "Alright, bye!"),
    ("street", 3): ("Ух ты! Да ну! (удивление)", "Wow! No way!"),
    ("street", 4): ("Стыд, неловкая вышла история", "How embarrassing"),
    ("street", 5): ("Бардак, неразбериха", "A mess, chaos"),
    ("street", 6): ("Именно так; и назло", "Precisely; and out of spite"),
    ("street", 7): ("Дорогой мой (ласково, к мужчине)", "My dear (to a man)"),
}


SITUATIONS_EN = {
    "daily": "Everyday: corner shop, market, café",
    "office": "Institutions: bank, Bituach Leumi, health fund",
    "home": "Housing and repairs",
    "meeting": "Meeting people and talking about yourself",
    "time": "Time and arrangements",
    "transport": "Transport: bus, train, taxi",
    "health": "At the doctor and the pharmacy",
    "emergency": "If something happens",
    "street": "How people actually talk",
}


def phrase_text(situation, index, ru):
    """Подпись к фразе по-английски. Пусто — если перевода нет."""
    found = PHRASES_EN.get((situation, index))
    return found[1] if found else ""


def note(situation, index):
    return NOTES_EN.get((situation, index), "")
