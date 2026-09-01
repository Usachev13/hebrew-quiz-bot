// Линтер для static/app.html — ловит обращения к переменным, объявленным
// в чужой области видимости. Именно так сломался профиль: он читал
// `user`, объявленный внутри renderHome, и падал с ReferenceError.
// check_app.py такого не видит принципиально: он проверяет вызовы
// функций, а не переменные, а `node --check` смотрит только синтаксис.
//
//   npm install eslint
//   python3 -c "import re;h=open('static/app.html',encoding='utf-8').read();\
//     open('/tmp/app.js','w',encoding='utf-8').write(\
//     re.findall(r'<script>(.*?)</script>',h,re.S)[-1])"
//   npx eslint --config tools/eslint.config.mjs /tmp/app.js
export default [{
  languageOptions: {
    ecmaVersion: 2022,
    sourceType: "script",
    globals: {
      window:"readonly", document:"readonly", console:"readonly",
      fetch:"readonly", setTimeout:"readonly", setInterval:"readonly",
      requestAnimationFrame:"readonly", matchMedia:"readonly",
      Audio:"readonly", Image:"readonly", localStorage:"readonly",
      navigator:"readonly", performance:"readonly", Math:"readonly",
      JSON:"readonly", Date:"readonly", Set:"readonly", Map:"readonly",
      Array:"readonly", Object:"readonly", String:"readonly",
      Number:"readonly", Boolean:"readonly", Promise:"readonly",
      Intl:"readonly", URLSearchParams:"readonly", isNaN:"readonly",
      parseInt:"readonly", parseFloat:"readonly",
      encodeURIComponent:"readonly", alert:"readonly", confirm:"readonly",
      prompt:"readonly", Error:"readonly", RegExp:"readonly",
    },
  },
  rules: { "no-undef": "error", "no-redeclare": "error" },
}];
