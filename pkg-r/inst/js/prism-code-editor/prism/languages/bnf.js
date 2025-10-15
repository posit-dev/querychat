import { l as languages } from "../../index-bkac8M6P.js";
languages.rbnf = languages.bnf = {
  "string": /"[^\n"]*"|'[^\n']*'/,
  "definition": {
    pattern: /<[^<>\n	]+>(?=\s*::=)/,
    alias: "rule keyword",
    inside: {
      "punctuation": /^<|>$/
    }
  },
  "rule": {
    pattern: /<[^<>\n	]+>/,
    inside: {
      "punctuation": /^<|>$/
    }
  },
  "operator": /::=|[|()[\]{}*+?]|\.{3}/
};
//# sourceMappingURL=bnf.js.map
