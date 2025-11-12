import { l as languages } from "../../index-bkac8M6P.js";
languages.ebnf = {
  "comment": /\(\*[^]*?\*\)/,
  "string": {
    pattern: /"[^\n"]*"|'[^\n']*'/g,
    greedy: true
  },
  "special": {
    pattern: /\?[^\n?]*\?/g,
    greedy: true,
    alias: "class-name"
  },
  "definition": {
    pattern: /^([ 	]*)[a-z]\w*(?:[ 	]+[a-z]\w*)*(?=\s*=)/im,
    lookbehind: true,
    alias: "rule keyword"
  },
  "rule": /\b[a-z]\w*(?:[ 	]+[a-z]\w*)*\b/i,
  "punctuation": /\([:/]|[:/]\)|[()[\]{}.,;]/,
  "operator": /[|!=/*-]/
};
//# sourceMappingURL=ebnf.js.map
