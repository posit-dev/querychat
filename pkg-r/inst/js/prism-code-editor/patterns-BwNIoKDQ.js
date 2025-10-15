var clikeComment = () => ({
  pattern: /\/\/.*|\/\*[^]*?(?:\*\/|$)/g,
  greedy: true
});
var clikeString = () => ({
  pattern: /(["'])(?:\\[^]|(?!\1)[^\\\n])*\1/g,
  greedy: true
});
var clikeNumber = /\b0x[a-f\d]+\b|(?:\b\d+(?:\.\d*)?|\B\.\d+)(?:e[+-]?\d+)?/i;
var clikePunctuation = /[()[\]{}.,:;]/;
var boolean = /\b(?:false|true)\b/;
export {
  clikeString as a,
  boolean as b,
  clikeComment as c,
  clikePunctuation as d,
  clikeNumber as e
};
//# sourceMappingURL=patterns-BwNIoKDQ.js.map
