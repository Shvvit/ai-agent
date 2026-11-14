import assert from "node:assert/strict"
import { createRequire } from "node:module"
import { resolve } from "node:path"

const require = createRequire(resolve(process.cwd(), "package.json"))
const { chromium } = require("@playwright/test")
const cdpUrl = process.env.WLASNEAI_ELECTRON_CDP_URL ?? "http://127.0.0.1:9223"
const browser = await chromium.connectOverCDP(cdpUrl, { timeout: 30_000 })
const pageErrors = []

try {
  const context = browser.contexts()[0]
  assert.ok(context, "Electron did not expose a Chromium browser context")

  let page
  let editor
  const pageDeadline = Date.now() + 90_000
  while (!page && Date.now() < pageDeadline) {
    for (const candidate of context.pages()) {
      if (candidate.url() === "about:blank" || candidate.url().startsWith("devtools://")) continue
      const candidateEditor = candidate.locator('[data-component="composer-editor"][contenteditable="true"]').first()
      if (await candidateEditor.isVisible().catch(() => false)) {
        page = candidate
        editor = candidateEditor
        break
      }
    }
    if (!page) await new Promise((resolve) => setTimeout(resolve, 250))
  }
  assert.ok(page, "Electron did not open the original renderer with its chat composer")
  page.on("pageerror", (error) => pageErrors.push(error.message))

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
    } catch {}
  }
  if (pageErrors.length) console.error("Renderer errors:", pageErrors)
  throw error
} finally {
  await browser.close()
}
