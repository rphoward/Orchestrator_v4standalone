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
  - id: css-pressed-motion
    content: >-
      style.css — Add :active + hover ordering for .btn-primary, .btn-secondary,
      .btn-icon, and .send-button. Pressed = middle-road desaturation + tiny darken
      via stacked filters (target ~saturate(0.84–0.88) and ~brightness(0.95–0.97)
      on primary/send; tune so label contrast stays acceptable). Add transform
      translateY(1px) or scale(0.98) only inside @media (prefers-reduced-motion: no-preference).
      Ensure :disabled keeps filter:none (or explicit reset) so pressed styles never
      apply to disabled. Add :focus-visible outline/ring where missing for keyboard.
    status: pending
  - id: css-secondary-icon-tabs
    content: >-
      style.css — Mirror :active treatment for .btn-secondary and .btn-icon (subtler
      movement acceptable). Optionally add light :active to .settings-tab and .agent-tab
      for parity; skip if it fights .active tab styling — document decision in PR.
    status: pending
  - id: html-interface-strip
    content: >-
      index.html — Between settings-header and settings-tab-bar, insert a compact
      "Interface" row (label + checkbox or switch). Use native checkbox with visible
      label "UI sounds" and id; associate label with for=. Do not put this inside a
      single tab panel. Match existing Tailwind/theme classes used on the modal
      (text-themeMuted, flex, gap, border-b if needed).
    status: pending
  - id: module-ui-feedback
    content: >-
      modules/ui_feedback.js (new) — Export initUiFeedback(). Constants: LOCAL_STORAGE_KEY
      = 'orchestrator_v4_ui_sounds_enabled' (or project-consistent prefix), default false.
      On init: read storage, set checkbox checked, on change persist boolean. Implement
      playUiClick() using Web Audio API (short oscillator or noise burst, very low
      volume, ~40–80ms envelope); no external audio files. If sounds enabled, register
      capture or bubble pointerdown on document (or main) that matches button selectors:
      .btn-primary, .btn-secondary, .btn-icon, .send-button, and optionally .settings-tab
      not .active — skip when event.target.closest('button, [role=button]') is disabled
      or has disabled ancestor. Call audioCtx.resume() inside the handler after user
      gesture. Guard double-fire (pointerdown only, not click). No sound for plain links
      unless they use button classes.
    status: pending
  - id: wire-app-entry
    content: >-
      app.js — import './modules/ui_feedback.js' and call initUiFeedback() from
      DOMContentLoaded after DOM exists (same listener block as loadModels is fine, or
      end of listener). Update app.js header comment module tree to list ui_feedback.js.
    status: pending
  - id: verify-manual
    content: >-
      Manual QA — With sounds off: press/hover/disabled on Agent Config Apply and a
      registry save. With sounds on: hear click on primary buttons; toggle off mid-session.
      OS "reduce motion" on: confirm no transform, color press still visible. Bump
      index.html script cache ?v= if the project does that for static busting when
      index changes.
    status: pending
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
| `orchestrator_v4/presentation/static/style.css` | `:active`, `:focus-visible`, reduced-motion for `.btn-*`, `.send-button`, optional tabs. |
| `orchestrator_v4/presentation/static/index.html` | Interface strip markup inside `#settingsModal`. |
| `orchestrator_v4/presentation/static/modules/ui_feedback.js` | **New** — storage, toggle wiring, delegated sound. |
| `orchestrator_v4/presentation/static/app.js` | Import + `initUiFeedback()`. |

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

## Tests

Automated E2E for Web Audio is brittle; **manual QA todo** is the gate. If the repo
adds a small JSDOM-less unit test harness later, optional test could assert
`localStorage` key round-trip — not required for this slice.

## Completion rule

When all YAML todos above are `completed`, this plan is done. Update statuses in this
file as each todo merges; do not leave stale `pending` after the work ships.

## Relocation note

If this file was copied to the monorepo root for recovery, move it to
`orchestrator_v4/.cursor/plans/button_ui_feedback_and_sounds.plan.md` on your working
tree so it sits with other v4 plans.
