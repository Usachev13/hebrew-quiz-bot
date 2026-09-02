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
}


SITUATIONS_EN = {
    "daily": "Everyday: corner shop, market, café",
    "office": "Institutions: bank, Bituach Leumi, health fund",
    "home": "Housing and repairs",
    "meeting": "Meeting people and talking about yourself",
}


def phrase_text(situation, index, ru):
    """Подпись к фразе по-английски. Пусто — если перевода нет."""
    found = PHRASES_EN.get((situation, index))
    return found[1] if found else ""


def note(situation, index):
    return NOTES_EN.get((situation, index), "")
