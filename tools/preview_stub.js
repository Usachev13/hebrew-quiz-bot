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

window.fetch = async (path, opt) => {
  const b = JSON.parse(opt.body); let r = {};
  if (path.endsWith("/menu")) r = {
    topics: PT.map(([key,name,count]) => ({key,name,count})),
    grammar: [["adjectives","Прилагательные",10],["cardinals","Числительные",9]]
      .map(([key,name,count]) => ({key,name,count})),
    verbs: [["verbs","глаголы",75],["past","прошедшее время",693]]
      .map(([key,name,count]) => ({key,name,count})),
    alphabet: [["alef_names","названия букв",22]].map(([key,name,count]) => ({key,name,count})),
    due: 91, weak: 42, anagram_modes: ["vocab","weak"] };
  else if (path.endsWith("/home")) r = {
    xp:158, level:5, at_level:27, need:64, streak:1, due:91, weak:42,
    answers:242, correct:181, learned:11,
    week: [["С",0],["Ч",0],["П",0],["С",0],["В",0],["П",0],["В",1]]
      .map(([l,on],i) => ({l, on:!!on, today:i===6})),
    word: {ru:"второй", he:"שֵׁנִי", reading:"шени", audio:null},
    topics: PT.map(([key,name,total,seen,learned]) => ({key,name,total,seen,learned})),
    resume: {mode:"present", cat:null, label:"настоящее время",
      ru:"приближаться (לְהִתְקָרֵב) — жен. род, мн. число",
      he:"מִתְקָרְבוֹת", reading:"миткарвот", audio:null} };
  else if (path.endsWith("/round")) r = { label:"еда", format:b.format,
    questions: PW.map(([ru,he],i) => ({ru, mode:"vocab",
      options:[he, PW[(i+1)%10][1], PW[(i+2)%10][1], PW[(i+3)%10][1]],
      letters:[...he.replace(/[\u0591-\u05C7]/g,"")]})) };
  else if (path.endsWith("/answer")) { const c = PW.find(x => x[0]===b.ru) || PW[0];
    const right = b.answer === c[1];
    r = {verdict: right?"exact":"wrong", correct:right, expected:c[1], reading:c[2],
         audio:null, memory: right?null:"Второй раз на нём спотыкаешься."}; }
  else if (path.endsWith("/words")) r = { words: PW.map(([ru,he,reading],i) =>
      ({ru,he,reading, cat:"food", topic:"Еда",
        state: i<3?"learned":i<6?"learning":"new", fav:i===0, audio:null})),
    learned_box: 4 };
  else if (path.endsWith("/profile")) r = {xp:158, level:5, at_level:27, need:64,
    streak:1, answers:242, correct:181, learned:11, favourites:1,
    voice:true, slow:false, daily:true, reactions:true};
  else if (path.endsWith("/stats")) r = {total:242, correct:181, streak:1, due:91,
    by_mode:[{mode:"vocab",name:"слова",total:150,correct:120},
             {mode:"present",name:"настоящее время",total:92,correct:61}],
    weak: PW.slice(0,4).map(([ru,he,reading],i) => ({ru,he,reading,wrong:4-i,mode:"vocab"}))};
  else if (path.endsWith("/round_done")) r = {xp:163, level:5, at_level:32, need:64};
  return { ok:true, status:200, json: async () => r };
};
