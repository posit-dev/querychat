import { l as languages } from "../../index-bkac8M6P.js";
import { c as clikeComment, a as clikeString, b as boolean, e as clikeNumber, d as clikePunctuation } from "../../patterns-BwNIoKDQ.js";
languages.clike = {
  "comment": clikeComment(),
  "string": clikeString(),
  "class-name": {
    pattern: /(\b(?:class|extends|implements|instanceof|interface|new|trait)\s+|\bcatch\s+\()[\w.\\]+/i,
    lookbehind: true,
    inside: {
      "punctuation": /[.\\]/
    }
  },
  "keyword": /\b(?:break|catch|continue|do|else|finally|for|function|if|in|instanceof|new|null|return|throw|try|while)\b/,
  "boolean": boolean,
  "function": /\b\w+(?=\()/,
  "number": clikeNumber,
  "operator": /[!=]==|[!=<>]=?|--?|\+\+?|&&?|\|\|?|[?*/~^%]/,
  "punctuation": clikePunctuation
};
//# sourceMappingURL=clike.js.map
