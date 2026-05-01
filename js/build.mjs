import { build } from "esbuild";
import {
  access,
  copyFile,
  mkdir,
  mkdtemp,
  readFile,
  rm,
  writeFile,
} from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.dirname(fileURLToPath(import.meta.url));
export const repoDir = path.resolve(rootDir, "..");

const jsTargets = [
  {
    source: "src/viz-r.ts",
    output: "../pkg-r/inst/htmldep/viz.js",
  },
  {
    source: "src/viz-py.ts",
    output: "../pkg-py/src/querychat/static/js/viz.js",
  },
];

const cssTargets = [
  {
    source: "src/viz.css",
    output: "../pkg-r/inst/htmldep/viz.css",
  },
  {
    source: "src/viz.css",
    output: "../pkg-py/src/querychat/static/css/viz.css",
  },
];

const ensureParentDir = async (relativePath) => {
  const absolutePath = path.resolve(rootDir, relativePath);
  await mkdir(path.dirname(absolutePath), { recursive: true });
  return absolutePath;
};

export const assetTargets = [...cssTargets, ...jsTargets];

export const resolveOutputPath = (baseDir, relativePath) =>
  path.resolve(baseDir, path.relative(repoDir, path.resolve(rootDir, relativePath)));

const banner = (source) =>
  `/* Generated file. Source: js/${source}. Do not edit directly. */\n`;

const uniqueSources = (targets) => [...new Set(targets.map((target) => target.source))];

const findMissingSources = async (targets) => {
  const missingSources = [];

  for (const source of uniqueSources(targets)) {
    try {
      await access(path.resolve(rootDir, source));
    } catch {
      missingSources.push(`js/${source}`);
    }
  }

  return missingSources;
};

const reportMissingSources = async () => {
  const missingCssSources = await findMissingSources(cssTargets);
  const missingJsSources = await findMissingSources(jsTargets);

  if (missingCssSources.length === 0 && missingJsSources.length === 0) {
    return;
  }

  const messages = [];

  if (missingCssSources.length > 0) {
    messages.push(`Missing CSS source files:\n- ${missingCssSources.join("\n- ")}`);
  }

  if (missingJsSources.length > 0) {
    messages.push(`Missing JS source files:\n- ${missingJsSources.join("\n- ")}`);
  }

  throw new Error(messages.join("\n\n"));
};

export const stageBuildOutputs = async (stageDir) => {
  const cssSourcePath = path.resolve(rootDir, "src/viz.css");
  const cssSource = await readFile(cssSourcePath, "utf8");

  for (const target of cssTargets) {
    const outputPath = resolveOutputPath(stageDir, target.output);
    await mkdir(path.dirname(outputPath), { recursive: true });
    await writeFile(outputPath, `${banner(target.source)}${cssSource}`, "utf8");
  }

  for (const target of jsTargets) {
    const outputPath = resolveOutputPath(stageDir, target.output);
    await mkdir(path.dirname(outputPath), { recursive: true });
    await build({
      bundle: true,
      entryPoints: [path.resolve(rootDir, target.source)],
      format: "iife",
      logLevel: "info",
      outfile: outputPath,
      platform: "browser",
      target: "es2020",
      banner: {
        js: banner(target.source),
      },
    });
  }
};

export const commitBuildOutputs = async (stageDir) => {
  for (const target of assetTargets) {
    const stagedOutputPath = resolveOutputPath(stageDir, target.output);
    await ensureParentDir(target.output);
    await copyFile(stagedOutputPath, path.resolve(rootDir, target.output));
  }
};

export async function withStagedBuild(callback) {
  await reportMissingSources();

  const stageDir = await mkdtemp(path.join(os.tmpdir(), "querychat-build-"));

  try {
    await stageBuildOutputs(stageDir);
    return await callback(stageDir);
  } finally {
    await rm(stageDir, { force: true, recursive: true });
  }
}

export async function buildOutputs() {
  await withStagedBuild(commitBuildOutputs);
}

const isEntrypoint =
  process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (isEntrypoint) {
  await buildOutputs();
}
