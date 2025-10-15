import { l as languageMap } from "../index-BltwYS88.js";
import { getClosestToken } from "../utils/index.js";
import { c as clikeComment, d as markupComment, h as htmlAutoIndent, e as autoCloseTags, v as voidTags, x as xmlOpeningTag } from "../index-CHhGi2gg.js";
languageMap.php = {
  comments: clikeComment,
  getComments: (editor, position) => {
    if (getClosestToken(editor, ".php", 0, 0, position))
      return clikeComment;
    return markupComment;
  },
  autoIndent: htmlAutoIndent(xmlOpeningTag, voidTags),
  autoCloseTags: ([start, end], value, editor) => {
    return !value.includes("<?") || getClosestToken(editor, ".php", 0, 0, start) ? "" : autoCloseTags(editor, start, end, value, xmlOpeningTag, voidTags);
  }
};
//# sourceMappingURL=php.js.map
