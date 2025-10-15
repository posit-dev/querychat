import { l as languages } from "../../index-bkac8M6P.js";
import { i as insertBefore, e as extend } from "../../language-DPYOfXzt.js";
import "./php.js";
import "./javadoclike.js";
insertBefore(
  languages.phpdoc = extend("javadoclike", {
    "parameter": {
      pattern: /(@(?:global|param|property(?:-read|-write)?|var)\s+(?:(?:\b[a-zA-Z]\w*|[|\\[\]])+\s+)?)\$\w+/,
      lookbehind: true
    }
  }),
  "keyword",
  {
    "class-name": [
      {
        pattern: /(@(?:global|package|param|property(?:-read|-write)?|return|subpackage|throws|var)\s+)(?:\b[a-zA-Z]\w*|[|\\[\]])+/,
        lookbehind: true,
        inside: {
          "keyword": /\b(?:array|bool|boolean|callback|double|false|true|float|int|integer|mixed|null|object|resource|self|string|void)\b/,
          "punctuation": /[|\\()[\]]/
        }
      }
    ]
  }
);
//# sourceMappingURL=phpdoc.js.map
