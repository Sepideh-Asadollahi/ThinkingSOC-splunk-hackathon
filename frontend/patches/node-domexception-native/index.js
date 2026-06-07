const DOMException = globalThis.DOMException

if (!DOMException) {
  throw new Error("node-domexception-native requires Node 18+ (global DOMException)")
}

export default DOMException
export { DOMException }
