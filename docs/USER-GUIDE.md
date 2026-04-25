# Orchestrator v4 — User Guide

A hands-on walkthrough for running live discovery interviews. Each section covers one thing. Do it, see the result, move on.

---

## 1. Start the app

**Do:**

```powershell
python run_dev.py
```

**You should see:**

```
🎙️  Orchestrator V4 -> http://127.0.0.1:5001
```

Open that URL in your browser.

If you see `offline stub` in the terminal instead of a live Gemini message, you need a `GEMINI_API_KEY` in `.env` at the repo root. See [DEV-STANDALONE.md](../DEV-STANDALONE.md#environment-files) for the setup table.

---

## 2. Create your first session

**You should see:** A welcome screen titled "Ready for Discovery" with a coffee cup icon and two text fields.

**Do:**

1. Type a client or project name into the **Client / Project Name** field (e.g. `Acme Corp Rebrand`).
2. Optionally type a short label into **Internal Session Title** (e.g. `Initial Discovery`).
3. Click **🚀 Start New Session**.

**You should see:** The welcome screen slides away and the main interview screen appears. The header at the top now shows your session title.

---

## 3. Resume a past session

**Do:**

1. Click the **+** button in the top-left corner of the sidebar. A modal appears.
2. In the **Search by client name** box, type part of a past client name.
3. Click the client name, then pick the session you want.

**You should see:** The main interview screen loads with the prior conversation history already in the thread tabs.

---

## 4. Send a message

**You should see:** A text area with the placeholder "Type or paste what the founder said…" and a **▶** send button.

**Do:** Type something the founder just said in the interview, then press **▶** or hit **Enter**.

**You should see:**
- A brief "Routing & Analyzing…" status appears while the AI decides which specialist agent to use.
- The response card appears below the input, showing which agent answered (e.g. "Routed to: 🪞 Brand") and the suggested next question in the highlighted box.
- The agent's thread tab fills in with the exchange.

---

## 5. Read the response card

After each send, the response card shows three things:

| What you see | What it means |
|---|---|
| "Routed to: 🪞 Brand" (or another agent name) | The specialist agent that answered this turn |
| Suggested next question | The verbatim script you can read to the founder |
| 🧠 Analysis / 🎯 Pivot (collapsible rows) | The agent's internal reasoning and suggested reframe — open if you want the detail |

The next question text is the model's formatted output. A numbered **1.** in that text is just a markdown list item — it does not mean the app is "on stage 1."

---

## 6. Understand the stage badge and dots

At the top of the screen, next to "Discovery Co-Pilot", you will see:

- A small pill that reads **Stage: 1** (or 2, 3, 4). This is the **active stage pointer** — the earliest stage that is not yet marked complete. It updates automatically after each turn.
- Four small colored **dots** to the right. Each dot = one stage (Brand, Founder, Customer, Arch). A filled dot = that stage is complete; an open dot = still in progress.

**Important:** The stage badge tells you which stage the system is tracking, not necessarily which agent just answered. If stage 1 is complete but the router still picks the Brand agent for a follow-up question, the badge advances to **Stage: 2** while the thread still shows Brand content. That is normal — the router can revisit any completed stage.

---

## 7. Switch between auto-routing and manual routing

By default, the **Auto-Route** checkbox in the top-left of the chat card is checked. The AI router picks the specialist agent automatically.

**To pick the agent yourself:**

1. Uncheck **Auto-Route**.
2. You should see four agent buttons appear: **🪞 Brand**, **🛑 Founder**, **🎯 Customer**, **⚙️ DDD**.
3. Click the one you want.
4. Type your message and send.

**You should see:** The response card says "Manual → Brand" (or whichever you chose) instead of "Routed to: …".

**To go back to auto-routing:** Check **Auto-Route** again. The picker hides and the input snaps to the active stage agent thread automatically.

---

## 8. Read the agent threads

Below the response card is the **Agent Threads** section with four tabs: **🪞 Brand**, **🛑 Founder**, **🎯 Customer**, **⚙️ DDD**.

**Do:** Click any tab.

**You should see:** The full conversation history for that specialist — every message you sent and every reply from that agent, in order.

You can switch tabs freely while the interview is running. Reading the Brand thread while on the Founder stage is fine and often useful.

---

## 9. Check the routing log

Near the bottom of the main screen is a collapsed section: **📡 Routing Intelligence Log**.

**Do:** Click the "📡 Routing Intelligence Log" heading to expand it.

**You should see:** A list of recent routing decisions — each entry shows which agent was chosen, when, a snippet of what you typed, and the reason the router chose that agent (e.g. "STAY: user is still providing Brand identity information").

---

## 10. See stage tracking detail (debug)

Inside the Routing Intelligence Log section, there is a smaller nested row: **Stage tracking (debug)**.

**Do:** Click "Stage tracking (debug)" to expand it.

**You should see:** A single line of technical output showing the last turn's stage tracking snapshot — mode, gate result, whether the completion judge ran, and the current stage flags (e.g. `1=True, 2=False, 3=False, 4=False`).

This panel shows only the most recent turn. It is for spotting why a stage has or has not advanced yet. If you want to see the full history of snapshots, see [DEV-STANDALONE.md](../DEV-STANDALONE.md#active-stage-pointer-and-auto-routing).

---

## 11. Change stage tracking settings

Stage tracking controls *when* the AI is asked to judge whether a stage is complete.

**Do:**

1. Click **⚙️ Agent Settings** at the bottom of the left sidebar.
2. The settings panel opens. Scroll to the **Stage Tracking** card (purple left border).
3. Choose a mode from the **Mode** dropdown:
   - **Hybrid** (default) — judges completion after a natural amount of evidence builds up; skips unnecessary calls.
   - **Semantic** — judges every eligible turn; more thorough, more model calls.
   - **Off** — no automatic stage completion; stages only advance if you force it.
4. Optionally change the **Judge interval** number (how many turns between judge calls in Hybrid mode; default 4).
5. Click **Save**.

**You should see:** A small "Saved: Hybrid, judge interval 4 turns." confirmation line appears.

For a deeper explanation of how the judge gate works, see [DEV-STANDALONE.md](../DEV-STANDALONE.md#active-stage-pointer-and-auto-routing).

---

## 12. Run the grand synthesis (Agent 5)

When all four stage dots are filled, the **📋 Finalize Report** button in the top-right becomes active.

**Do:** Click **📋 Finalize Report**.

**You should see:** A confirmation prompt, then the report generation runs. Agent 5 (Grand Synthesis) does not appear in the regular agent tabs — it only runs at finalization and cannot be selected during the interview.

---

## 13. Export the transcript

At any point during or after an interview:

**Do:** Click **📜 Transcript** in the top-right header.

**You should see:** A full chronological transcript of all messages across all agents opens in a modal. You can read or copy it from there.

---

## Summary of screen areas

| Area | Where | Purpose |
|------|-------|---------|
| Sidebar | Left column | Session list; switch or create sessions; open settings |
| Header | Top bar | Session title; Stage badge; four stage dots; Transcript; Finalize Report |
| Chat card | Main area | "What did the founder just say?" input, Auto-Route toggle, manual agent picker |
| Response card | Below chat | Routed agent, next question, Analysis, Pivot |
| Agent Threads | Below response | Per-agent full conversation history |
| Routing Intelligence Log | Bottom, collapsed | Routing decisions; nested Stage tracking (debug) |

---

## For developers

This section lists internal names for anyone reading source code or this document alongside the codebase.

| Screen label | HTML id / file |
|---|---|
| Stage badge ("Stage: N") | `#activeStagePointerBadge` — updated by `updateActiveStagePointerBadge()` in `interview_sessions_panel.js` |
| Four stage dots | `#stageStatusTrackerDots` |
| Auto-Route checkbox | `#autoRoutingToggle` |
| Manual agent picker | `#manualRoutingAgentPicker` |
| Chat input | `#messageInput` |
| Response card | `#responseSection` |
| Next question box | `#nextQuestion` |
| Agent Threads section | `#threadsSection` |
| Routing Intelligence Log | `#routingSection` / `#routingLog` |
| Stage tracking (debug) | `#stageTrackingDebug` — populated by `loadStageTrackingDebug()` and `renderStageTrackingPanel()` in `interview_chat_panel.js` |
| Stage Tracking settings card | `#stageTrackingModeSelect`, `#stageTrackingJudgeIntervalInput` in `settings_agent.js` |
| Backend stage tracking API | `GET /api/sessions/<id>/stage-tracking` returns `{"entries": [...]}` (full history) |
| Stage completion judge | `infrastructure/ai/gemini_stage_completion_judge.py` |
| Stage flag persistence | `sessions.stage1_complete … stage4_complete` columns in SQLite |
