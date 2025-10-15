import { l as languages } from "../../index-bkac8M6P.js";
import { i as insertBefore, c as clone } from "../../language-DPYOfXzt.js";
import "./c.js";
insertBefore(languages["cilk-c"] = languages.cilkc = clone(languages.c), "function", {
  "parallel-keyword": {
    pattern: /\bcilk_(?:for|reducer|s(?:cope|pawn|ync))\b/,
    alias: "keyword"
  }
});
//# sourceMappingURL=cilkc.js.map
