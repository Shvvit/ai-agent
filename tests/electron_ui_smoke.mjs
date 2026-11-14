import assert from "node:assert/strict"
import { createRequire } from "node:module"
import { resolve } from "node:path"

const require = createRequire(resolve(process.cwd(), "package.json"))
const { chromium } = require("@playwright/test")
const cdpUrl = process.env.WLASNEAI_ELECTRON_CDP_URL ?? "http://127.0.0.1:9223"
const browser = await chromium.connectOverCDP(cdpUrl, { timeout: 30_000 })
const pageErrors = []
const consoleErrors = []
const failedRequests = []
const apiResponses = []
const observedPages = new WeakSet()

try {
  const context = browser.contexts()[0]
  assert.ok(context, "Electron did not expose a Chromium browser context")

  let page
  let editor
  let startupErrorPage
  const pageDeadline = Date.now() + 90_000
  while (!page && !startupErrorPage && Date.now() < pageDeadline) {
    for (const candidate of context.pages()) {
      if (candidate.url() === "about:blank" || candidate.url().startsWith("devtools://")) continue
      if (!observedPages.has(candidate)) {
        observedPages.add(candidate)
        candidate.on("pageerror", (error) => pageErrors.push(error.message))
        candidate.on("console", (message) => {
          if (message.type() === "error") consoleErrors.push(message.text())
        })
        candidate.on("requestfailed", (request) => {
          failedRequests.push(`${request.method()} ${request.url()}: ${request.failure()?.errorText ?? "failed"}`)
        })
        candidate.on("response", async (response) => {
          if (!new URL(response.url()).pathname.startsWith("/api/")) return
          const entry = `${response.status()} ${response.request().method()} ${response.url()}`
          apiResponses.push(entry)
          if (response.status() >= 400) {
            try {
              apiResponses.push((await response.text()).slice(0, 1_200))
            } catch {}
          }
        })
      }
      const candidateEditor = candidate.locator('[data-component="composer-editor"][contenteditable="true"]').first()
      if (await candidateEditor.isVisible().catch(() => false)) {
        page = candidate
        editor = candidateEditor
        break
      }
      const body = await candidate.locator("body").innerText({ timeout: 1_000 }).catch(() => "")
      if (body.includes("Something went wrong") && body.includes("Error Details")) {
        startupErrorPage = candidate
        break
      }
    }
    if (!page) await new Promise((resolve) => setTimeout(resolve, 250))
  }
  page ??= startupErrorPage
  assert.ok(page, "Electron did not open its original renderer")
  if (!editor) throw new Error("The original renderer displayed its error page before the chat composer appeared")

  const prompt = `Check the WlasneAI sidecar UI ${Date.now()}`
  const reply = `WlasneAI E2E response: ${prompt}`

  await editor.fill(prompt)
  await editor.press("Enter")

  const transcript = page.locator("[data-timeline-virtual-content]")
  await transcript.locator('[data-timeline-row="UserMessage"]').filter({ hasText: prompt }).waitFor({
    state: "visible",
    timeout: 30_000,
  })
  await transcript.locator('[data-timeline-row="AssistantPart"]').filter({ hasText: reply }).waitFor({
    state: "visible",
    timeout: 90_000,
  })

  assert.deepEqual(pageErrors, [], "The original OpenCode renderer reported an uncaught error")
  console.log(`Verified Electron UI → WlasneAI Python sidecar → local model → UI response: ${reply}`)
} catch (error) {
  const pages = browser.contexts().flatMap((context) => context.pages())
  for (const page of pages) {
    try {
      console.error(`Renderer ${page.url()} title=${await page.title()}`)
      console.error((await page.locator("body").innerText({ timeout: 5_000 })).slice(0, 6_000))
      console.error("Error details:", await page.locator("textarea,input").evaluateAll((items) => items.map((item) => item.value)))
    } catch {}
  }
  if (pageErrors.length) console.error("Renderer errors:", pageErrors)
  if (consoleErrors.length) console.error("Renderer console errors:", consoleErrors.slice(-80))
  if (failedRequests.length) console.error("Failed requests:", failedRequests.slice(-80))
  if (apiResponses.length) console.error("API responses:", apiResponses.slice(-160))
  throw error
} finally {
  await browser.close()
}
