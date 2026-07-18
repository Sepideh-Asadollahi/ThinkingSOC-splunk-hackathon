#!/usr/bin/env node

import { execFileSync } from "node:child_process"
import { existsSync, mkdirSync, readdirSync, renameSync } from "node:fs"
import { homedir } from "node:os"
import { join, resolve } from "node:path"
import { chromium } from "@playwright/test"

const mode = process.argv[2] === "full" ? "full" : "sample"
const recordingPart = process.env.TSOC_RECORDING_PART || "all"
const segmentGroups = {
  all: new Set(["welcome", "soc", "value", "investigation", "agents", "execution-graph", "library", "shadow-evaluation", "chat", "closing"]),
  "1": new Set(["welcome", "soc", "value"]),
  "2": new Set(["investigation", "agents", "execution-graph", "library"]),
  "3": new Set(["shadow-evaluation", "chat", "closing"]),
}
const partDurations = { all: "170", "1": "57", "2": "74", "3": "39" }
const activeSegments = segmentGroups[recordingPart]
if (!activeSegments) throw new Error(`Unsupported TSOC_RECORDING_PART: ${recordingPart}`)
const baseUrl = (process.env.TSOC_UI_URL || "http://127.0.0.1:3000").replace(/\/$/, "")
const username = process.env.TSOC_DEMO_USER || "admin"
const password = process.env.TSOC_DEMO_PASSWORD || "123456@a"
const sourceRecordId = process.env.TSOC_DEMO_RECORD_ID || "395"
const alertName = process.env.TSOC_DEMO_ALERT_NAME || "Judge Demo: Suspicious OAuth Token Replay"
const outputRoot = resolve(
  process.env.TSOC_RECORDING_DIR || join(process.cwd(), "..", "artifacts", "devpost-recording"),
)
const partLabel = recordingPart === "all" ? "" : `-part-${recordingPart}`
const runLabel = `${mode}${partLabel}-${new Date().toISOString().replace(/[:.]/g, "-")}`
const outputDir = join(outputRoot, runLabel)
const rawVideoDir = join(outputDir, "raw")
const warmupPaths = [
  "/analysis",
  `/analysis/investigation/${sourceRecordId}`,
  "/runbooks/library",
  "/runbooks/evaluation",
  "/soc-chat",
  "/dashboard",
]

let cursorPosition = { x: 1500, y: 850 }

mkdirSync(rawVideoDir, { recursive: true })

const sleep = (ms) => new Promise((resolvePromise) => setTimeout(resolvePromise, ms))

function log(message) {
  process.stdout.write(`[record:${mode}:${recordingPart}] ${message}\n`)
}

async function waitForApplication(page) {
  await page.waitForLoadState("domcontentloaded")
  await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {})
  await sleep(250)
}

async function authenticate(browser) {
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } })
  const response = await context.request.post(`${baseUrl}/api/auth/login`, {
    data: { username, password },
    timeout: 30_000,
  })
  if (!response.ok()) {
    throw new Error(`Demo authentication failed with HTTP ${response.status()}: ${await response.text()}`)
  }

  const storageState = await context.storageState()
  const sessionCookies = storageState.cookies.filter((cookie) => cookie.name === "tsoc_session")
  if (sessionCookies.length !== 1) {
    throw new Error(`Expected one tsoc_session cookie after login; received ${sessionCookies.length}`)
  }
  log(`authenticated session domain=${sessionCookies[0].domain}; secure=${sessionCookies[0].secure}`)
  await context.close()
  return storageState
}

