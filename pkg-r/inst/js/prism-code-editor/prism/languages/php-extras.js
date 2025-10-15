import { l as languages } from "../../index-bkac8M6P.js";
import { i as insertBefore } from "../../language-DPYOfXzt.js";
import "./php.js";
insertBefore(languages.php.php.inside, "variable", {
  "this": {
    pattern: /\$this\b/,
    alias: "keyword"
  },
  "global": /\$(?:GLOBALS|HTTP_RAW_POST_DATA|_COOKIE|_ENV|_FILES|_GET|_POST|_REQUEST|_SERVER|_SESSION|arg[cv]|http_response_header|php_errormsg)\b/,
  "scope": {
    pattern: /\b[\w\\]+::/,
    inside: {
      "keyword": /\b(?:parent|self|static)\b/,
      "punctuation": /::|\\/
    }
  }
});
//# sourceMappingURL=php-extras.js.map
