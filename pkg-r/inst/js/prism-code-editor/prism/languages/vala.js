import { l as languages, r as rest } from "../../index-bkac8M6P.js";
import { c as clikeComment, a as clikeString, b as boolean, d as clikePunctuation } from "../../patterns-BwNIoKDQ.js";
languages.vala = {
  "comment": clikeComment(),
  "raw-string": {
    pattern: /"""[^]*?"""/g,
    greedy: true,
    alias: "string"
  },
  "template-string": {
    pattern: /@"[^"]*"/g,
    greedy: true,
    inside: {
      "interpolation": {
        pattern: /\$(?:\([^)]*\)|[a-zA-Z]\w*)/,
        inside: {
          "delimiter": {
            pattern: /^\$\(?|\)$/,
            alias: "punctuation"
          },
          [rest]: "vala"
        }
      },
      "string": /[^]+/
    }
  },
  "string": clikeString(),
  // Classes copied from prism-csharp
  "class-name": [
    {
      // (Foo bar, Bar baz)
      pattern: /\b[A-Z]\w*(?:\.\w+)*\b(?=(?:\?\s+|\*?\s+\*?)\w)/,
      inside: {
        punctuation: /\./
      }
    },
    {
      // [Foo]
      pattern: /(\[)[A-Z]\w*(?:\.\w+)*\b/,
      lookbehind: true,
      inside: {
        punctuation: /\./
      }
    },
    {
      // class Foo : Bar
      pattern: /(\b(?:class|interface)\s+[A-Z]\w*(?:\.\w+)*\s*:\s*)[A-Z]\w*(?:\.\w+)*\b/,
      lookbehind: true,
      inside: {
        punctuation: /\./
      }
    },
    {
      // class Foo
      pattern: /((?:\b(?:class|enum|interface|new|struct)\s+)|(?:catch\s+\())[A-Z]\w*(?:\.\w+)*\b/,
      lookbehind: true,
      inside: {
        punctuation: /\./
      }
    }
  ],
  "regex": {
    pattern: /\/(?:\[(?:\\.|[^\\\n\]])*\]|\\.|[^/\\[\n])+\/[imsx]{0,4}(?=\s*(?:$|[\n,.;})\]]))/g,
    greedy: true,
    inside: {
      "regex-flags": /\w+$/,
      "regex-delimiter": /^\/|\/$/,
      "regex-source": {
        pattern: /[^]+/,
        alias: "language-regex",
        inside: "regex"
      }
    }
  },
  "keyword": /\b(?:abstract|as|assert|async|[bc]ase|bool|break|catch|class|const|construct|continue|default|delegate|delete|do|double|dynamic|else|ensures|enum|errordomain|extern|finally|float|for|foreach|[gs]et|i[fns]|inline|interface|internal|lock|namespace|new|null|out|override|owned|params|private|protected|public|ref|requires|return|signal|sizeof|ss?ize_t|static|string|struct|switch|this|throws?|try|typeof|u?char|u?int(?:8|16|32|64)?|u?long|unichar|unowned|u?short|using|value|var|virtual|void|volatile|weak|while|yield)\b/i,
  "boolean": boolean,
  "function": /\b\w+(?=\s*\()/,
  "number": /(?:\b0x[a-f\d]+\b|(?:\b\d+(?:\.\d*)?|\B\.\d+)(?:e[+-]?\d+)?)(?:f|u?l?)?/i,
  "operator": /--|\+\+|&&|\|\||=>|->|~|>>=?|<<=?|[%&|^!=<>/*+-]=?|\?\??|\.{3}/,
  "punctuation": clikePunctuation,
  "constant": /\b[A-Z\d_]+\b/
};
//# sourceMappingURL=vala.js.map
