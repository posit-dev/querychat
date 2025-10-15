import { l as languages } from "../../index-bkac8M6P.js";
import { a as re } from "../../shared-DKTvH67n.js";
var comment = {
  pattern: /(^[ 	]*|  |	)#.*/mg,
  lookbehind: true,
  greedy: true
};
var variable = {
  pattern: /((?:^|[^\\])(?:\\\\)*)[$@&%]\{(?:[^{}\n]|\{[^{}\n]*\})*\}/,
  lookbehind: true,
  inside: {
    "punctuation": /^[$@&%]\{|\}$/
  }
};
var createSection = (name, inside) => {
  var extendecInside = {};
  extendecInside["section-header"] = {
    pattern: /^ ?\*{3}.+?\*{3}/,
    alias: "keyword"
  };
  Object.assign(extendecInside, inside);
  extendecInside["tag"] = {
    pattern: /(\n(?:  |	)[ 	]*)\[[-\w]+\]/,
    lookbehind: true,
    inside: {
      "punctuation": /[[\]]/
    }
  };
  extendecInside["variable"] = variable;
  extendecInside["comment"] = comment;
  return {
    pattern: re("^ ?\\*{3}[ 	]*<0>[ 	]*\\*{3}(?:.|\n(?!\\*{3}))*", [name], "im"),
    alias: "section",
    inside: extendecInside
  };
};
var docTag = {
  pattern: /(\[Documentation\](?:  |	)[ 	]*)(?![ 	]|#)(?:.|\n[ 	]*\.{3})+/,
  lookbehind: true,
  alias: "string"
};
var testNameLike = {
  pattern: /(\n ?)(?!#)(?:\S(?:[ 	]\S)*)+/,
  lookbehind: true,
  alias: "function",
  inside: {
    "variable": variable
  }
};
var testPropertyLike = {
  pattern: /(\n(?: |	)[ 	]*)(?!\[|\.{3}|#)(?:\S(?:[ 	]\S)*)+/,
  lookbehind: true,
  inside: {
    "variable": variable
  }
};
languages.robot = languages.robotframework = {
  "settings": createSection("Settings", {
    "documentation": {
      pattern: /(\n ?Documentation(?:  |	)[ 	]*)(?![ 	]|#)(?:.|\n[ 	]*\.{3})+/,
      lookbehind: true,
      alias: "string"
    },
    "property": {
      pattern: /(\n ?)(?!\.{3}|#)(?:\S(?:[ 	]\S)*)+/,
      lookbehind: true
    }
  }),
  "variables": createSection("Variables"),
  "test-cases": createSection("Test Cases", {
    "test-name": testNameLike,
    "documentation": docTag,
    "property": testPropertyLike
  }),
  "keywords": createSection("Keywords", {
    "keyword-name": testNameLike,
    "documentation": docTag,
    "property": testPropertyLike
  }),
  "tasks": createSection("Tasks", {
    "task-name": testNameLike,
    "documentation": docTag,
    "property": testPropertyLike
  }),
  "comment": comment
};
//# sourceMappingURL=robotframework.js.map
