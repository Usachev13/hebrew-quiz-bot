/* Подставные данные для режима предпросмотра.

   Нужен, чтобы страницу можно было открыть без Telegram и без базы:
   разработчик (или помощник) видит вёрстку сразу, не выкатывая сборку и
   не заходя с телефона. Реальных данных здесь нет и быть не может —
   подменяются и Telegram, и сам fetch, так что до API дело не доходит. */
window.Telegram = { WebApp: { initData:"preview", colorScheme:"light",
  initDataUnsafe:{ user:{ id:0, first_name:"Даниил", last_name:"" } },
  ready(){}, expand(){}, onEvent(){}, setBackgroundColor(){}, setHeaderColor(){},
  BackButton:{show(){},hide(){},onClick(){}}, HapticFeedback:{} } };

const PW = [["хлеб","לֶחֶם","лехем"],["вода","מַיִם","мáйим"],["молоко","חָלָב","халав"],
  ["яблоко","תַּפּוּחַ","тапуах"],["сыр","גְּבִינָה","гвина"],["мясо","בָּשָׂר","басар"],
  ["рыба","דָּג","даг"],["яйцо","בֵּיצָה","бейца"],["суп","מָרָק","марак"],
  ["дом","בַּיִת","бáйит"]];
const PT = [["greetings","Приветствия",12,10,3],["family","Семья",18,10,2],
  ["food","Еда",26,4,0],["home","Дом",18,1,0],["city","Город",18,0,0],
  ["transport","Транспорт",12,2,1],["time","Время",21,1,0],["weather","Погода",10,0,0],
  ["health","Здоровье",17,1,0],["shopping","Покупки",14,0,0],
  ["work_study","Работа и учёба",14,1,0],["clothes","Одежда",10,1,0],
  ["emotions","Эмоции",11,0,0]];

let PREVIEW_NAME = {ru:"Даниил", heb:"דניאל", auto:"דניאל",
                    guess:false, edited:false};