async function installRecordingChrome(page) {
  if ((await page.locator("#tsoc-recording-style").count()) === 0) {
    const style = await page.addStyleTag({
      content: `
      html { scroll-behavior: smooth !important; }
      #tsoc-recording-caption {
        position: fixed;
        left: 50%;
        bottom: 28px;
        z-index: 2147483646;
        width: min(1180px, calc(100vw - 96px));
        transform: translate(-50%, 16px);
        border: 1px solid rgba(45, 212, 191, .34);
        border-radius: 14px;
        padding: 15px 20px;
        background: rgba(2, 6, 12, .91);
        box-shadow: 0 18px 60px rgba(0, 0, 0, .46), inset 0 1px rgba(255,255,255,.04);
        color: #e5edf5;
        font-family: Inter, ui-sans-serif, system-ui, sans-serif;
        opacity: 0;
        transition: opacity .32s ease, transform .32s ease;
        pointer-events: none;
        backdrop-filter: blur(12px);
      }
      #tsoc-recording-caption[data-visible="true"] { opacity: 1; transform: translate(-50%, 0); }
      #tsoc-recording-caption strong { display: block; color: #5eead4; font-size: 18px; letter-spacing: .01em; }
      #tsoc-recording-caption span { display: block; margin-top: 4px; color: #b8c6d7; font-size: 14px; line-height: 1.45; }
      #tsoc-recording-cursor {
        position: fixed;
        z-index: 2147483647;
        width: 18px;
        height: 18px;
        margin: -9px 0 0 -9px;
        border: 2px solid rgba(94, 234, 212, .95);
        border-radius: 999px;
        background: rgba(13, 148, 136, .16);
        box-shadow: 0 0 0 5px rgba(45, 212, 191, .08);
        pointer-events: none;
        transition: left .06s linear, top .06s linear, transform .12s ease;
      }
      #tsoc-recording-cursor[data-click="true"] { transform: scale(.72); }
      `,
    })
    await style.evaluate((element) => { element.id = "tsoc-recording-style" })
  }

  await page.evaluate(() => {
    let caption = document.querySelector("#tsoc-recording-caption")
    if (!caption) {
      caption = document.createElement("div")
      caption.id = "tsoc-recording-caption"
      caption.innerHTML = "<strong></strong><span></span>"
      document.body.append(caption)
    }

    let cursor = document.querySelector("#tsoc-recording-cursor")
    if (!cursor) {
      cursor = document.createElement("div")
      cursor.id = "tsoc-recording-cursor"
      cursor.style.left = "1500px"
      cursor.style.top = "850px"
      document.body.append(cursor)
    }

    if (!window.__tsocRecordingPointerInstalled) {
      window.__tsocRecordingPointerInstalled = true
      window.addEventListener("mousemove", (event) => {
        const activeCursor = document.querySelector("#tsoc-recording-cursor")
        if (!activeCursor) return
        activeCursor.style.left = `${event.clientX}px`
        activeCursor.style.top = `${event.clientY}px`
      })
      window.addEventListener("mousedown", () => {
        const activeCursor = document.querySelector("#tsoc-recording-cursor")
        if (activeCursor) activeCursor.dataset.click = "true"
      })
      window.addEventListener("mouseup", () => {
        const activeCursor = document.querySelector("#tsoc-recording-cursor")
        if (activeCursor) activeCursor.dataset.click = "false"
      })
    }
  })
}

async function caption(page, title, detail, duration = 2600) {
  await page.evaluate(({ titleText, detailText }) => {
    const root = document.querySelector("#tsoc-recording-caption")
    if (!root) return
    root.querySelector("strong").textContent = titleText
    root.querySelector("span").textContent = detailText
    root.dataset.visible = "true"
  }, { titleText: title, detailText: detail })
  await sleep(duration)
}

async function hideCaption(page, delay = 450) {
  await page.evaluate(() => {
    const root = document.querySelector("#tsoc-recording-caption")
    if (root) root.dataset.visible = "false"
  })
  await sleep(delay)
}

async function moveTo(page, locator) {
  await locator.waitFor({ state: "visible", timeout: 20_000 })
  const box = await locator.boundingBox()
  if (!box) return
  const target = { x: box.x + box.width / 2, y: box.y + box.height / 2 }
  const distance = Math.hypot(target.x - cursorPosition.x, target.y - cursorPosition.y)
  const steps = Math.max(22, Math.min(46, Math.round(distance / 28)))
  const start = { ...cursorPosition }
  for (let index = 1; index <= steps; index += 1) {
    const progress = index / steps
    const eased = progress < 0.5
      ? 4 * progress * progress * progress
      : 1 - Math.pow(-2 * progress + 2, 3) / 2
    await page.mouse.move(
      start.x + (target.x - start.x) * eased,
      start.y + (target.y - start.y) * eased,
    )
    await sleep(18)
  }
  cursorPosition = target
  await sleep(180)
}

