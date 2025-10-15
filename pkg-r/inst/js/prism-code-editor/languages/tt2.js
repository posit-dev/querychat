import { getClosestToken } from "../utils/index.js";
import { f as markupTemplateLang } from "../index-CHhGi2gg.js";
markupTemplateLang("tt2", {
  block: ["[%#", "%]"]
}).getComments = (editor, position) => ({
  line: getClosestToken(editor, ".tt2", 0, 0, position) && "#",
  block: ["[%#", "%]"]
});
//# sourceMappingURL=tt2.js.map
