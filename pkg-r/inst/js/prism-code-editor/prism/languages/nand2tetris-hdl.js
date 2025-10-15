import { l as languages } from "../../index-bkac8M6P.js";
import { c as clikeComment, b as boolean } from "../../patterns-BwNIoKDQ.js";
languages["nand2tetris-hdl"] = {
  "comment": clikeComment(),
  "keyword": /\b(?:BUILTIN|CHIP|CLOCKED|IN|OUT|PARTS)\b/,
  "boolean": boolean,
  "function": /\b[a-zA-Z][A-Za-z\d]*(?=\()/,
  "number": /\b\d+\b/,
  "operator": /=|\.\./,
  "punctuation": /[()[\]{},:;]/
};
//# sourceMappingURL=nand2tetris-hdl.js.map