async function humanClick(page, locator) {
  await moveTo(page, locator)
  await page.mouse.down()
  await sleep(90)
  await page.mouse.up()
  await sleep(650)
}

async function reveal(locator, position = "center") {
  await locator.waitFor({ state: "attached", timeout: 20_000 })
  await locator.evaluate((element, block) => {
    element.scrollIntoView({ behavior: "smooth", block, inline: "nearest" })
  }, position)
  await sleep(1500)
}

async function gentleWheel(page, pixels, steps = 7) {
  const frameSteps = Math.max(24, steps * 4)
  const weights = Array.from(
    { length: frameSteps },
    (_, index) => 0.35 + Math.sin(((index + 1) / frameSteps) * Math.PI),
  )
  const weightTotal = weights.reduce((total, weight) => total + weight, 0)
  for (const weight of weights) {
    await page.mouse.wheel(0, pixels * (weight / weightTotal))
    await sleep(22)
  }
  await sleep(320)
}

async function open(page, path) {
  const currentUrl = new URL(page.url())
  if (currentUrl.origin === baseUrl && currentUrl.pathname === path) {
    await waitForApplication(page)
    await installRecordingChrome(page)
    return
  }
  const isInvestigationDetail = path.startsWith("/analysis/investigation/")
  const canUseClientNavigation =
    currentUrl.origin === baseUrl && currentUrl.pathname !== path && !isInvestigationDetail
  const link = canUseClientNavigation ? page.locator(`a[href="${path}"]`).first() : null
  const linkIsVisible = link ? await link.isVisible().catch(() => false) : false

  if (link && linkIsVisible) {
    await moveTo(page, link)
    const routeReady = page.waitForURL(
      (url) => url.origin === baseUrl && url.pathname === path,
      { timeout: 30_000 },
    )
    await page.mouse.down()
    await sleep(90)
    await page.mouse.up()
    await routeReady
  } else {
    await page.goto(`${baseUrl}${path}`, { waitUntil: "domcontentloaded", timeout: 30_000 })
  }
  await waitForApplication(page)
  if (new URL(page.url()).pathname.includes("/login")) {
    throw new Error("The authenticated recording session was redirected to /login")
  }
  await installRecordingChrome(page)
}

async function prewarmApplication(context) {
  const page = await context.newPage()
  const video = page.video()
  try {
    for (const path of warmupPaths) {
      await page.goto(`${baseUrl}${path}`, { waitUntil: "domcontentloaded", timeout: 30_000 })
      await page.waitForLoadState("networkidle", { timeout: 8_000 }).catch(() => {})
    }
  } finally {
    await page.close()
    if (video) await video.delete().catch(() => {})
  }
  log("application routes pre-warmed")
}

