// ggsql-grammar.js - Extends SQL grammar for Prism Code Editor with ggsql tokens.
//
// Grammar derived from the TextMate grammar at posit-dev/ggsql:
// https://github.com/posit-dev/ggsql/blob/main/ggsql-vscode/syntaxes/ggsql.tmLanguage.json
//
// IMPORTANT: This dynamically imports from a content-hashed internal module of
// prism-code-editor. The filename (index-C1_GGQ8y.js) may change when bslib
// updates prism-code-editor. If syntax highlighting stops working after a bslib
// upgrade, check:
//   {shiny_package}/www/shared/prism-code-editor/prism/languages/sql.js
// and copy the hashed filename from the import on the first line.
(async () => {
  // Locate the prism-code-editor base URL from its script tag.
  var scriptEl = document.querySelector(
    'script[src*="prism-code-editor"][src$="index.js"]'
  );
  if (!scriptEl) return;

  var baseUrl = scriptEl.src.replace(/\/index\.js$/, "");

  // Import the GRAMMAR registry (not the languageMap from index.js).
  // The grammar registry is only exported from the internal hashed module.
  var grammarModule = await import(baseUrl + "/index-C1_GGQ8y.js");
  var languages = grammarModule.l;
  if (!languages) return;

  // Wait for SQL grammar to be loaded on demand by the code editor.
  var sqlGrammar = await new Promise(function (resolve) {
    if (languages.sql) return resolve(languages.sql);
    var check = setInterval(function () {
      if (languages.sql) {
        clearInterval(check);
        resolve(languages.sql);
      }
    }, 50);
    setTimeout(function () {
      clearInterval(check);
      resolve(null);
    }, 5000);
  });
  if (!sqlGrammar) return;

  // --- Extend the SQL grammar in-place with ggsql tokens ---

  // ggsql clause keywords — alias "keyword" so the theme styles them
  sqlGrammar["ggsql-keyword"] = {
    pattern: /\b(?:VISUALISE|VISUALIZE|DRAW|MAPPING|REMAPPING|SETTING|FILTER|PARTITION|SCALE|FACET|PROJECT|LABEL|THEME|RENAMING|VIA|TO)\b/i,
    alias: "keyword",
  };

  // Geom types (after DRAW)
  sqlGrammar["ggsql-geom"] = {
    pattern: /\b(?:point|line|path|bar|col|area|tile|polygon|ribbon|histogram|density|smooth|boxplot|violin|text|label|segment|arrow|hline|vline|abline|errorbar)\b/,
    alias: "builtin",
  };

  // Scale type modifiers
  sqlGrammar["ggsql-scale-type"] = {
    pattern: /\b(?:CONTINUOUS|DISCRETE|BINNED|ORDINAL|IDENTITY)\b/i,
    alias: "builtin",
  };

  // Aesthetic names
  sqlGrammar["ggsql-aesthetic"] = {
    pattern: /\b(?:x|y|xmin|xmax|ymin|ymax|xend|yend|weight|color|colour|fill|stroke|opacity|size|shape|linetype|linewidth|width|height|family|fontface|hjust|vjust|panel|row|column|theta|radius|thetamin|thetamax|radiusmin|radiusmax|thetaend|radiusend|offset)\b/,
    alias: "attr-name",
  };

  // Theme names
  sqlGrammar["ggsql-theme"] = {
    pattern: /\b(?:minimal|classic|gray|grey|bw|dark|light|void)\b/,
    alias: "class-name",
  };

  // Project types
  sqlGrammar["ggsql-project"] = {
    pattern: /\b(?:cartesian|polar|flip|fixed|trans|map|quickmap)\b/,
    alias: "class-name",
  };

  // Fat arrow operator (SETTING/LABEL/RENAMING clauses)
  sqlGrammar["ggsql-arrow"] = {
    pattern: /=>/,
    alias: "operator",
  };

  // Broader SQL function coverage: aggregate, window, datetime, string, math,
  // conversion, conditional, JSON, list (from TextMate grammar sql-functions)
  sqlGrammar["function"] =
    /\b(?:count|sum|avg|min|max|stddev|variance|array_agg|string_agg|group_concat|row_number|rank|dense_rank|ntile|lag|lead|first_value|last_value|nth_value|cume_dist|percent_rank|date_trunc|date_part|datepart|datename|dateadd|datediff|extract|now|current_date|current_time|current_timestamp|getdate|getutcdate|strftime|strptime|make_date|make_time|make_timestamp|concat|substring|substr|left|right|length|len|char_length|lower|upper|trim|ltrim|rtrim|replace|reverse|repeat|lpad|rpad|split_part|string_split|format|printf|regexp_replace|regexp_extract|regexp_matches|abs|ceil|ceiling|floor|round|trunc|truncate|mod|power|sqrt|exp|ln|log|log10|log2|sign|sin|cos|tan|asin|acos|atan|atan2|pi|degrees|radians|random|rand|cast|convert|coalesce|nullif|ifnull|isnull|nvl|try_cast|typeof|if|iff|iif|greatest|least|decode|json|json_extract|json_extract_path|json_extract_string|json_value|json_query|json_object|json_array|json_array_length|to_json|from_json|list|list_value|list_aggregate|array_length|unnest|generate_series|range|first|last)(?=\s*\()/i;

  // Reorder grammar so ggsql tokens are checked before generic SQL tokens.
  // Prism checks tokens in object key order.
  var ggsqlKeys = [
    "ggsql-keyword",
    "ggsql-geom",
    "ggsql-scale-type",
    "ggsql-aesthetic",
    "ggsql-theme",
    "ggsql-project",
    "ggsql-arrow",
  ];
  var ordered = {};

  // 1. Greedy/high-priority tokens first
  ["comment", "string", "identifier", "variable"].forEach(function (key) {
    if (key in sqlGrammar) ordered[key] = sqlGrammar[key];
  });

  // 2. ggsql-specific tokens
  ggsqlKeys.forEach(function (key) {
    if (key in sqlGrammar) ordered[key] = sqlGrammar[key];
  });

  // 3. Remaining SQL tokens
  Object.keys(sqlGrammar).forEach(function (key) {
    if (!(key in ordered)) ordered[key] = sqlGrammar[key];
  });

  // Update in-place to preserve the object identity Prism holds.
  Object.keys(sqlGrammar).forEach(function (key) {
    delete sqlGrammar[key];
  });
  Object.assign(sqlGrammar, ordered);
})();
