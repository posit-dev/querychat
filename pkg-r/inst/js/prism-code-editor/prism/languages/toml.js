import { l as languages } from "../../index-bkac8M6P.js";
import { b as boolean } from "../../patterns-BwNIoKDQ.js";
import { a as re } from "../../shared-DKTvH67n.js";
var insertKey = (pattern) => re(pattern, [`(?:[\\w-]+|'[^
']*'|"(?:\\\\.|[^\\\\"
])*")`], "mg");
languages.toml = {
  "comment": {
    pattern: /#.*/g,
    greedy: true
  },
  "table": {
    pattern: insertKey("(^[ 	]*\\[\\s*(?:\\[\\s*)?)<0>(?:\\s*\\.\\s*<0>)*(?=\\s*\\])"),
    lookbehind: true,
    greedy: true,
    alias: "class-name"
  },
  "key": {
    pattern: insertKey("(^[ 	]*|[{,]\\s*)<0>(?:\\s*\\.\\s*<0>)*(?=\\s*=)"),
    lookbehind: true,
    greedy: true,
    alias: "property"
  },
  "string": {
    pattern: /"""(?:\\[^]|[^\\])*?"""|'''[^]*?'''|'[^\n']*'|"(?:\\.|[^\\\n"])*"/g,
    greedy: true
  },
  "date": {
    // Offset Date-Time, Local Date-Time, Local Date, Local Time
    pattern: /\b(?:\d{4}-\d\d-\d\d(?:[t\s]\d\d:\d\d:\d\d(?:\.\d+)?(?:z|[+-]\d\d:\d\d)?)?|\d\d:\d\d:\d\d(?:\.\d+)?)\b/i,
    alias: "number"
  },
  "number": /(?:\b0(?:x[a-zA-Z\d]+(?:_[a-zA-Z\d]+)*|o[0-7]+(?:_[0-7]+)*|b[10]+(?:_[10]+)*))\b|[+-]?\b\d+(?:_\d+)*(?:\.\d+(?:_\d+)*)?(?:[eE][+-]?\d+(?:_\d+)*)?\b|[+-]?\b(?:inf|nan)\b/,
  "boolean": boolean,
  "punctuation": /[[\]{}.,=]/
};
//# sourceMappingURL=toml.js.map
