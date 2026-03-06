// ggsql-grammar.js - Extends SQL grammar for Prism Code Editor with ggsql tokens.
//
// Grammar is derived from the TextMate grammar at posit-dev/ggsql:
// https://github.com/posit-dev/ggsql/blob/main/ggsql-vscode/syntaxes/ggsql.tmLanguage.json
//
// The content-hashed filename below may change when bslib updates prism-code-editor.
// To find the current import path, check:
//   {shiny_package}/www/shared/prism-code-editor/prism/languages/sql.js
// and copy the import path from the first line.

import { l as languages } from "../../index-C1_GGQ8y.js";

// Wait for SQL grammar to be loaded on demand by the code editor.
const waitForSql = () =>
  new Promise((resolve) => {
    if (languages.sql) return resolve(languages.sql);
    const check = setInterval(() => {
      if (languages.sql) {
        clearInterval(check);
        resolve(languages.sql);
      }
    }, 50);
    setTimeout(() => {
      clearInterval(check);
      resolve(null);
    }, 5000);
  });

const sqlGrammar = await waitForSql();
if (sqlGrammar) {
  // New ggsql-specific token definitions
  const ggsqlTokens = {
    "ggsql-keyword": /\b(?:VISUALISE|VISUALIZE|DRAW|MAPPING|REMAPPING|SETTING|FILTER|PARTITION|SCALE|FACET|PROJECT|LABEL|THEME|RENAMING|VIA|TO)\b/i,
    "ggsql-geom": /\b(?:point|line|path|bar|col|area|tile|polygon|ribbon|histogram|density|smooth|boxplot|violin|text|label|segment|arrow|hline|vline|abline|errorbar)\b/,
    "ggsql-scale-type": /\b(?:CONTINUOUS|DISCRETE|BINNED|ORDINAL|IDENTITY)\b/i,
    "ggsql-aesthetic": /\b(?:x|y|xmin|xmax|ymin|ymax|xend|yend|weight|color|colour|fill|stroke|opacity|size|shape|linetype|linewidth|width|height|family|fontface|hjust|vjust|panel|row|column|theta|radius|thetamin|thetamax|radiusmin|radiusmax|thetaend|radiusend|offset)\b/,
    "ggsql-theme": /\b(?:minimal|classic|gray|grey|bw|dark|light|void)\b/,
    "ggsql-project": /\b(?:cartesian|polar|flip|fixed|trans|map|quickmap)\b/,
    "ggsql-arrow": /=>/,
    // Broader function coverage: aggregate, window, datetime, string, math, conversion, conditional, JSON, list
    "function": /\b(?:abs|acos|any_value|approx_count_distinct|approx_percentile|array_agg|array_append|array_cat|array_contains|array_length|array_position|array_prepend|array_remove|array_replace|array_to_string|ascii|asin|atan|atan2|avg|bit_and|bit_length|bit_or|bit_xor|bool_and|bool_or|cardinality|case|cast|cbrt|ceil(?:ing)?|char|char_length|character_length|charindex|chr|coalesce|concat|concat_ws|convert|corr|cos|cot|count|covar_pop|covar_samp|cume_dist|current_date|current_time|current_timestamp|date|date_add|date_diff|date_format|date_part|date_sub|date_trunc|dateadd|datediff|datepart|day|dayname|dayofmonth|dayofweek|dayofyear|decode|degrees|dense_rank|div|encode|exp|extract|first|first_value|floor|format|from_base64|from_unixtime|generate_series|greatest|group_concat|hour|if(?:null)?|initcap|instr|json_agg|json_array|json_array_length|json_build_array|json_build_object|json_each|json_extract|json_extract_path|json_extract_path_text|json_object|json_object_agg|json_query|json_table|json_value|jsonb_agg|jsonb_array_elements|jsonb_build_array|jsonb_build_object|jsonb_extract_path|jsonb_object|jsonb_object_agg|lag|last|last_value|lcase|lead|least|left|len|length|list|list_agg|list_append|list_contains|list_position|list_prepend|list_slice|ln|locate|log|log10|log2|lower|lpad|ltrim|max|md5|median|mid|min|minute|mod|month|monthname|now|nth_value|ntile|nullif|octet_length|ord|overlay|parse_json|percent_rank|percentile_cont|percentile_disc|pi|position|pow(?:er)?|quarter|radians|rand|random|rank|regexp_extract|regexp_like|regexp_match|regexp_replace|regexp_split_to_array|regr_slope|repeat|replace|reverse|right|round|row_number|rpad|rtrim|second|sha|sha1|sha2|sign|sin|space|split|split_part|sqrt|stddev|stddev_pop|stddev_samp|str_to_date|strftime|string_agg|string_to_array|strpos|subdate|substr(?:ing)?|sum|sysdate|tan|time|timediff|timestamp|to_base64|to_char|to_date|to_json|to_number|to_timestamp|translate|trim|trunc(?:ate)?|try_cast|typeof|ucase|unnest|upper|user|var_pop|var_samp|variance|week|year|yearweek)(?=\s*\()/i,
  };

  // Rebuild grammar object with ggsql tokens checked before generic SQL tokens.
  // Prism checks tokens in object key order, so order matters.
  const ordered = {};

  // Greedy / high-priority tokens first
  for (const key of ["comment", "string", "identifier", "variable"]) {
    if (key in sqlGrammar) ordered[key] = sqlGrammar[key];
  }

  // ggsql-specific tokens
  Object.assign(ordered, ggsqlTokens);

  // Remaining SQL tokens
  for (const key of Object.keys(sqlGrammar)) {
    if (!(key in ordered)) ordered[key] = sqlGrammar[key];
  }

  // Update sqlGrammar in-place to preserve object identity used by Prism.
  for (const key of Object.keys(sqlGrammar)) {
    delete sqlGrammar[key];
  }
  Object.assign(sqlGrammar, ordered);
}
