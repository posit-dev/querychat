import { l as languages } from "../../index-bkac8M6P.js";
languages.roboconf = {
  "comment": /#.*/,
  "keyword": {
    "pattern": /(^|\s)(?:(?:external|import)\b|(?:facet|instance of)(?=[ 	]+[\w-]+[ 	]*\{))/,
    lookbehind: true
  },
  "component": {
    pattern: /[\w-]+(?=[ 	]*\{)/,
    alias: "variable"
  },
  "property": /[\w.-]+(?=[ 	]*:)/,
  "value": {
    pattern: /(=[ 	]*(?![ 	]))[^,;]+/,
    lookbehind: true,
    alias: "attr-value"
  },
  "optional": {
    pattern: /\(optional\)/,
    alias: "builtin"
  },
  "wildcard": {
    pattern: /(\.)\*/,
    lookbehind: true,
    alias: "operator"
  },
  "punctuation": /[{}.,:;=]/
};
//# sourceMappingURL=roboconf.js.map
