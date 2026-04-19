/**
 * Cross-cutting interview UI shell — not a feature module.
 * Owns: shared mutable browser state (sessions list, agents, model registry
 * pointers) plus the active stage pointer mirror that the chat panel and
 * session panel both read.
 * Mutations go through setters so call sites are easy to grep.
 * See `.cursor/rules/orchestrator-screaming-presentation.mdc` for naming policy.
 */

// Routing mode: true when auto-routing is on (router picks the agent),
// false when manual routing is on (consultant picks the agent for the turn).
export let autoRoutingOn            = true;

// The agent the manual routing picker is currently aimed at.
export let manualRoutingTargetAgentId = 1;

// The chat thread currently open in the main pane (may differ from the
// manual routing target between clicks).
export let openChatThreadAgentId      = 1;

// Last known active stage pointer (earliest unfinished stage 1..4), mirrored
// from either the turn result or the current session summary. The chat panel
// reads this when the auto-routing toggle changes so it can snap the manual
// picker and open thread to the pointer without an extra /api/sessions fetch.
export let lastActiveStagePointer     = 1;

export let agents          = [];
export let currentReport   = null;
export let currentSessionId = null;
export let modelRegistry   = [];

export function setAutoRoutingOn(v)              { autoRoutingOn            = v; }
export function setManualRoutingTargetAgentId(v) { manualRoutingTargetAgentId = v; }
export function setOpenChatThreadAgentId(v)      { openChatThreadAgentId      = v; }
export function setLastActiveStagePointer(v)     { lastActiveStagePointer     = v; }
export function setAgents(v)                     { agents                    = v; }
export function setCurrentReport(v)              { currentReport             = v; }
export function setCurrentSessionId(v) {
    currentSessionId = v;
    if (v != null) localStorage.setItem('currentSessionId', String(v));
    else           localStorage.removeItem('currentSessionId');
}
export function setModelRegistry(v)    { modelRegistry    = v; }
export function spliceModelRegistry(index, count) { modelRegistry.splice(index, count); }
