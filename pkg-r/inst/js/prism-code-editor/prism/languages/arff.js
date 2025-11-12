import { l as languages } from "../../index-bkac8M6P.js";
languages.arff = {
  "comment": /%.*/,
  "string": {
    pattern: /(["'])(?:\\.|(?!\1)[^\\\n])*\1/g,
    greedy: true
  },
  "keyword": /@(?:attribute|data|end|relation)\b/i,
  "number": /\b\d+(?:\.\d+)?\b/,
  "punctuation": /[{},]/
};
//# sourceMappingURL=arff.js.map
