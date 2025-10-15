import { l as languages, t as tokenize } from "../../index-bkac8M6P.js";
import { e as embeddedIn } from "../../templating-yZpuvMTN.js";
import "./markup.js";
import "./ruby.js";
languages.erb = {
  "erb": {
    pattern: /<%=?(?:[^\n]|\n(?!=begin)|\n=begin\s(?:[^\n]|\n(?!=end))*\n=end)+?%>/,
    inside: {
      "delimiter": {
        pattern: /^<%=?|%>$/,
        alias: "punctuation"
      },
      "ruby": {
        pattern: /\s*\S[^]*/,
        alias: "language-ruby",
        inside: "ruby"
      }
    }
  },
  [tokenize]: embeddedIn("html")
};
//# sourceMappingURL=erb.js.map
