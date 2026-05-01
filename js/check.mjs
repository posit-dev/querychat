import { readFile } from "node:fs/promises";
import path from "node:path";
import ts from "typescript";
import { assetTargets, repoDir, resolveOutputPath, withStagedBuild } from "./build.mjs";

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

if (parsedConfig.fileNames.length > 0) {
  const program = ts.createProgram({
    options: parsedConfig.options,
    rootNames: parsedConfig.fileNames,
  });

  const diagnostics = ts.getPreEmitDiagnostics(program);
  if (diagnostics.length > 0) {
    console.error(ts.formatDiagnosticsWithColorAndContext(diagnostics, formatHost));
    process.exit(1);
  }
}

const staleOutputs = [];

await withStagedBuild(async (stageDir) => {
  for (const target of assetTargets) {
    const stagedOutputPath = resolveOutputPath(stageDir, target.output);
    const committedOutputPath = resolveOutputPath(repoDir, target.output);
    const relativeOutputPath = path.relative(repoDir, committedOutputPath);

    let stagedOutput;
    let committedOutput;

    try {
      [stagedOutput, committedOutput] = await Promise.all([
        readFile(stagedOutputPath),
        readFile(committedOutputPath),
      ]);
    } catch (error) {
      if (error && typeof error === "object" && "code" in error && error.code === "ENOENT") {
        staleOutputs.push(relativeOutputPath);
        continue;
      }

      throw error;
    }

    if (!stagedOutput.equals(committedOutput)) {
      staleOutputs.push(relativeOutputPath);
    }
  }
});

if (staleOutputs.length > 0) {
  console.error("Generated web assets are out of sync. Run `make js-build`.");
  for (const outputPath of staleOutputs) {
    console.error(`- ${outputPath}`);
  }
  process.exit(1);
}
