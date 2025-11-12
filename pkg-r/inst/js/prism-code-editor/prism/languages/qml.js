import { l as languages } from "../../index-bkac8M6P.js";
import { c as clikeComment } from "../../patterns-BwNIoKDQ.js";
import { n as nested, a as re } from "../../shared-DKTvH67n.js";
import "./javascript.js";
var jsExpr = nested(`(?:[^\\\\()[\\]{}"'/]|"(?:\\\\.|[^\\\\
"])*"|'(?:\\\\.|[^\\\\
'])*'|/(?![*/])|//.*(?!.)|/\\*(?:[^*]|\\*(?!/))*\\*/|\\(<self>*\\)|\\[<self>*\\]|\\{<self>*\\}|\\\\[\\s\\S])`, 2);
languages.qml = {
  "comment": clikeComment(),
  "javascript-function": {
    pattern: re("((?:^|;)[ 	]*)function\\s+(?!\\d)(?:(?!\\s)[$\\w\\xa0-\\uffff])+\\s*\\(<0>*\\)\\s*\\{<0>*\\}", [jsExpr], "mg"),
    lookbehind: true,
    greedy: true,
    alias: "language-javascript",
    inside: languages.js
  },
  "class-name": {
    pattern: /((?:^|[:;])[ 	]*)(?!\d)\w+(?=[ 	]*\{|[ 	]+on\b)/m,
    lookbehind: true
  },
  "property": [
    {
      pattern: /((?:^|[;{])[ 	]*)(?!\d)\w+(?:\.\w+)*(?=[ 	]*:)/m,
      lookbehind: true
    },
    {
      pattern: /((?:^|[;{])[ 	]*)property[ 	]+(?!\d)\w+(?:\.\w+)*[ 	]+(?!\d)\w+(?:\.\w+)*(?=[ 	]*:)/m,
      lookbehind: true,
      inside: {
        "keyword": /^property/,
        "property": /\w+(?:\.\w+)*/
      }
    }
  ],
  "javascript-expression": {
    pattern: re("(:[ 	]*)(?![\\s;}[])(?:(?!$|[;}])<0>)+", [jsExpr], "mg"),
    lookbehind: true,
    greedy: true,
    alias: "language-javascript",
    inside: languages.js
  },
  "string": {
    pattern: /"(?:\\.|[^\\\n"])*"/g,
    greedy: true
  },
  "keyword": /\b(?:as|import|on)\b/,
  "punctuation": /[[\]{},:;]/
};
//# sourceMappingURL=qml.js.map
