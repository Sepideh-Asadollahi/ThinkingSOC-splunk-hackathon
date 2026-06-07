/**
 * @vitest-environment node
 */
import { describe, expect, it } from "vitest"

import DOMExceptionDefault, { DOMException } from "./index.js"

describe("node-domexception-native shim", () => {
  it("exports the platform DOMException as default and named export", () => {
    expect(globalThis.DOMException).toBeDefined()
    expect(DOMException).toBe(globalThis.DOMException)
    expect(DOMExceptionDefault).toBe(globalThis.DOMException)
  })

  it("constructs exceptions compatible with fetch-blob/from.js", () => {
    const ex = new DOMException(
      "The requested file could not be read, typically due to permission problems that have occurred after a reference to a file was acquired.",
      "NotReadableError"
    )
    expect(ex).toBeInstanceOf(globalThis.DOMException)
    expect(ex.name).toBe("NotReadableError")
    expect(ex.message).toContain("could not be read")
  })
})
