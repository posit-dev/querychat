import { l as languages, t as tokenize } from "../../index-bkac8M6P.js";
import { e as embeddedIn } from "../../templating-yZpuvMTN.js";
import "./markup.js";
import "./lua.js";
languages.etlua = {
  "etlua": {
    pattern: /<%[^]+?%>/,
    inside: {
      "delimiter": {
        pattern: /^<%[=-]?|-?%>$/,
        alias: "punctuation"
      },
      "language-lua": {
        pattern: /[^]+/,
        inside: "lua"
      }
    }
  },
  [tokenize]: embeddedIn("html")
};
//# sourceMappingURL=etlua.js.map
