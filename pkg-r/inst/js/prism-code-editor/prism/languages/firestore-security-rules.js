import { l as languages } from "../../index-bkac8M6P.js";
import { e as extend, i as insertBefore } from "../../language-DPYOfXzt.js";
import "./clike.js";
var firestore = languages["firestore-security-rules"] = extend("clike", {
  "comment": /\/\/.*/,
  "keyword": /\b(?:allow|function|if|match|null|return|rules_version|service)\b/,
  "operator": /&&|\|\||[!=<>]=?|[%/*+-]|\bi[ns]\b/
});
delete firestore["class-name"];
insertBefore(firestore, "keyword", {
  "path": {
    pattern: /(^|[\s(),])(?:\/(?:[\w\xa0-\uffff]+|\{[\w\xa0-\uffff]+(?:=\*\*)?\}|\$\([\w\xa0-\uffff.]+\)))+/g,
    lookbehind: true,
    greedy: true,
    inside: {
      "variable": {
        pattern: /\{[\w\xa0-\uffff]+(?:=\*\*)?\}|\$\([\w\xa0-\uffff.]+\)/,
        inside: {
          "operator": /=/,
          "keyword": /\*\*/,
          "punctuation": /[(){}.$]/
        }
      },
      "punctuation": /\//
    }
  },
  "method": {
    // to make the pattern shorter, the actual method names are omitted
    pattern: /(\ballow\s+)[a-z]+(?:\s*,\s*[a-z]+)*(?=\s*[:;])/,
    lookbehind: true,
    alias: "builtin",
    inside: {
      "punctuation": /,/
    }
  }
});
//# sourceMappingURL=firestore-security-rules.js.map
