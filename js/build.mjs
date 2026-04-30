import { build } from "esbuild";
import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.dirname(fileURLToPath(import.meta.url));

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

for (const target of [...jsTargets, ...cssTargets]) {
  await ensureParentDir(target.output);
}

const missingCssSources = await findMissingSources(cssTargets);

if (missingCssSources.length > 0) {
  throw new Error(`Missing CSS source files:\n- ${missingCssSources.join("\n- ")}`);
}

const cssSourcePath = path.resolve(rootDir, "src/viz.css");
const cssSource = await readFile(cssSourcePath, "utf8");

for (const target of cssTargets) {
  const outputPath = path.resolve(rootDir, target.output);
  await writeFile(outputPath, `${banner(target.source)}${cssSource}`, "utf8");
}

const missingJsSources = await findMissingSources(jsTargets);

if (missingJsSources.length > 0) {
  throw new Error(`Missing JS source files:\n- ${missingJsSources.join("\n- ")}`);
}

for (const target of jsTargets) {
  await build({
    bundle: true,
    entryPoints: [path.resolve(rootDir, target.source)],
    format: "iife",
    logLevel: "info",
    outfile: path.resolve(rootDir, target.output),
    platform: "browser",
    target: "es2020",
    banner: {
      js: banner(target.source),
    },
  });
}
