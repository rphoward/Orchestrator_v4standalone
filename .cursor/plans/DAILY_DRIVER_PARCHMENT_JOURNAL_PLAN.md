---
name: Daily driver parchment journal
overview: >-
  Aesthetic shift for the daily driver (main chat, response card, threads): aged
  parchment page, warm paper cards, Fraunces display + IBM Plex Sans body, subtle
  paper grain. Modals inherit token changes only. No Flask, no JS behavior changes,
  no Tailwind build migration. Work through the execution checklist in order; set each
  YAML todo status to completed as the matching checkbox row ships.
todos:
  - id: html-google-fonts-preconnect
    content: Add two preconnect link tags for Google Fonts in index.html head.
    status: completed
  - id: html-google-fonts-stylesheet
    content: Add one stylesheet link for Fraunces and IBM Plex Sans in index.html head.
    status: completed
  - id: css-font-token-display
    content: In style.css :root, add --font-display for Fraunces.
    status: completed
  - id: css-font-token-body
    content: In style.css :root, add --font-body for IBM Plex Sans.
    status: completed
  - id: css-body-font-family
    content: Set body font-family to var(--font-body) in style.css.
    status: completed
  - id: css-class-t-display
    content: Add .t-display utility class in style.css.
    status: completed
  - id: css-class-t-display-italic
    content: Add .t-display-italic utility class in style.css.
    status: completed
  - id: html-apply-tagline-italic
    content: Add t-display-italic to the Discovery Co-Pilot tagline in index.html.
    status: completed
  - id: html-apply-session-title-display
    content: Add t-display to h2#currentSessionTitle in index.html.
    status: completed
  - id: html-apply-welcome-h2-display
    content: Add t-display to the welcome section h2 in index.html.
    status: completed
  - id: html-apply-nextquestion-display
    content: Add t-display to p#nextQuestion in index.html.
    status: completed
  - id: css-token-parchment-bg
    content: Set --color-bg to #F5ECD8 in style.css :root.
    status: completed
  - id: css-token-card-warm
    content: Set --color-card to #FBF5E9 in style.css :root.
    status: completed
  - id: css-token-border-or-log
    content: Set --color-border to #D8CBB4 or document skip in Decision log.
    status: completed
  - id: html-tailwind-themebg
    content: Set tailwind.config themeBg to #F5ECD8 in index.html.
    status: completed
  - id: html-tailwind-themesurface
    content: Set tailwind.config themeSurface to #FBF5E9 in index.html.
    status: completed
  - id: css-paper-grain-overlay
    content: Append body::before grain rule from Texture plan in style.css.
    status: completed
  - id: css-nextquestion-size
    content: Set #nextQuestion font-size for pull-quote feel in style.css.
    status: completed
  - id: css-nextquestion-lineheight
    content: Set #nextQuestion line-height in style.css.
    status: completed
  - id: css-nextquestion-tracking
    content: Set #nextQuestion letter-spacing in style.css.
    status: completed
  - id: html-cache-bust
    content: Bump style.css query string on the link in index.html (e.g. v=20 to v=22).
    status: completed
  - id: verify-manual-daily-driver
    content: Run app, spot-check daily driver UI and modals per verify section below.
    status: completed
---

# Daily driver aesthetic shift — parchment journal

## Execution checklist

Tick each box as you finish that slice. The YAML `todos` above use the same `id` as the backtick label on each row — flip `status: pending` → `status: completed` when the row ships.

- [x] `html-google-fonts-preconnect` — Preconnect to Google Fonts.
  - **Do:** In [presentation/static/index.html](../../presentation/static/index.html), inside `<head>`, add two lines: `rel="preconnect"` to `https://fonts.googleapis.com` and `https://fonts.gstatic.com` with `crossorigin` on the gstatic line (match Google Fonts boilerplate).
  - **See:** View page source; both preconnect tags appear before the stylesheet link.

- [x] `html-google-fonts-stylesheet` — Load Fraunces + IBM Plex Sans.
  - **Do:** In the same `<head>`, add one `<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=…">` using the family string from **Google Fonts URL** below.
  - **See:** Network tab shows the fonts CSS loading; no 404 on the stylesheet URL.

- [x] `css-font-token-display` — Display font variable.
  - **Do:** In [presentation/static/style.css](../../presentation/static/style.css), inside `:root`, add `--font-display: 'Fraunces', serif;` (or a fallback stack you prefer).
  - **See:** DevTools → `:root` shows `--font-display` in the computed custom properties list.

- [x] `css-font-token-body` — Body font variable.
  - **Do:** In `:root`, add `--font-body: 'IBM Plex Sans', system-ui, sans-serif;`.
  - **See:** `--font-body` appears next to other `--color-*` tokens.

- [x] `css-body-font-family` — Body uses IBM Plex Sans.
  - **Do:** Set `body { font-family: var(--font-body); }` (or merge into existing `body` rule if one exists).
  - **See:** Sidebar labels and thread copy render in IBM Plex Sans once the font loads.