const ALEF = {"alef_by_name": [{"ru": "как выглядит «алеф»", "he": "א", "opts": ["ט", "צ", "ש", "א"]}, {"ru": "как выглядит «бет / вет»", "he": "ב", "opts": ["ה", "ע", "ב", "ז"]}, {"ru": "как выглядит «гимель»", "he": "ג", "opts": ["ת", "ג", "ש", "מ"]}, {"ru": "как выглядит «далет»", "he": "ד", "opts": ["כ", "מ", "פ", "ד"]}, {"ru": "как выглядит «хей»", "he": "ה", "opts": ["ס", "ה", "ר", "ת"]}, {"ru": "как выглядит «вав»", "he": "ו", "opts": ["א", "ט", "ו", "כ"]}, {"ru": "как выглядит «заин»", "he": "ז", "opts": ["ז", "ת", "ד", "ב"]}, {"ru": "как выглядит «хет»", "he": "ח", "opts": ["ע", "ר", "ל", "ח"]}, {"ru": "как выглядит «тет»", "he": "ט", "opts": ["ו", "צ", "ז", "ט"]}, {"ru": "как выглядит «йуд»", "he": "י", "opts": ["ר", "ח", "י", "ב"]}], "alef_dotted": [{"ru": "звук буквы בּ", "he": "б", "opts": ["ф", "в", "х", "б"]}, {"ru": "звук буквы ב", "he": "в", "opts": ["б", "ш", "в", "п"]}, {"ru": "звук буквы כּ", "he": "к", "opts": ["х", "к", "с", "ф"]}, {"ru": "звук буквы כ", "he": "х", "opts": ["в", "х", "с", "ф"]}, {"ru": "звук буквы פּ", "he": "п", "opts": ["ш", "п", "ф", "б"]}, {"ru": "звук буквы פ", "he": "ф", "opts": ["х", "ф", "к", "б"]}, {"ru": "звук буквы שׁ", "he": "ш", "opts": ["в", "ф", "б", "ш"]}, {"ru": "звук буквы שׂ", "he": "с", "opts": ["к", "б", "ш", "с"]}], "alef_finals": [{"ru": "конечная форма буквы כ", "he": "ך", "opts": ["ך", "ץ", "ן", "ם"]}, {"ru": "конечная форма буквы מ", "he": "ם", "opts": ["ם", "ף", "ץ", "ך"]}, {"ru": "конечная форма буквы נ", "he": "ן", "opts": ["ך", "ף", "ץ", "ן"]}, {"ru": "конечная форма буквы פ", "he": "ף", "opts": ["ן", "ף", "ץ", "ם"]}, {"ru": "конечная форма буквы צ", "he": "ץ", "opts": ["ף", "ם", "ן", "ץ"]}], "alef_names": [{"ru": "буква א", "he": "алеф", "opts": ["мем", "алеф", "шин / син", "самех"]}, {"ru": "буква ב", "he": "бет / вет", "opts": ["тет", "бет / вет", "пей / фей", "йуд"]}, {"ru": "буква ג", "he": "гимель", "opts": ["шин / син", "гимель", "вав", "бет / вет"]}, {"ru": "буква ד", "he": "далет", "opts": ["йуд", "тет", "далет", "самех"]}, {"ru": "буква ה", "he": "хей", "opts": ["хет", "цади", "далет", "хей"]}, {"ru": "буква ו", "he": "вав", "opts": ["хет", "вав", "заин", "мем"]}, {"ru": "буква ז", "he": "заин", "opts": ["заин", "куф", "нун", "вав"]}, {"ru": "буква ח", "he": "хет", "opts": ["каф / хаф", "хет", "нун", "мем"]}, {"ru": "буква ט", "he": "тет", "opts": ["самех", "пей / фей", "тав", "тет"]}, {"ru": "буква י", "he": "йуд", "opts": ["хет", "йуд", "цади", "пей / фей"]}], "alef_niqqud": [{"ru": "огласовка בַ — какой звук", "he": "а", "opts": ["э", "и", "нет гласного", "а"]}, {"ru": "огласовка בָ — какой звук", "he": "а", "opts": ["и", "о", "у", "а"]}, {"ru": "огласовка בֶ — какой звук", "he": "э", "opts": ["и", "о", "нет гласного", "э"]}, {"ru": "огласовка בֵ — какой звук", "he": "э", "opts": ["о", "э", "а", "и"]}, {"ru": "огласовка בִ — какой звук", "he": "и", "opts": ["э", "и", "а", "э"]}, {"ru": "огласовка בֹ — какой звук", "he": "о", "opts": ["о", "и", "э", "у"]}, {"ru": "огласовка בֻ — какой звук", "he": "у", "opts": ["э", "у", "э", "о"]}, {"ru": "огласовка בוּ — какой звук", "he": "у", "opts": ["у", "нет гласного", "а", "и"]}, {"ru": "огласовка בְ — какой звук", "he": "нет гласного", "opts": ["о", "нет гласного", "у", "э"]}], "alef_sounds": [{"ru": "звук буквы א", "he": "нет звука", "opts": ["нет звука", "к", "б / в", "х, в конце немая"]}, {"ru": "звук буквы ב", "he": "б / в", "opts": ["с", "х, в конце немая", "г", "б / в"]}, {"ru": "звук буквы ג", "he": "г", "opts": ["г", "т", "х, в конце немая", "р"]}, {"ru": "звук буквы ד", "he": "д", "opts": ["д", "л", "й / и", "з"]}, {"ru": "звук буквы ה", "he": "х, в конце немая", "opts": ["с", "х, в конце немая", "нет звука", "з"]}, {"ru": "звук буквы ו", "he": "в / о / у", "opts": ["в / о / у", "р", "с", "т"]}, {"ru": "звук буквы ז", "he": "з", "opts": ["н", "г", "з", "к / х"]}, {"ru": "звук буквы ח", "he": "х горловое", "opts": ["з", "к", "х горловое", "т"]}, {"ru": "звук буквы ט", "he": "т", "opts": ["в / о / у", "т", "б / в", "л"]}, {"ru": "звук буквы י", "he": "й / и", "opts": ["нет звука, горловая", "н", "ц", "й / и"]}], "alef_syllables": [{"ru": "прочитай מָ", "he": "ма", "opts": ["ма", "ло", "лу", "тэ"]}, {"ru": "прочитай מִ", "he": "ми", "opts": ["ми", "тэ", "ду", "ку"]}, {"ru": "прочитай מוּ", "he": "му", "opts": ["кэ", "до", "му", "ни"]}, {"ru": "прочитай מֶ", "he": "мэ", "opts": ["дэ", "мэ", "ки", "нэ"]}, {"ru": "прочитай מֹ", "he": "мо", "opts": ["ко", "рэ", "ди", "мо"]}, {"ru": "прочитай שָׁ", "he": "ша", "opts": ["ту", "тэ", "но", "ша"]}, {"ru": "прочитай שִׁ", "he": "ши", "opts": ["нэ", "ту", "до", "ши"]}, {"ru": "прочитай שׁוּ", "he": "шу", "opts": ["шу", "но", "ши", "ми"]}, {"ru": "прочитай שֶׁ", "he": "шэ", "opts": ["шэ", "на", "ду", "ри"]}, {"ru": "прочитай שֹׁ", "he": "шо", "opts": ["ла", "да", "ша", "шо"]}]};

const realFetch = window.fetch.bind(window);

