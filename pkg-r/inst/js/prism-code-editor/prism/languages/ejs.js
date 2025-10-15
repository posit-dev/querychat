import { l as languages, t as tokenize } from "../../index-bkac8M6P.js";
import { e as embeddedIn } from "../../templating-yZpuvMTN.js";
import "./javascript.js";
import "./markup.js";
languages.eta = languages.ejs = {
  "ejs": {
    pattern: /<%[^%][^]*?%>/,
    inside: {
      "comment": /^<%#[^]+/,
      "delimiter": {
        pattern: /^<%[-_=]?|[-_]?%>$/,
        alias: "punctuation"
      },
      "language-javascript": {
        pattern: /[^]+/,
        inside: "js"
      }
    }
  },
  "escape": /<%%|%%>/,
  [tokenize]: embeddedIn("html")
};
//# sourceMappingURL=ejs.js.map
