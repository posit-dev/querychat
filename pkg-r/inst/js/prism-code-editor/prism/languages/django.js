import { l as languages, t as tokenize } from "../../index-bkac8M6P.js";
import { d as clikePunctuation } from "../../patterns-BwNIoKDQ.js";
import { e as embeddedIn } from "../../templating-yZpuvMTN.js";
import "./markup.js";
languages.jinja2 = languages.django = {
  "django": {
    pattern: /\{(?:\{[^]*?\}|%[^]*?%|#[^]*?#)\}/,
    alias: "language-django",
    inside: {
      "comment": /^\{#[^]+/,
      "tag": {
        pattern: /(^\{%[+-]?\s*)\w+/,
        lookbehind: true,
        alias: "keyword"
      },
      "delimiter": {
        pattern: /^\{[{%][+-]?|[+-]?[}%]\}$/,
        alias: "punctuation"
      },
      "string": {
        pattern: /(["'])(?:\\.|(?!\1)[^\\\n])*\1/g,
        greedy: true
      },
      "filter": {
        pattern: /(\|)\w+/,
        lookbehind: true,
        alias: "function"
      },
      "test": {
        pattern: /(\bis\s+(?:not\s+)?)(?!not\b)\w+/,
        lookbehind: true,
        alias: "function"
      },
      "function": /\b(?!\d)\w+(?=\s*\()/,
      "keyword": /\b(?:and|as|by|else|f?or|i[fns]|import|loop|not|recursive|with|without)\b/,
      "operator": /!=|\*\*=?|\/\/=?|<>|>>|<<|[%=<>/*+-]=?|[&|^~]/,
      "number": /\b\d+(?:\.\d+)?\b/,
      "boolean": /[Ff]alse|[Nn]one|[Tt]rue/,
      "variable": /\w+/,
      "punctuation": clikePunctuation
    }
  },
  [tokenize]: embeddedIn("html")
};
//# sourceMappingURL=django.js.map
