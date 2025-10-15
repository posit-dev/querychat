import { l as languages } from "../../index-bkac8M6P.js";
languages.shortcode = languages.bbcode = {
  "tag": {
    pattern: /\[\/?[^\s=\]]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'\]=]+))?(?:\s+[^\s=\]]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'\]=]+))*\s*\]/,
    inside: {
      "punctuation": /^\[\/?|\]$/,
      "attr-value": {
        pattern: /(=\s*)(?:"[^"]*"|'[^']*'|\S+)/,
        lookbehind: true,
        inside: {
          "punctuation": /^["']|["']$/
        }
      },
      "attr-equals": /=/,
      "tag": /^\S+/,
      "attr-name": /\S+/
    }
  }
};
//# sourceMappingURL=bbcode.js.map
