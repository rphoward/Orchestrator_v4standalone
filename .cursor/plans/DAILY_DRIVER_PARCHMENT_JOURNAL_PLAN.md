---
name: Daily driver parchment journal
overview: >-
  Aesthetic shift for the daily driver (main chat, response card, threads): aged
  parchment page, warm paper cards, Fraunces display + IBM Plex Sans body, subtle
  paper grain. Modals inherit token changes only. No Flask, no JS behavior changes,
  no Tailwind build migration. Execute YAML todos in order; flip status to completed
  as each slice lands.
todos:
  - id: html-google-fonts-link
    content: >-
      index.html ONLY — add Google Fonts preconnect + CSS link for Fraunces + IBM Plex
      Sans in <head>.
    status: pending
  - id: css-font-tokens
    content: >-
      style.css ONLY — add --font-display and --font-body in :root; set body
      font-family to --font-body.
    status: pending
  - id: css-display-class-and-headings
    content: >-
      style.css ONLY — add .t-display and .t-display-italic utility classes. No HTML
      changes yet.
    status: pending
  - id: html-apply-display-class-tagline
    content: >-
      index.html ONLY — add t-display-italic to Discovery Co-Pilot tagline and
      t-display to #currentSessionTitle.
    status: pending
  - id: html-apply-display-welcome-and-response
    content: >-
      index.html ONLY — add t-display to #welcomeSection h2 and #nextQuestion.
    status: pending
  - id: css-token-parchment-bg
    content: "style.css ONLY — --color-bg to #F5ECD8."
    status: pending
  - id: css-token-card-warm
    content: "style.css ONLY — --color-card to #FBF5E9."
    status: pending
  - id: html-tailwind-theme-sync
    content: >-
      index.html ONLY — tailwind.config themeBg to #F5ECD8 and themeSurface to
      #FBF5E9.
    status: pending
  - id: css-border-tune-or-skip
    content: >-
      style.css — either set --color-border to #D8CBB4 OR append a Decision bullet
      skipping it.
    status: pending
  - id: css-paper-grain-overlay
    content: "style.css ONLY — append body::before grain overlay rule (see §Texture plan)."
    status: pending
  - id: css-response-pullquote-polish
    content: >-
      style.css ONLY — nudge #nextQuestion size/line-height/tracking for serif
      pull-quote feel.
    status: pending
  - id: html-cache-bust
    content: "index.html ONLY — bump style.css ?v= query (e.g. 20 → 22) on the stylesheet link."
    status: pending
  - id: verify-manual-daily-driver
    content: >-
      Run python run_dev.py, start a session, verify header/welcome/response serif,
      parchment + card read, grain subtle, modals unchanged beyond token inheritance.
    status: pending
---

# Daily driver aesthetic shift — parchment journal

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

## Atomic slice rules

- One YAML todo = one primary concern; HTML class application split from CSS class definition.
- No module renames (`sessions.js`, etc.) in this pass.
- Bump `style.css?v=` when [index.html](../../presentation/static/index.html) or CSS ships; leave `app.js?v=` unchanged unless JS edits occur.

## Decision log

- _(Append: final border choice, grain opacity/size, any font weight tweaks after verify.)_

## Non-goals

- No Tailwind CDN → build migration.
- No full modal restyling.
- No new accent color beyond existing teal.
- No JS behavior changes.

## Relation to other plans

Supersedes any **parchment-only** token tweak if you execute this file end-to-end; this plan already includes `--color-bg` / `--color-card` / Tailwind sync as atomic todos.

## Completion rule

When all YAML todos above are `completed`, this plan is done. Update statuses as slices merge; do not leave stale `pending` after the work ships.