window.fetch = async (path, opt) => {
  // Подменяем только вызовы API. Всё остальное — статику вроде
  // words.svg — пропускаем как есть: иначе разбор тела падал на
  // обычном GET, у которого тела нет.
  if (!String(path).startsWith("/api/")) return realFetch(path, opt);

  const b = JSON.parse(opt.body); let r = {};
  if (path.endsWith("/menu")) r = {
    topics: PT.map(([key,name,count]) => ({key,name,count})),
    grammar: [["adjectives","Прилагательные",10],["cardinals","Числительные",9]]
      .map(([key,name,count]) => ({key,name,count})),
    verbs: [["verbs","глаголы",75],["past","прошедшее время",693]]
      .map(([key,name,count]) => ({key,name,count})),
    alphabet: [{"key": "alef_names", "name": "названия букв", "count": 22}, {"key": "alef_sounds", "name": "звуки букв", "count": 22}, {"key": "alef_by_name", "name": "узнать букву по названию", "count": 22}, {"key": "alef_finals", "name": "конечные формы", "count": 5}, {"key": "alef_dotted", "name": "точка меняет звук", "count": 8}, {"key": "alef_niqqud", "name": "огласовки", "count": 9}, {"key": "alef_syllables", "name": "чтение слогов", "count": 40}],
    due: 91, weak: 42, anagram_modes: ["vocab","weak"] };
  else if (path.endsWith("/home")) r = {
    xp:158, level:5, at_level:27, need:64, streak:1, due:91, weak:42,
    answers:242, correct:181, learned:11,
    week: [["С",0],["Ч",0],["П",0],["С",0],["В",0],["П",0],["В",1]]
      .map(([l,on],i) => ({l, on:!!on, today:i===6})),
    word: {ru:"второй", he:"שֵׁנִי", reading:"шени", audio:null},
    name: PREVIEW_NAME,
    topics: PT.map(([key,name,total,seen,learned]) => ({key,name,total,seen,learned})),
    resume: {mode:"present", cat:null, label:"настоящее время",
      ru:"приближаться (לְהִתְקָרֵב) — жен. род, мн. число",
      he:"מִתְקָרְבוֹת", reading:"миткарвот", audio:null} };
  else if (path.endsWith("/round")) {
    // Раньше на любой режим отдавались словарные вопросы, и раздел
    // «Алфавит» показывал слова вместо букв. Теперь заглушка знает
    // про режимы alef_* и берёт их настоящие карточки.
    const al = ALEF[b.mode];
    // Знакомство: в предпросмотре показываем первые четыре слова темы.
    const intro = al
      ? al.slice(0, 4).map(q => ({ru:q.ru, main:q.he, gloss:q.ru,
          cat:b.mode, reading:"", audio:null}))
      : PW.slice(0, 4).map(([ru,he,reading]) => ({ru, main:he, gloss:ru,
          cat:"food", reading, audio:null}));
    r = al
      ? { label:b.mode, format:b.format, intro,
          questions: al.map(q => ({ru:q.ru, mode:b.mode, options:q.opts,
            letters:[...q.he.replace(/[\u0591-\u05C7]/g,"")]})) }
      : { label:"еда", format:b.format, intro,
          questions: PW.map(([ru,he],i) => ({ru, mode:"vocab",
            options:[he, PW[(i+1)%10][1], PW[(i+2)%10][1], PW[(i+3)%10][1]],
            letters:[...he.replace(/[\u0591-\u05C7]/g,"")]})) }; }
  else if (path.endsWith("/answer")) {
    const a = (ALEF[b.mode] || []).find(q => q.ru === b.ru);
    if (a){ const ok = b.answer === a.he;
      return { ok:true, status:200, json: async () => ({verdict: ok?"exact":"wrong",
        correct:ok, expected:a.he, reading:"", audio:null, memory:null}) }; }
    const c = PW.find(x => x[0]===b.ru) || PW[0];
    const right = b.answer === c[1];
    r = {verdict: right?"exact":"wrong", correct:right, expected:c[1], reading:c[2],
         audio:null, memory: right?null:"Второй раз на нём спотыкаешься."}; }
  else if (path.endsWith("/words")) r = { words: PW.map(([ru,he,reading],i) =>
      ({ru,he,reading, cat:"food", topic:"Еда",
        state: i<3?"learned":i<6?"learning":"new", fav:i===0, audio:null})),
    learned_box: 4 };
  else if (path.endsWith("/profile")) {
    if ("name" in b){                       // правка имени в предпросмотре
      PREVIEW_NAME = b.name
        ? {ru:"Даниил", heb:b.name, auto:"דניאל", guess:false, edited:true}
        : {ru:"Даниил", heb:"דניאל", auto:"דניאל", guess:false, edited:false};
    }
    r = {xp:158, level:5, at_level:27, need:64,
      streak:1, answers:242, correct:181, learned:11, favourites:1,
      voice:true, slow:false, daily:true, reactions:true, name:PREVIEW_NAME}; }
  else if (path.endsWith("/stats")) r = {total:242, correct:181, streak:1, due:91,
    by_mode:[{mode:"vocab",name:"слова",total:150,correct:120},
             {mode:"present",name:"настоящее время",total:92,correct:61}],
    weak: PW.slice(0,4).map(([ru,he,reading],i) => ({ru,he,reading,wrong:4-i,mode:"vocab"}))};
  else if (path.endsWith("/round_done")) r = {xp:163, level:5, at_level:32, need:64};
  return { ok:true, status:200, json: async () => r };
};
