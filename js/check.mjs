import ts from "typescript";

const configPath = "tsconfig.json";
const formatHost = {
  getCanonicalFileName: (fileName) => fileName,
  getCurrentDirectory: ts.sys.getCurrentDirectory,
  getNewLine: () => ts.sys.newLine,
};

const readResult = ts.readConfigFile(configPath, ts.sys.readFile);
if (readResult.error) {
  console.error(ts.formatDiagnosticsWithColorAndContext([readResult.error], formatHost));
  process.exit(1);
}

const parsedConfig = ts.parseJsonConfigFileContent(
  readResult.config,
  ts.sys,
  process.cwd(),
  undefined,
  configPath,
);

const configErrors = parsedConfig.errors.filter((error) => error.code !== 18003);
if (configErrors.length > 0) {
  console.error(ts.formatDiagnosticsWithColorAndContext(configErrors, formatHost));
  process.exit(1);
}

if (parsedConfig.fileNames.length === 0) {
  process.exit(0);
}

const program = ts.createProgram({
  options: parsedConfig.options,
  rootNames: parsedConfig.fileNames,
});

const diagnostics = ts.getPreEmitDiagnostics(program);
if (diagnostics.length > 0) {
  console.error(ts.formatDiagnosticsWithColorAndContext(diagnostics, formatHost));
  process.exit(1);
}