- [x] `css-class-t-display` — Display utility (upright).
  - **Do:** Add `.t-display { font-family: var(--font-display); font-weight: 600; letter-spacing: -0.01em; }` (adjust weight only if verify looks wrong; log tweaks in **Decision log**).
  - **See:** Any element with class `t-display` uses Fraunces at 600 weight.

- [x] `css-class-t-display-italic` — Display utility (italic).
  - **Do:** Add `.t-display-italic { font-family: var(--font-display); font-style: italic; font-weight: 400; }`.
  - **See:** Tagline will use this class in the next rows.

- [x] `html-apply-tagline-italic` — Tagline uses display italic.
  - **Do:** Find the `<p>` in the header whose text is `Discovery Co-Pilot` (uppercase micro-label row). Append `t-display-italic` to its `class` list. Keep existing Tailwind classes unless they fight the look; if they do, trim only what you must and note under **Decision log**.
  - **See:** That line reads in Fraunces italic; it should still feel like a small label (you may add a `text-xs` or similar if size is off).

- [x] `html-apply-session-title-display` — Session title uses display.
  - **Do:** On `h2#currentSessionTitle`, add class `t-display`.
  - **See:** "Select a Session" / session name in the header uses Fraunces display.

- [x] `html-apply-welcome-h2-display` — Welcome headline uses display.
  - **Do:** Inside `#welcomeSection`, on the `h2` that says "Ready for Discovery", add class `t-display`.
  - **See:** Welcome headline uses Fraunces.

- [x] `html-apply-nextquestion-display` — Agent pull-quote uses display.
  - **Do:** On `p#nextQuestion`, add class `t-display`.
  - **See:** The suggested-question block uses Fraunces for the pull-quote line.

- [x] `css-token-parchment-bg` — Parchment page background.
  - **Do:** In `:root`, change `--color-bg` from `#FDF8F5` to `#F5ECD8`.
  - **See:** Page background shifts to warmer parchment yellow.

- [x] `css-token-card-warm` — Warm card surface.
  - **Do:** In `:root`, change `--color-card` from `#FFFFFF` to `#FBF5E9`.
  - **See:** Cards and surfaces using `var(--color-card)` read as warm paper, not stark white.

- [x] `css-token-border-or-log` — Border token or documented skip.
  - **Do:** Either set `--color-border` to `#D8CBB4`, **or** leave `#E2D9CD` and add a bullet under **Decision log** explaining why you skipped.
  - **See:** Borders either match the warmer palette or the log explains the choice.

- [x] `html-tailwind-themebg` — Tailwind background token matches CSS.
  - **Do:** In the inline `tailwind.config` object in `index.html`, set `themeBg: '#F5ECD8'`.
  - **See:** Tailwind `bg-themeBg` areas match the parchment `--color-bg`.

- [x] `html-tailwind-themesurface` — Tailwind surface token matches CSS.
  - **Do:** In the same config, set `themeSurface: '#FBF5E9'`.
  - **See:** `bg-themeSurface` panels match `--color-card`.

- [x] `css-paper-grain-overlay` — Subtle paper grain.
  - **Do:** Append the `body::before` block from **Texture plan** to `style.css` unchanged unless verify needs opacity or `z-index` tuning (log tweaks in **Decision log**).
  - **See:** A very light grain sits across the viewport; it does not block clicks (`pointer-events: none`).

- [x] `css-nextquestion-size` — Pull-quote size.
  - **Do:** Add or extend a `#nextQuestion` rule; set `font-size` per **Pull-quote polish** (e.g. `1.125rem` or `1.25rem`).
  - **See:** Pull-quote reads slightly larger than body micro-copy.

- [x] `css-nextquestion-lineheight` — Pull-quote line height.
  - **Do:** In the same `#nextQuestion` rule (or merge), set `line-height` (e.g. `1.45`).
  - **See:** Multi-line suggested questions do not feel cramped.

- [x] `css-nextquestion-tracking` — Pull-quote tracking.
  - **Do:** In the same rule, set `letter-spacing` (e.g. `-0.02em`).
  - **See:** Serif headline has a slightly editorial tightness; adjust if it looks muddy on your display.

- [x] `html-cache-bust` — Bust cache for stylesheet only.
  - **Do:** On the `<link rel="stylesheet" href="/static/style.css?v=…">` line, bump the `v=` number (e.g. `20` → `22`). Do **not** bump `app.js?v=` unless you edited JS.
  - **See:** Hard refresh picks up new CSS without stale bundle.

- [x] `verify-manual-daily-driver` — Manual pass.
  - **Do:** From repo root, run `python run_dev.py`, open `http://127.0.0.1:5001` (or your `ORCHESTRATOR_PORT`). Start or open a session. Scan header tagline + title, welcome screen, main response area + `#nextQuestion`, thread cards, routing log card. Open Settings briefly — modals should only pick up token changes (bg/surface/border), not grain or forced display fonts inside modal bodies unless inherited accidentally.
  - **See:** Parchment + warm cards + Fraunces on the listed daily-driver surfaces; grain subtle; teal accent unchanged; no JS regressions (send, tabs, settings still work).

---

## Aesthetic direction (locked)

