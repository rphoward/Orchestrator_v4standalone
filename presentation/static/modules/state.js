/**
 * Cross-cutting interview UI shell — not a feature module.
 * Owns: shared mutable browser state (sessions list, agents, model registry pointers).
 * Mutations go through setters so call sites are easy to grep.
 * See `.cursor/rules/orchestrator-screaming-presentation.mdc` for naming policy.
 */

export let autoRoute       = true;
export let selectedAgentId = 1;
export let activeThreadId  = 1;
export let agents          = [];
export let currentReport   = null;
export let currentSessionId = null;
export let modelRegistry   = [];

export function setAutoRoute(v)        { autoRoute        = v; }
export function setSelectedAgentId(v)  { selectedAgentId  = v; }
export function setActiveThreadId(v)   { activeThreadId   = v; }
export function setAgents(v)           { agents           = v; }
export function setCurrentReport(v)    { currentReport    = v; }
export function setCurrentSessionId(v) {
    currentSessionId = v;
    if (v != null) localStorage.setItem('currentSessionId', String(v));
    else           localStorage.removeItem('currentSessionId');
}
export function setModelRegistry(v)    { modelRegistry    = v; }
export function spliceModelRegistry(index, count) { modelRegistry.splice(index, count); }