async function showTailoredFull(page) {
  const timelineStartedAt = Date.now()
  let plannedElapsedMs = 0
  const runSegment = async (label, durationMs, action) => {
    if (!activeSegments.has(label)) return
    plannedElapsedMs += durationMs
    await action()
    const actualElapsedMs = Date.now() - timelineStartedAt
    const remainingMs = plannedElapsedMs - actualElapsedMs
    if (remainingMs > 0) {
      await sleep(remainingMs)
    } else {
      log(
        `timeline overrun label=${label}; actualElapsedMs=${actualElapsedMs}; plannedElapsedMs=${plannedElapsedMs}`,
      )
    }
  }

  await runSegment("welcome", 17_000, async () => {
    await caption(
      page,
      "Welcome to ThinkingSOC Lite",
      "AI Agents turn completed Splunk investigations into checked, analyst-approved Runbooks for matching alerts.",
      6_500,
    )
    await hideCaption(page)
    await gentleWheel(page, 180, 5)
  })

  await runSegment("soc", 17_000, async () => {
    await open(page, "/analysis")
    await caption(
      page,
      "What is a SOC?",
      "A Security Operations Center watches for threats, investigates alerts, and helps the organization respond to incidents—often at very high scale.",
      7_000,
    )
    await hideCaption(page)
    await gentleWheel(page, 300, 6)
  })

  await runSegment("value", 23_000, async () => {
    await open(page, "/dashboard")
    const operations = page.getByText("Runbook operations", { exact: true })
    await reveal(operations, "center")
    await caption(
      page,
      "Reusable knowledge creates measurable value",
      "Mid-sized teams can save thousands annually. Large, high-volume SOCs can save hundreds of thousands—or potentially millions—depending on staffing, alert volume, and reuse.",
      9_000,
    )
    await hideCaption(page)
    await gentleWheel(page, 260, 6)
  })

  await runSegment("investigation", 17_000, async () => {
    await open(page, `/analysis/investigation/${sourceRecordId}`)
    const heading = page.getByText(alertName, { exact: true }).first()
    await heading.waitFor({ state: "visible", timeout: 20_000 })
    await caption(
      page,
      "Accepted investigation → reusable Runbook",
      "The original Splunk alert, verdict, source evidence, and analyst timeline stay together. Acknowledgement compiles accepted findings for the exact Alert Name.",
      8_000,
    )
    await hideCaption(page)
  })

  await runSegment("agents", 23_000, async () => {
    const thinkingSocTab = page.getByRole("tab", { name: "ThinkingSOC Lite" })
    await humanClick(page, thinkingSocTab)
    const agentHeading = page.getByRole("heading", { name: "Runbook Autopilot Agents" })
    await reveal(agentHeading, "start")
    await caption(
      page,
      "Runbook Autopilot Agents",
      "Supervisor manages the workflow; Evidence Scout collects context; Runbook Engineer writes read-only SPL; Policy Guard checks safety; Response Advisor suggests the next step.",
      10_000,
    )
    await hideCaption(page)
    const trace = page.locator('[data-testid="runbook-autopilot-trace"]')
    await trace.waitFor({ state: "visible", timeout: 20_000 })
    const events = trace.locator("article")
    if ((await events.count()) > 3) await reveal(events.nth(3), "center")
    await caption(
      page,
      "MCP first, Splunk REST API fallback",
      "Tool access can fall back to the Splunk REST API. Every Agent handoff, tool result, duration, and failure remains visible in the auditable trace.",
      8_000,
    )
    await hideCaption(page)
  })

  await runSegment("execution-graph", 17_000, async () => {
    const graphHeading = page.getByRole("heading", { name: "Runbook execution graph" })
    await reveal(graphHeading, "start")
    await caption(
      page,
      "Visible evidence and safety gates",
      "Each box exposes read-only SPL, parser validation, source evidence, and its current gate. Reuse requires exact Alert Name matching and human-in-the-loop approval.",
      8_000,
    )
    await hideCaption(page)
  })

  await runSegment("library", 17_000, async () => {
    await open(page, "/runbooks/library")
    const cardTitle = page.getByText("Investigate OAuth Token Replay with Identity Correlation", { exact: true }).first()
    await cardTitle.scrollIntoViewIfNeeded()
    await sleep(400)
    const card = cardTitle.locator("xpath=ancestor::article[1]")
    await humanClick(page, card.getByRole("button", { name: "View details" }))
    const dialog = page.getByRole("dialog")
    await dialog.waitFor({ state: "visible", timeout: 10_000 })
    await caption(
      page,
      "Runbook Library keeps every revision",
      "Search, sort, inspect details, import or export JSON, and create immutable revisions without overwriting history. SPL, evidence, model provenance, performance, and approvals remain available.",
      9_000,
    )
    await hideCaption(page, 200)
    await page.keyboard.press("Escape")
  })

  await runSegment("shadow-evaluation", 17_000, async () => {
    await open(page, "/runbooks/evaluation")
    const recent = page.getByRole("heading", { name: "Recent Shadow Replays" })
    await reveal(recent, "center")
    await caption(
      page,
      "Shadow Evaluation",
      "Test the same detection against another alert and measure SPL validation, evidence coverage, speed, errors, and estimated time saved. Missing evidence and incomplete outcomes stay visible.",
      9_000,
    )
    await hideCaption(page)
  })

  await runSegment("chat", 16_000, async () => {
    await open(page, "/soc-chat")
    const judgeConversation = page.getByText("Judge tour — Runbook Autopilot", { exact: true })
    if (await judgeConversation.isVisible().catch(() => false)) await humanClick(page, judgeConversation)
    await caption(
      page,
      "Runbook knowledge is available in SOC Chat",
      "Ask why an Agent made a decision, inspect its tools and Autopilot trace, or request an approved Runbook for an alert in plain English. The same safety checks still apply.",
      9_000,
    )
    await hideCaption(page, 250)
    const messageInput = page.getByPlaceholder("Ask about alerts—or run an approved Runbook by SID…")
    await moveTo(page, messageInput)
    await messageInput.fill("")
    await messageInput.pressSequentially(
      "Explain the Autopilot Agent handoffs, tool use, and safety gates for this alert.",
      { delay: 20 },
    )
  })

  await runSegment("closing", 6_000, async () => {
    await caption(
      page,
      "ThinkingSOC Lite",
      "Every accepted investigation makes the response to the next matching alert safer, faster, and more useful.",
      2_400,
    )
    await hideCaption(page, 150)
  })
}

