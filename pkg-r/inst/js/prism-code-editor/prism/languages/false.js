import { l as languages } from "../../index-bkac8M6P.js";
languages["false"] = {
  "comment": /\{[^}]*\}/,
  "string": {
    pattern: /"[^"]*"/g,
    greedy: true
  },
  "character-code": {
    pattern: /'[^]/,
    alias: "number"
  },
  "assembler-code": {
    pattern: /\d+`/,
    alias: "important"
  },
  "number": /\d+/,
  "operator": /[#$?'.,:;@\\_`~ßø%&|^!=>/*+-]/,
  "punctuation": /[[\]]/,
  "variable": /[a-z]/,
  "non-standard": {
    pattern: /[()<BDO®]/,
    alias: "bold"
  }
};
//# sourceMappingURL=false.js.map
