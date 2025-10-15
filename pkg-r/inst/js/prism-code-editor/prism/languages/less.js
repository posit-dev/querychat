import { l as languages } from "../../index-bkac8M6P.js";
import { i as insertBefore, e as extend } from "../../language-DPYOfXzt.js";
import { c as clikeComment } from "../../patterns-BwNIoKDQ.js";
import "./css.js";
insertBefore(
  languages.less = extend("css", {
    "comment": clikeComment(),
    "atrule": {
      pattern: /@[\w-](?:\((?:[^(){}]|\([^(){}]*\))*\)|[^(){};\s]|\s+(?!\s))*?(?=\s*\{)/,
      inside: {
        "punctuation": /[():]/
      }
    },
    // selectors and mixins are considered the same
    "selector": {
      pattern: /(?:@\{[\w-]+\}|[^{};\s@])(?:@\{[\w-]+\}|\((?:[^(){}]|\([^(){}]*\))*\)|[^(){};@\s]|\s+(?!\s))*?(?=\s*\{)/,
      inside: {
        // mixin parameters
        "variable": /@+[\w-]+/
      }
    },
    "property": /(?:@\{[\w-]+\}|[\w-])+(?:\+_?)?(?=\s*:)/,
    "operator": /[/*+-]/
  }),
  "property",
  {
    "variable": [
      // Variable declaration (the colon must be consumed!)
      {
        pattern: /@[\w-]+\s*:/,
        inside: {
          "punctuation": /:/
        }
      },
      // Variable usage
      /@@?[\w-]+/
    ],
    "mixin-usage": {
      pattern: /([{;]\s*)[.#](?!\d)[\w-].*?(?=[(;])/,
      lookbehind: true,
      alias: "function"
    }
  }
);
//# sourceMappingURL=less.js.map
