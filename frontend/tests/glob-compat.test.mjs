import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createRequire } from "node:module";
import test from "node:test";
import fastGlob from "fast-glob";

test("build-tool glob adapter discovers modules and root directories", async () => {
  const cwd = await mkdtemp(join(tmpdir(), "revon-glob-"));
  try {
    await mkdir(join(cwd, "app"));
    await mkdir(join(cwd, "packages", "web"), { recursive: true });
    await Promise.all(["a.ts", "b.tsx", "c.js", ".hidden.ts"].map(
      (name) => writeFile(join(cwd, "app", name), ""),
    ));
    assert.deepEqual(fastGlob.sync("app/*.{ts,tsx}", { cwd }).sort(),
      ["app/a.ts", "app/b.tsx"]);
    assert.deepEqual(await fastGlob("app/*.js", { cwd }), ["app/c.js"]);
    assert.deepEqual(fastGlob.globSync("packages/*", { cwd, onlyDirectories: true }),
      ["packages/web"]);
    assert.deepEqual(fastGlob.sync("app", { cwd }), []);
    assert.deepEqual(fastGlob.sync("app", { cwd, onlyDirectories: true }), ["app"]);
    assert.throws(() => fastGlob.sync("*", { cwd, objectMode: true }), /does not support/);
  } finally {
    await rm(cwd, { recursive: true, force: true });
  }
});

test("both affected build tools resolve the audited adapter", () => {
  for (const name of ["@next/eslint-plugin-next", "vite-plugin-dynamic-import"]) {
    const require = createRequire(import.meta.resolve(name));
    assert.equal(require("fast-glob"), fastGlob, name);
  }
});
