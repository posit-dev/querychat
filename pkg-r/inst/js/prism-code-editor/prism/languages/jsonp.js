import { l as languages } from "../../index-bkac8M6P.js";
import { i as insertBefore, e as extend } from "../../language-DPYOfXzt.js";
import { d as clikePunctuation } from "../../patterns-BwNIoKDQ.js";
import "./json.js";
insertBefore(languages.jsonp = extend("json", {
  "punctuation": clikePunctuation
}), "punctuation", {
  "function": /(?!\d)(?:(?!\s)[$\w\xa0-\uffff])+(?=\s*\()/
});
//# sourceMappingURL=jsonp.js.map
