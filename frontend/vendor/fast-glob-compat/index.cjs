"use strict";

// This adapter must be loadable by the two CommonJS build-tool consumers.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const { glob, globSync } = require("tinyglobby");

// Next's ESLint plugin uses globSync(..., { onlyDirectories: true });
// vite-plugin-dynamic-import uses sync(..., { cwd }). Neither needs the
// stream/task/object APIs of fast-glob. Fail explicitly if a future update does.
function options(input = {}) {
  const supported = new Set([
    "absolute", "braceExpansion", "caseSensitiveMatch", "cwd", "deep", "dot",
    "extglob", "followSymbolicLinks", "globstar", "ignore", "onlyDirectories",
    "onlyFiles",
  ]);
  for (const key of Object.keys(input)) {
    if (!supported.has(key)) {
      throw new TypeError(`Revon's fast-glob adapter does not support ${key}`);
    }
  }
  // fast-glob does not implicitly descend into a literal directory pattern.
  return { ...input, expandDirectories: false };
}

function paths(entries) {
  // tinyglobby marks directories with '/', while fast-glob leaves them bare.
  return entries.map((entry) => entry.endsWith("/") && entry !== "/" &&
    !/^[A-Za-z]:\/$/.test(entry) ? entry.slice(0, -1) : entry);
}
async function fastGlob(patterns, input) {
  return paths(await glob(patterns, options(input)));
}
fastGlob.sync = (patterns, input) => paths(globSync(patterns, options(input)));
fastGlob.glob = fastGlob;
fastGlob.globSync = fastGlob.sync;
module.exports = fastGlob;
