import { l as languages, r as rest } from "../../index-bkac8M6P.js";
import { c as clone, i as insertBefore } from "../../language-DPYOfXzt.js";
import { b as boolean } from "../../patterns-BwNIoKDQ.js";
import "./markup.js";
var vel = languages.velocity = clone(languages.html);
var string = {
  pattern: /"[^"]*"|'[^']*'/g,
  greedy: true
};
var punctuation = /[()[\]{}.,:]/;
var number = /\b\d+\b/;
var variable = {
  pattern: /(^|[^\\](?:\\\\)*)\$!?(?:[a-z][\w-]*(?:\([^)]*\))?(?:\.[a-z][\w-]*(?:\([^)]*\))?|\[[^\]]+\])*|\{[^}]+\})/i,
  lookbehind: true,
  inside: {
    "string": string,
    "function": {
      pattern: /([^\w-])[a-z][\w-]*(?=\()/,
      lookbehind: true
    },
    "number": number,
    "boolean": boolean,
    "punctuation": punctuation
  }
};
insertBefore(vel, "comment", {
  "unparsed": {
    pattern: /(^|[^\\])#\[\[[^]*?\]\]#/g,
    lookbehind: true,
    greedy: true,
    inside: {
      "punctuation": /^#\[\[|\]\]#$/
    }
  },
  "velocity-comment": [
    {
      pattern: /(^|[^\\])#\*[^]*?\*#/g,
      lookbehind: true,
      greedy: true,
      alias: "comment"
    },
    {
      pattern: /(^|[^\\])##.*/g,
      lookbehind: true,
      greedy: true,
      alias: "comment"
    }
  ],
  "directive": {
    pattern: /(^|[^\\](?:\\\\)*)#@?(?:[a-z][\w-]*|\{[a-z][\w-]*\})(?:\s*\((?:[^()]|\([^)]*\))*\))?/i,
    lookbehind: true,
    inside: {
      "keyword": {
        pattern: /^#@?(?:[a-z][\w-]*|\{[a-z][\w-]*\})|\bin\b/,
        inside: {
          "punctuation": /[{}]/
        }
      },
      "variable": variable,
      "string": string,
      "number": number,
      "boolean": boolean,
      "operator": /[!=<>]=?|[%/*+-]|&&|\|\||\.\.|\b(?:eq|[gl][et]|ne|not)\b/,
      "punctuation": punctuation
    }
  },
  "variable": variable
});
vel["tag"].inside["attr-value"][2].inside[rest] = vel;
//# sourceMappingURL=velocity.js.map
