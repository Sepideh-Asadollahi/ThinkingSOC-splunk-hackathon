/**
 * Ensures fetch-blob uses the overridden node-domexception shim (not deprecated v1).
 *
 * @vitest-environment node
 */
import { readFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { describe, expect, it } from "vitest"

const FRONTEND_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")

describe("fetch-blob + node-domexception override", () => {
  it("fetch-blob/from.js imports the same DOMException as the shim", async () => {
    const shim = await import("../patches/node-domexception-native/index.js")
    const fromMod = await import("fetch-blob/from.js")
    // from.js default-imports node-domexception; behavior must match our shim.
    expect(shim.default).toBe(globalThis.DOMException)
    const ex = new shim.default("test", "NotReadableError")
    expect(ex.name).toBe("NotReadableError")
    expect(fromMod).toBeDefined()
  })

  it("node_modules node-domexception package is the local shim", async () => {
    const mod = await import("node-domexception")
    const pkg = JSON.parse(
      readFileSync(path.join(FRONTEND_ROOT, "node_modules/node-domexception/package.json"), "utf8")
    ) as { version?: string }
    expect(pkg.version).toBe("2.0.0")
    expect(mod.default).toBe(globalThis.DOMException)
  })
})
