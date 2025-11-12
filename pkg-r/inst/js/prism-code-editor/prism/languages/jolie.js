import { l as languages } from "../../index-bkac8M6P.js";
import { c as clikeComment, b as boolean, d as clikePunctuation } from "../../patterns-BwNIoKDQ.js";
languages.jolie = {
  "comment": clikeComment(),
  "string": {
    pattern: /(^|[^\\])"(?:\\[^]|[^\\"])*"/g,
    lookbehind: true,
    greedy: true
  },
  "class-name": {
    pattern: /((?:\b(?:as|courier|embed|in|inputPort|outputPort|service)\b|@)[ 	]*)\w+/,
    lookbehind: true
  },
  "aggregates": {
    pattern: /(\bAggregates\s*:\s*)(?:\w+(?:\s+with\s+\w+)?\s*,\s*)*\w+(?:\s+with\s+\w+)?/,
    lookbehind: true,
    inside: {
      "keyword": /\bwith\b/,
      "class-name": /\w+/,
      "punctuation": /,/
    }
  },
  "redirects": {
    pattern: /(\bRedirects\s*:\s*)(?:\w+\s*=>\s*\w+\s*,\s*)*(?:\w+\s*=>\s*\w+)/,
    lookbehind: true,
    inside: {
      "punctuation": /,/,
      "class-name": /\w+/,
      "operator": /=>/
    }
  },
  "property": /\b(?:Aggregates|[Ii]nterfaces|Java|Javascript|Jolie|[Ll]ocation|OneWay|[Pp]rotocol|Redirects|RequestResponse)\b(?=[ 	]*:)/,
  "keyword": /\b(?:as|cH|comp|concurrent|constants|courier|csets?|default|define|else|embed|embedded|execution|exit|extender|for|foreach|forward|from|global|if|import|in|include|init|inputPort|install|instanceof|interface|is_defined|linkIn|linkOut|main|new|nullProcess|outputPort|over|private|provide|public|scope|sequential|service|single|spawn|synchronized|this|throws?|type|undef|until|while|with)\b/,
  "boolean": boolean,
  "function": /\b[a-z_]\w*(?=[ 	]*[@(])/i,
  "number": /(?:\b\d+(?:\.\d*)?|\B\.\d+)(?:e[+-]?\d+)?l?/i,
  "operator": /--|\+\+|&&|\|\||->|<<|[!=<>*+-]=?|[%|^@/?]/,
  "punctuation": clikePunctuation,
  "builtin": /\b(?:Byte|any|bool|char|double|enum|float|int|length|long|ranges|regex|string|undefined|void)\b/
};
//# sourceMappingURL=jolie.js.map
