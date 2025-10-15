var nested = (pattern, depthLog2) => {
  for (var i = 0; i < depthLog2; i++) {
    pattern = pattern.replace(/<self>/g, `(?:${pattern})`);
  }
  return pattern.replace(/<self>/g, "[]");
};
var replace = (pattern, replacements) => pattern.replace(/<(\d+)>/g, (m, index) => `(?:${replacements[+index]})`);
var re = (pattern, replacements, flags) => RegExp(replace(pattern, replacements), flags);
export {
  re as a,
  nested as n,
  replace as r
};
//# sourceMappingURL=shared-DKTvH67n.js.map