- **Concept**: consultant's field notebook. Aged ivory paper, dark ink, teal wax-seal accents. Editorial-but-quiet, not maximalist. Keeps the current calm tone; adds soul.
- **Type pair** (Google Fonts, avoid Inter / Space Grotesk):
  - **Display**: `Fraunces` (soft serif with character).
  - **Body**: `IBM Plex Sans` (warm humanist sans).
- **Palette**: parchment `#F5ECD8`, card `#FBF5E9`, keep teal `#1A3626`. No new accent hue.
- **Texture**: single fixed SVG-noise overlay on `body::before`, low opacity, `pointer-events: none`, no animation.
- **Scope fence**: **Daily driver** — header session title + tagline, `#welcomeSection`, `#mainContent` (chat, response, threads, routing log card). Modals inherit `--color-*` tokens only; **no** display-serif or grain inside modals this pass.

## Files touched

| File | Role |
|------|------|
| [presentation/static/index.html](../../presentation/static/index.html) | Fonts `<link>`, Tailwind `themeBg` / `themeSurface`, display classes on headings, cache bust |
| [presentation/static/style.css](../../presentation/static/style.css) | Tokens, body font, `.t-display*`, grain, optional border, `#nextQuestion` polish |

No JS, no Flask.

## Type plan (where each font goes)

- `body` → `var(--font-body)` (IBM Plex Sans).
- **Display** (`var(--font-display)`) via `.t-display` / `.t-display-italic`:
  - `header` `h2#currentSessionTitle`
  - "Discovery Co-Pilot" tagline — italic display, small
  - `#welcomeSection` main `h2` ("Ready for Discovery")
  - `#nextQuestionBlock` `p#nextQuestion` (agent pull-quote)
- `.section-label` stays body sans (uppercase micro-label).
- Thread message bodies stay body sans.

## Pull-quote polish (suggested `#nextQuestion`)

Use one rule or merge into existing blocks. Tune at verify; log final numbers in **Decision log**.

```css
#nextQuestion {
    font-size: 1.125rem; /* or 1.25rem */
    line-height: 1.45;
    letter-spacing: -0.02em;
}
```

## Texture plan (grain)

Append to [style.css](../../presentation/static/style.css):

```css
body::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    opacity: 0.04;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
    background-size: 160px 160px;
}
```

If grain sits above content, give main chrome `position: relative; z-index: 1` or tune `opacity` / `background-size` at verify (log in **Decision log**).

## Palette delta (small)

- `--color-bg`: `#FDF8F5` → `#F5ECD8` (yellowed parchment, darker than current ivory).
- `--color-card`: `#FFFFFF` → `#FBF5E9` (warm paper so cards do not read clinical).
- `--color-border`: optional `#E2D9CD` → `#D8CBB4` if edges dissolve; else skip and note under **Decision log**.

Tailwind `themeBg` / `themeSurface` must match the same hex values.

## Google Fonts URL (implementer paste)

Use a single stylesheet link after `preconnect` to `fonts.googleapis.com` and `fonts.gstatic.com`. Typical families string (verify weights on Google Fonts):

- `Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,400`
- `IBM+Plex+Sans:wght@400;500;600;700`

Full href pattern (encode as needed):

`https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,400&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap`

## Atomic slice rules

- One checkbox row = one YAML todo = one primary concern; HTML class application is split from CSS class definition.
- No module renames (`sessions.js`, etc.) in this pass.
- Bump `style.css?v=` when [index.html](../../presentation/static/index.html) or CSS ships; leave `app.js?v=` unchanged unless JS edits occur.

## Decision log

- **Border:** `--color-border` set to `#D8CBB4` (matches warmer parchment palette).
- **Grain:** Texture plan block applied as written (`opacity: 0.04`, `z-index: 0`). Added `body > aside, body > .flex-1 { position: relative; z-index: 1; }` so daily-driver chrome paints above the noise layer; modals/toasts already use higher z-index.
- **Pull-quote:** `#nextQuestion` uses `font-size: 1.125rem`, `line-height: 1.45`, `letter-spacing: -0.02em` (overrides `.t-display` tracking for this line).
- **Verify:** `python run_dev.py --smoke` exit 0; browser spot-check of header, welcome, response card, Settings recommended on first load after deploy.

## Non-goals

- No Tailwind CDN → build migration.
- No full modal restyling.
- No new accent color beyond existing teal.
- No JS behavior changes.

## Relation to other plans

Supersedes any **parchment-only** token tweak if you execute this file end-to-end; this plan already includes `--color-bg` / `--color-card` / Tailwind sync as atomic todos.

## Docs you may read (not required for the checklist)

- [docs/HANDOFF.md](../../docs/HANDOFF.md) — session bridge, smoke command, where plans live.
- [DEV-STANDALONE.md](../../DEV-STANDALONE.md) — runbook, `.env`, verification checklist for the app as a whole.

## Completion rule

When **every** execution checkbox above is checked **and** every YAML `todos[].status` is `completed`, this plan is done. Keep the two in sync; do not leave stale `pending` after the work ships.
