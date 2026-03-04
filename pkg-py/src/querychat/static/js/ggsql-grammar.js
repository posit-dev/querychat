// ggsql-grammar.js - Extends SQL grammar for Prism Code Editor with ggsql keywords.
(async () => {
  const scriptEl = document.querySelector(
    'script[src*="prism-code-editor"][src$="index.js"]'
  );
  if (!scriptEl) return;

  const baseUrl = scriptEl.src.replace(/\/index\.js$/, "");
  const indexModule = await import(baseUrl + "/index.js");
  const languages = indexModule.languages || indexModule.l;
  if (!languages) return;

  // Wait for SQL grammar to be loaded (loaded on demand by code editor)
  const waitForSql = () =>
    new Promise((resolve) => {
      if (languages.sql) return resolve(languages.sql);
      const check = setInterval(() => {
        if (languages.sql) {
          clearInterval(check);
          resolve(languages.sql);
        }
      }, 50);
      setTimeout(() => { clearInterval(check); resolve(null); }, 5000);
    });

  const sqlGrammar = await waitForSql();
  if (!sqlGrammar) return;

  // Extend SQL grammar in-place with ggsql keywords
  const existingKeyword = sqlGrammar.keyword;
  if (existingKeyword instanceof RegExp) {
    const src = existingKeyword.source;
    const ggsqlKeywords = "VISUALISE|DRAW|LABEL|FACET|SCALE|THEME";
    const newSrc = src.replace(/\)\\b/, `|${ggsqlKeywords})\\b`);
    sqlGrammar.keyword = new RegExp(newSrc, existingKeyword.flags);
  }
})();
