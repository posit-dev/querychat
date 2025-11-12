import { l as languages } from "../../index-bkac8M6P.js";
import { e as extend } from "../../language-DPYOfXzt.js";
import { a as clikeString } from "../../patterns-BwNIoKDQ.js";
import "./json.js";
var string = clikeString();
languages.json5 = extend("json", {
  "property": [
    RegExp(string.pattern.source + "(?=\\s*:)"),
    {
      pattern: /(?!\d)(?:(?!\s)[$\w\xa0-\uffff])+(?=\s*:)/,
      alias: "unquoted"
    }
  ],
  "string": string,
  "number": /[+-]?\b(?:NaN|Infinity|0x[a-fA-F\d]+)\b|[+-]?(?:\b\d+(?:\.\d*)?|\B\.\d+)(?:[eE][+-]?\d+\b)?/
});
//# sourceMappingURL=json5.js.map