async function showLite(page, sample = false) {
  await open(page, `/analysis/investigation/${sourceRecordId}`)
  const heading = page.getByText(alertName, { exact: true }).first()
  await heading.waitFor({ state: "visible", timeout: 20_000 })

  if (!sample) {
    await caption(
      page,
      "Accepted investigation → reusable operational knowledge",
      "The original Alert Name, source SID, evidence, analyst decision, and timeline remain auditable.",
      3300,
    )
    await hideCaption(page)
    await gentleWheel(page, 360, 6)
  }

  const liteTab = page.getByRole("tab", { name: "ThinkingSOC Lite" })
  await humanClick(page, liteTab)
  const agentHeading = page.getByRole("heading", { name: "Runbook Autopilot Agents" })
  await reveal(agentHeading, "start")
  await caption(
    page,
    "Bounded multi-agent Autopilot",
    "Supervisor → Evidence Scout → Runbook Engineer → Policy Guard → Response Advisor; every handoff and tool result is stored.",
    sample ? 3800 : 3400,
  )
  await hideCaption(page)

  const trace = page.locator('[data-testid="runbook-autopilot-trace"]')
  await trace.waitFor({ state: "visible", timeout: 20_000 })
  const events = trace.locator("article")
  const eventCount = await events.count()
  if (eventCount > 3) {
    await reveal(events.nth(Math.min(3, eventCount - 1)))
    await caption(
      page,
      "Agent and tool communication is visible—not implied",
      "The trace shows MCP/REST evidence retrieval, compiler output, policy decisions, and safe-response preview handoffs.",
      sample ? 4200 : 3500,
    )
    await hideCaption(page)
  }

  if (sample) return

  if (eventCount > 8) {
    await reveal(events.nth(8))
    await sleep(1200)
  }
  const graphHeading = page.getByRole("heading", { name: "Runbook execution graph" })
  await reveal(graphHeading, "start")
  await caption(
    page,
    "Evidence and approval are separate gates",
    "Fresh SPL is sanitized, parser-validated, read-only, and source-verified. Human approval is still required before reuse.",
    3600,
  )
  await hideCaption(page)
  await gentleWheel(page, 380, 6)
}

function findBundledFfmpeg() {
  const cache = join(homedir(), ".cache", "ms-playwright")
  if (!existsSync(cache)) return null
  const directory = readdirSync(cache).find((entry) => entry.startsWith("ffmpeg-"))
  if (!directory) return null
  const candidate = join(cache, directory, "ffmpeg-linux")
  return existsSync(candidate) ? candidate : null
}

function findX265Ffmpeg() {
  const candidates = [process.env.TSOC_FFMPEG_BIN, "ffmpeg", findBundledFfmpeg()].filter(Boolean)
  for (const candidate of candidates) {
    try {
      const encoders = execFileSync(candidate, ["-hide_banner", "-encoders"], {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "pipe"],
      })
      if (encoders.includes("libx265")) return candidate
    } catch {
      // Try the next available FFmpeg binary.
    }
  }
  return null
}

function probeDurationSeconds(videoPath) {
  try {
    const value = execFileSync(
      "ffprobe",
      ["-v", "error", "-show_entries", "format=duration", "-of", "default=nokey=1:noprint_wrappers=1", videoPath],
      { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] },
    )
    const duration = Number.parseFloat(value.trim())
    return Number.isFinite(duration) ? duration : null
  } catch {
    return null
  }
}

