---
name: Button UI feedback and optional sounds
overview: >-
  Add visible press feedback (motion + desaturated/darker :active) to shared button
  classes and the send control; add an always-visible Settings strip with an opt-in
  "UI sounds" toggle (localStorage, default off) and a tiny Web-Audio click on
  pointerdown when enabled. No backend or Flask changes. Reasoning and file
  touchpoints live here; coding agents execute the YAML todos in order and flip
  statuses to completed as they land each slice.
todos:
  - id: css-focus-visible-btn-send
    content: >-
      style.css ONLY — Add :focus-visible keyboard ring/outline for .btn-primary,
      .btn-secondary, .btn-icon, .send-button. No :active or transform in this slice.
    status: completed
  - id: css-active-filter-primary-send
    content: >-
      style.css ONLY — For .btn-primary and .send-button: ensure :hover then :active
      order; :active uses desaturate+darken filter stack per §CSS details; :disabled
      must not show pressed (filter none / reset). No transform yet.
    status: completed
  - id: css-active-transform-primary-send-rrm
    content: >-
      style.css ONLY — Small translateY/scale on :active for .btn-primary and
      .send-button wrapped in @media (prefers-reduced-motion: no-preference). Disabled
      unchanged.
    status: completed
  - id: css-active-secondary-icon
    content: >-
      style.css ONLY — .btn-secondary and .btn-icon: :hover/:active/:disabled press
      treatment (subtler than teal; filter or background per §CSS details). No tab
      rules in this slice.
    status: completed
  - id: css-active-tabs-or-skip-doc
    content: >-
      style.css — Optional light :active on .settings-tab / .agent-tab OR skip with a
      one-line "Decision" bullet under §Decision log in this plan (no code if skipped).
    status: completed
  - id: html-settings-interface-strip
    content: >-
      index.html ONLY — Between settings-header and settings-tab-bar: compact row,
      native checkbox + visible label "UI sounds", stable id + label[for]. Theme
      classes only; no new JS in this slice.
    status: completed
  - id: js-module-shell-interview-ui-sounds
    content: >-
      presentation/static/modules/interview_ui_press_feedback.js (new) — Create file
      with 4+ line header per orchestrator-screaming-presentation.mdc (interview UI
      chrome, not feature panel). Export initUiFeedback() as no-op that does not throw.
      No localStorage, no AudioContext, no listeners yet.
    status: completed
  - id: js-checkbox-localstorage-only
    content: >-
      interview_ui_press_feedback.js ONLY — LOCAL_STORAGE_KEY constant; on
      initUiFeedback: bind checkbox by id from prior HTML todo; read storage default
      false; sync checked; on change persist boolean. No Web Audio, no document
      pointerdown yet.
    status: completed
  - id: js-web-audio-play-click-only
    content: >-
      interview_ui_press_feedback.js ONLY — playUiClick() + single reused
      AudioContext; resume on user gesture path; short low-volume envelope. No delegated
      listeners yet.
    status: completed
  - id: js-delegated-pointerdown-sounds
    content: >-
      interview_ui_press_feedback.js ONLY — When sounds enabled, one document-level
      pointerdown path: match .btn-primary/.btn-secondary/.btn-icon/.send-button and
      optional .settings-tab:not(.active); skip disabled/ancestor; pointerdown only;
      call resume + playUiClick. No changes to other modules.
    status: completed
  - id: app-import-interview-ui-sounds
    content: >-
      app.js ONLY — Add static import for ./modules/interview_ui_press_feedback.js
      alongside existing shell imports. Do not call init yet; do not reorder unrelated
      imports unless required for load order.
    status: completed
  - id: app-bootstrap-init-interview-ui-sounds
    content: >-
      app.js ONLY — In DOMContentLoaded handler, call initUiFeedback(). Update the
      header "Module tree" comment to list interview_ui_press_feedback.js.
    status: completed
  - id: verify-manual-and-cache-bust
    content: >-
      Manual QA per "Manual verification checklist" below; bump index.html
      /static/app.js?v= if index or app.js changed.
    status: completed
---

# Button UI feedback and optional sounds

## Goal

Primary and secondary actions should feel **responsive**: visible **press** state
(distinct from hover and disabled), optional **motion** for users who allow it,
and optional **short click sounds** controlled in **Settings** (not buried, not
agent-specific).

## Non-goals

