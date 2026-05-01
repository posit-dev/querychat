import assert from "node:assert/strict";
import test from "node:test";
import { assetTargets } from "../build.mjs";

test("shared asset targets stay scoped to Python outputs on this branch", () => {
  const outputs = assetTargets.map((target) => target.output);

  assert(outputs.length > 0);
  assert(outputs.every((output) => output.startsWith("../pkg-py/")));
});

test("shared viz JavaScript uses a single entrypoint", () => {
  const jsSources = [
    ...new Set(
      assetTargets
        .filter((target) => target.output.endsWith(".js"))
        .map((target) => target.source),
    ),
  ];

  assert.deepEqual(jsSources, ["src/viz.ts"]);
});
