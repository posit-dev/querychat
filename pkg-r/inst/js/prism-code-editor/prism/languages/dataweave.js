import { l as languages } from "../../index-bkac8M6P.js";
import { c as clikeComment, b as boolean } from "../../patterns-BwNIoKDQ.js";
languages.dataweave = {
  "url": /\b[a-zA-Z]+:\/\/[\w/:.?=&-]+|\burn:[\w:.?=&-]+/,
  "property": {
    pattern: /(?:\b\w+#)?(?:"(?:\\.|[^\\\n"])*"|\b\w+)(?=\s*[:@])/g,
    greedy: true
  },
  "string": {
    pattern: /(["'`])(?:\\[^]|(?!\1)[^\\])*\1/g,
    greedy: true
  },
  "mime-type": /\b(?:application|audio|image|multipart|text|video)\/[\w+-]+/,
  "date": {
    pattern: /\|[\w:+-]+\|/g,
    greedy: true
  },
  "comment": clikeComment(),
  "regex": {
    pattern: /\/(?:[^\\\n/]|\\[^\n])+\//g,
    greedy: true
  },
  "keyword": /\b(?:and|as|at|case|do|else|fun|if|input|is|match|not|ns|null|or|output|type|unless|update|using|var)\b/,
  "function": /\b[a-z_]\w*(?=\s*\()/i,
  "number": /-?\b\d+(?:\.\d+)?(?:e[+-]?\d+)?\b/i,
  "punctuation": /[()[\]{}.,:;@]/,
  "operator": /<<|>>|->|[~!=<>]=?|--?-?|\+\+?|\?/,
  "boolean": boolean
};
//# sourceMappingURL=dataweave.js.map