- No server persistence for the sound toggle (local only is correct for chrome prefs).
- No long audio assets, no autoplay before gesture.
- No change to core/use cases; `presentation/` static only.

## Atomic slice rules (for agents)

- **One YAML todo = one slice:** touch the listed primary file(s) only; do not rename `sessions.js` / `settings.js` / etc. in the same commit as this work.
- **Order is load-bearing:** HTML checkbox ids before JS binding; CSS focus before stacked `:active` if that avoids fighting specificity; import-only `app.js` todo before `init` todo so bisect stays clean.
- **Screaming rename:** New sound module uses **`interview_ui_press_feedback.js`** (not `ui_feedback.js`) so the filename matches interview UI chrome policy; older drafts used `ui_feedback` — ignore that name unless you explicitly revert in a dedicated rename todo.
- **Standalone paths:** Repo root paths are `presentation/static/...` (there is no `orchestrator_v4/` folder on disk).

## Decision log

- **Tab press:** Shipped light `:active` on `.settings-tab` (opacity) and `.agent-tab` (brightness filter); no skip.

## Locked design decisions

| Topic | Decision |
|-------|----------|
| Pressed primary color | **Less saturated + tiny darken** via CSS `filter` stack on `:active`, not a separate hex unless filters prove insufficient. |
| Motion | **Small transform** on `:active`; **omitted** when `prefers-reduced-motion: reduce`. |
| Sound default | **Off**; persist with **localStorage**. |
| Sound placement | **Settings modal**, **between header and tab bar**, visible on every tab. |
| Sound implementation | **Web Audio** generated click; volume very low; **pointerdown** only. |

## Files to touch

| File | Role |
|------|------|
| [presentation/static/style.css](../../presentation/static/style.css) | `:active`, `:focus-visible`, reduced-motion for `.btn-*`, `.send-button`, optional tabs. |
| [presentation/static/index.html](../../presentation/static/index.html) | Interface strip markup inside `#settingsModal`. |
| [presentation/static/modules/interview_ui_press_feedback.js](../../presentation/static/modules/interview_ui_press_feedback.js) | **New** — localStorage, toggle, Web Audio click, delegated `pointerdown`. |
| [presentation/static/app.js](../../presentation/static/app.js) | Import + `initUiFeedback()`. |

## CSS details (for implementers)

- **Order matters**: define `:hover` then `:active` so active wins; `:disabled` must
  reset filters after active rules or use specificity so disabled never shows press.
- **Primary + send** share teal background — keep their `:active` treatment aligned.
- **Secondary / icon** use card/bg colors — pressed state should be a **slight**
  background darken or border emphasis, not the same filter stack as teal if it looks
  wrong; still document chosen values.
- **Contrast**: white text on `:active` primary must still meet reasonable contrast;
  if filters muddy text, reduce darken strength before desaturation or vice versa.

## JS details (for implementers)

- **Single AudioContext** reused; handle suspended state after tab backgrounding.
- **Toggle UI** must run even if user never opens Agents tab — init on app load, not
  only when `openSettings()` runs (checkbox exists in DOM at parse time).
- **Security / noise**: keep listener logic minimal; no eval; no new dependencies.
- **localStorage key (locked):** `orchestrator_v4_ui_sounds_enabled` — boolean; default
  when missing is off (`false`).

## Manual verification checklist

- Sounds **off** (default): press and hover **Agent Config → Apply** and a registry
  save control; confirm **disabled** controls never show pressed styling or play sound.
- Sounds **on**: `pointerdown` on primary (and other matched) controls produces a
  short click; toggle **off** mid-session and confirm silence immediately.
- OS **reduce motion** on: no translate/scale on `:active`; color/filter press still
  visible on primary/send where designed.

## Tests

Automated E2E for Web Audio is brittle; **manual QA todo** is the gate. If the repo
adds a small JSDOM-less unit test harness later, optional test could assert
`localStorage` key round-trip — not required for this slice.

## Completion rule

When all YAML todos above are `completed`, this plan is done. Update statuses in this
file as each todo merges; do not leave stale `pending` after the work ships.

## Relocation note

If this file was copied to the monorepo root for recovery, move it under the package’s
`.cursor/plans/` on your working tree so it sits with other v4 plans. Path prefix in
monorepos may be `orchestrator_v4/`; this standalone clone uses repo-root
`presentation/static/`.
