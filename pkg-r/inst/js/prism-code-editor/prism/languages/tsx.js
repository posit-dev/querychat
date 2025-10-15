import { l as languages } from "../../index-bkac8M6P.js";
import { a as addJsxTag } from "../../jsx-shared-Bxuvc7gd.js";
import "./jsx.js";
import "./typescript.js";
addJsxTag(languages.ts, "tsx");
var tag = languages.tsx.tag;
var bracket = "(?:^|(";
try {
  RegExp("(?<=)");
  bracket += "?<=";
} catch {
  tag.lookbehind = true;
}
tag.pattern = RegExp(bracket + `[^\\w$])|(?=</))${tag.pattern.source}`, "g");
//# sourceMappingURL=tsx.js.map
