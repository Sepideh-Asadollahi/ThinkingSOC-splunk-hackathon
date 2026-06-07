/**
 * Guards the frontend dependency tree against deprecated packages removed in
 * patches/node-domexception-native and the jsdom/whatwg-encoding cleanup.
 *
 * @vitest-environment node
 */
import { execSync } from "node:child_process"
import { readFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { describe, expect, it } from "vitest"

const FRONTEND_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")

type NpmLsNode = {
  version?: string
  resolved?: string
  dependencies?: Record<string, NpmLsNode>
}

function readJson<T>(relativePath: string): T {
  return JSON.parse(readFileSync(path.join(FRONTEND_ROOT, relativePath), "utf8")) as T
}

function findNpmLsDependency(root: NpmLsNode, packageName: string): NpmLsNode | null {
  const deps = root.dependencies
  if (!deps) return null
  if (deps[packageName]) return deps[packageName]
  for (const child of Object.values(deps)) {
    const hit = findNpmLsDependency(child, packageName)
    if (hit) return hit
  }
  return null
}

describe("npm dependency policy", () => {
  it("overrides node-domexception with the native shim", () => {
    const pkg = readJson<{ overrides?: Record<string, string> }>("package.json")
    expect(pkg.overrides?.["node-domexception"]).toBe("file:./patches/node-domexception-native")
  })

  it("does not depend on jsdom (whatwg-encoding came from jsdom)", () => {
    const pkg = readJson<{
      dependencies?: Record<string, string>
      devDependencies?: Record<string, string>
    }>("package.json")
    expect(pkg.dependencies?.jsdom).toBeUndefined()
    expect(pkg.devDependencies?.jsdom).toBeUndefined()
  })

  it("lockfile does not resolve deprecated whatwg-encoding or node-domexception@1", () => {
    const lock = readFileSync(path.join(FRONTEND_ROOT, "package-lock.json"), "utf8")
    expect(lock).not.toContain("whatwg-encoding-3.1.1.tgz")
    expect(lock).not.toContain("node-domexception-1.0.0.tgz")
  })

  it("vitest uses happy-dom (not jsdom)", () => {
    const config = readFileSync(path.join(FRONTEND_ROOT, "vitest.config.mts"), "utf8")
    expect(config).toContain('environment: "happy-dom"')
    expect(config).not.toContain("jsdom")
  })

  it("npm install tree resolves node-domexception to the shim", () => {
    const out = execSync("npm ls node-domexception --json", {
      cwd: FRONTEND_ROOT,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    })
    const tree = JSON.parse(out) as NpmLsNode
    const hit = findNpmLsDependency(tree, "node-domexception")
    expect(hit?.resolved ?? "").toContain("node-domexception-native")
    expect(hit?.version).toBe("2.0.0")
  })

  it("npm install tree has no whatwg-encoding", () => {
    try {
      execSync("npm ls whatwg-encoding", {
        cwd: FRONTEND_ROOT,
        encoding: "utf8",
        stdio: ["pipe", "pipe", "pipe"],
      })
      expect.fail("whatwg-encoding should not be installed")
    } catch (err: unknown) {
      const execErr = err as { status?: number; stdout?: string; stderr?: string }
      expect(execErr.status).toBe(1)
      const combined = `${execErr.stdout ?? ""}${execErr.stderr ?? ""}`
      expect(combined).toContain("(empty)")
    }
  })
})

describe("node-domexception npm override (runtime)", () => {
  it("import node-domexception resolves to native DOMException", async () => {
    const mod = await import("node-domexception")
    expect(mod.default).toBe(globalThis.DOMException)
  })
})

describe("shadcn tailwind entry", () => {
  it("globals.css imports shadcn tailwind (build-time CSS contract)", () => {
    const css = readFileSync(path.join(FRONTEND_ROOT, "app/globals.css"), "utf8")
    expect(css).toContain('@import "shadcn/tailwind.css"')
  })
})
