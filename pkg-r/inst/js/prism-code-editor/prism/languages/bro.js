import { l as languages } from "../../index-bkac8M6P.js";
import { a as clikeString, e as clikeNumber, d as clikePunctuation } from "../../patterns-BwNIoKDQ.js";
languages.bro = {
  "comment": {
    pattern: /(^|[^\\$])#.*/,
    lookbehind: true,
    inside: {
      "italic": /\b(?:FIXME|TODO|XXX)\b/
    }
  },
  "string": clikeString(),
  "boolean": /\b[TF]\b/,
  "function": {
    pattern: /(\b(?:event|function|hook)[ 	]+)\w+(?:::\w+)?/,
    lookbehind: true
  },
  "builtin": /(?:@(?:load(?:-(?:plugin|sigs))?|unload|prefixes|ifn?def|else|(?:end)?if|DIR|FILENAME))|(?:&?(?:add_func|create_expire|default|delete_func|encrypt|error_handler|expire_func|group|log|mergeable|optional|persistent|priority|raw_output|read_expire|redef|rotate_interval|rotate_size|synchronized|type_column|write_expire))/,
  "constant": {
    pattern: /(\bconst[ 	]+)\w+/i,
    lookbehind: true
  },
  "keyword": /\b(?:add|addr|alarm|any|bool|break|const|continue|count|delete|double|else|enum|event|export|file|for|function|global|hook|if|int?|interval|local|module|next|of|opaque|pattern|port|print|record|return|schedule|set|string|subnet|table|time|timeout|using|vector|when)\b/,
  "operator": /--|\+\+|&&?|::|\|\|?|[!=<>+-]=?|\??\$|[?/*~^%]/,
  "number": clikeNumber,
  "punctuation": clikePunctuation
};
//# sourceMappingURL=bro.js.map