function transcodeToMp4(webmPath, mp4Path) {
  const ffmpeg = findX265Ffmpeg()
  if (!ffmpeg) return false
  const crf = process.env.TSOC_X265_CRF || "24"
  const trimStart = process.env.TSOC_TRIM_START || "3"
  const preserveNaturalTiming = process.env.TSOC_PRESERVE_TIMING === "1"
  const targetDuration = preserveNaturalTiming
    ? ""
    : process.env.TSOC_TARGET_DURATION || (mode === "full" ? partDurations[recordingPart] : "")
  try {
    const args = [
      "-y", "-ss", trimStart, "-i", webmPath,
    ]
    const sourceDuration = probeDurationSeconds(webmPath)
    const availableDuration = sourceDuration === null ? null : sourceDuration - Number.parseFloat(trimStart)
    if (targetDuration && availableDuration && availableDuration > Number.parseFloat(targetDuration) + 0.25) {
      const timelineScale = Number.parseFloat(targetDuration) / availableDuration
      args.push("-vf", `setpts=${timelineScale.toFixed(8)}*PTS`)
      log(
        `fitting complete clip into ${targetDuration}s; available=${availableDuration.toFixed(2)}s; timelineScale=${timelineScale.toFixed(4)}`,
      )
    }
    if (targetDuration) args.push("-t", targetDuration)
    args.push(
      "-an",
      "-c:v", "libx265",
      "-preset", "medium",
      "-crf", crf,
      "-tag:v", "hvc1",
      "-pix_fmt", "yuv420p",
      "-movflags", "+faststart",
      mp4Path,
    )
    execFileSync(ffmpeg, args, { stdio: "inherit" })
    return true
  } catch {
    return false
  }
}

async function main() {
  log(`target=${baseUrl}; output=${outputDir}`)
  // Use the full Chromium build in modern headless mode. This avoids a second, redundant
  // headless-shell download and records the same rendering engine judges use in Chrome.
  const browser = await chromium.launch({ headless: true, channel: "chromium" })
  const storageState = await authenticate(browser)
  const context = await browser.newContext({
    storageState,
    viewport: { width: 1920, height: 1080 },
    screen: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    colorScheme: "dark",
    recordVideo: { dir: rawVideoDir, size: { width: 1920, height: 1080 } },
  })
  await prewarmApplication(context)
  const page = await context.newPage()
  const failedResponses = []
  page.on("response", (response) => {
    if (response.status() >= 400) failedResponses.push(`${response.status()} ${response.url()}`)
  })

  try {
    if (mode === "sample") {
      await showLite(page, true)
      await page.screenshot({ path: join(outputDir, "sample-preview.png"), fullPage: false })
    } else {
      const initialPath = recordingPart === "2"
        ? `/analysis/investigation/${sourceRecordId}`
        : recordingPart === "3"
          ? "/runbooks/evaluation"
          : "/dashboard"
      await open(page, initialPath)
      await sleep(3_500)
      await showTailoredFull(page)
      await page.screenshot({ path: join(outputDir, "final-frame.png"), fullPage: false })
    }
  } finally {
    const video = page.video()
    await page.close()
    await context.close()
    await browser.close()

    if (!video) throw new Error("Playwright did not create a video artifact")
    const generatedPath = await video.path()
    const webmPath = join(outputDir, `thinking-soc-${mode}-1080p.webm`)
    if (resolve(generatedPath) !== resolve(webmPath)) renameSync(generatedPath, webmPath)
    const mp4Path = join(outputDir, `thinking-soc-${mode}-1080p-x265.mp4`)
    const hasMp4 = transcodeToMp4(webmPath, mp4Path)

    log(`WebM: ${webmPath}`)
    if (hasMp4) log(`MP4:  ${mp4Path}`)
    else log("x265 MP4 conversion skipped because an FFmpeg build with libx265 was not found; the 1080p WebM is ready.")
    if (failedResponses.length > 0) {
      log(`HTTP warnings (${failedResponses.length}):`)
      for (const warning of failedResponses.slice(0, 20)) log(`  ${warning}`)
    }
  }
}

main().catch((error) => {
  const message = error instanceof Error ? error.stack || error.message : String(error)
  process.stderr.write(`[record:${mode}:${recordingPart}] FAILED\n${message}\n`)
  process.exitCode = 1
})
