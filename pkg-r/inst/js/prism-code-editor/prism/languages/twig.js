import { l as languages, t as tokenize } from "../../index-bkac8M6P.js";
import { e as embeddedIn } from "../../templating-yZpuvMTN.js";
import "./markup.js";
languages.twig = {
  "twig": {
    pattern: /\{(?:#[^]*?#|%[^]*?%|\{[^]*?\})\}/,
    alias: "language-twig",
    inside: {
      "comment": /^\{#[^]+/,
      "tag-name": {
        pattern: /(^\{%-?\s*)\w+/,
        lookbehind: true,
        alias: "keyword"
      },
      "delimiter": {
        pattern: /^\{[{%]-?|-?[%}]\}$/,
        alias: "punctuation"
      },
      "string": {
        pattern: /(["'])(?:\\.|(?!\1)[^\\\n])*\1/,
        inside: {
          "punctuation": /^["']|["']$/
        }
      },
      "keyword": /\b(?:even|if|odd)\b/,
      "boolean": /\b(?:false|true|null)\b/,
      "number": /\b0x[a-fA-F\d]+|(?:\b\d+(?:\.\d*)?|\B\.\d+)(?:[Ee][+-]?\d+)?/,
      "operator": [
        {
          pattern: /(\s)(?:and|b-and|b-x?or|ends with|in|is|matches|not|or|same as|starts with)(?!\S)/,
          lookbehind: true
        },
        /[=<>]=?|!=|\*\*?|\/\/?|\?:?|[~%|+-]/
      ],
      "punctuation": /[()[\]{}.,:]/
    }
  },
  [tokenize]: embeddedIn("html")
};
//# sourceMappingURL=twig.js.map
