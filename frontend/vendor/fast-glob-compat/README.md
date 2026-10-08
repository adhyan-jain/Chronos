# Build-tool glob adapter

`@next/eslint-plugin-next` calls `fast-glob.globSync` to find project root
directories. `vite-plugin-dynamic-import`, via vinext's CommonJS plugin, calls
`fast-glob.sync` to find modules. This local adapter implements those calls
with pinned `tinyglobby`, plus its asynchronous equivalent. It disables
implicit directory expansion to preserve fast-glob's behavior.

The override removes the vulnerable `braces` dependency, which has no patched
release for [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)
as of 9 October 2026. It does not suppress npm audit findings. The separate
sharp and source-map-js overrides select patched releases for
[GHSA-wq5f-xc86-pv6w](https://github.com/advisories/GHSA-wq5f-xc86-pv6w) and
[GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q).

This is a deliberately limited compatibility layer, not a full fast-glob
implementation. Unsupported options fail explicitly. The glob tests check
module brace patterns, directory roots, CommonJS resolution in both consumers,
and the absence of implicit directory expansion. `npm test` also builds and
server-renders the complete application.

When upgrading either consumer, review its glob calls. Remove this adapter
once upstream dependencies offer a tested, vulnerability-free replacement.
After changing overrides, regenerate the lockfile and verify a fresh `npm ci`,
`npm ls fast-glob braces --all`, `npm run lint`, `npm test`, and `npm audit`.
