import { l as languages } from "../../index-bkac8M6P.js";
languages.properties = {
  "comment": /^[ 	]*[#!].*/m,
  "value": {
    pattern: /(^[ 	]*(?:\\[^]|[^\\\s:=])+(?: *[=:] *(?! )| ))(?:\\[^]|[^\\\n])+/m,
    lookbehind: true,
    alias: "attr-value"
  },
  "key": {
    pattern: /^[ 	]*(?:\\[^]|[^\\\s:=])+(?= *[=:]| )/m,
    alias: "attr-name"
  },
  "punctuation": /[=:]/
};
//# sourceMappingURL=properties.js.map
