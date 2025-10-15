import { l as languages } from "../../index-bkac8M6P.js";
import { c as clikeComment } from "../../patterns-BwNIoKDQ.js";
var statement = {
  pattern: /[^]+/
};
statement.inside = languages.mel = {
  "comment": clikeComment(),
  "code": {
    pattern: /`(?:\\.|[^\\`])*`/g,
    greedy: true,
    alias: "italic",
    inside: {
      "delimiter": {
        pattern: /^`|`$/,
        alias: "punctuation"
      },
      "statement": statement
    }
  },
  "string": {
    pattern: /"(?:\\.|[^\\\n"])*"/g,
    greedy: true
  },
  "variable": /\$\w+/,
  "number": /\b0x[a-fA-F\d]+\b|\b\d+(?:\.\d*)?|\B\.\d+/,
  "flag": {
    pattern: /-[^\d\W]\w*/,
    alias: "operator"
  },
  "keyword": /\b(?:break|case|continue|default|do|else|float|for|global|if|int?|matrix|proc|return|string|switch|vector|while)\b/,
  "function": {
    pattern: /((?:^|[{;])[ 	]*)[a-z_]\w*\b(?!\s*(?:\.(?!\.)|[[{=]))|\b[a-z_]\w*(?=[ 	]*\()/img,
    lookbehind: true,
    greedy: true
  },
  "tensor-punctuation": {
    pattern: /<<|>>/,
    alias: "punctuation"
  },
  "operator": /--|\+\+|&&|\|\||[!=<>/*+-]=?|[%^]/,
  "punctuation": /[()[\]{}.,:;?]/
};
//# sourceMappingURL=mel.js.map
