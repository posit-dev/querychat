import { l as languages } from "../../index-bkac8M6P.js";
languages.javadoclike = {
  "parameter": {
    pattern: /(^[ 	]*(?:\/{3}|\*|\/\*\*)\s*@(?:arg|arguments|param)\s+)\w+/m,
    lookbehind: true
  },
  "keyword": {
    // keywords are the first word in a line preceded be an `@` or surrounded by curly braces.
    // @word, {@word}
    pattern: /(^[ 	]*(?:\/{3}|\*|\/\*\*)\s*|\{)@[a-z][a-zA-Z-]+\b/m,
    lookbehind: true
  },
  "punctuation": /[{}]/
};
//# sourceMappingURL=javadoclike.js.map
