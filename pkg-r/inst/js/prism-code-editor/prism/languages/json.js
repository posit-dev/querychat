import { l as languages } from "../../index-bkac8M6P.js";
import { c as clikeComment, b as boolean } from "../../patterns-BwNIoKDQ.js";
languages.webmanifest = languages.json = {
  "property": {
    pattern: /"(?:\\.|[^\\\n"])*"(?=\s*:)/g,
    greedy: true
  },
  "string": {
    pattern: /"(?:\\.|[^\\\n"])*"/g,
    greedy: true
  },
  "comment": clikeComment(),
  "number": /-?\b\d+(?:\.\d+)?(?:e[+-]?\d+)?\b/i,
  "operator": /:/,
  "punctuation": /[[\]{},]/,
  "boolean": boolean,
  "null": {
    pattern: /\bnull\b/,
    alias: "keyword"
  }
};
//# sourceMappingURL=json.js.map
