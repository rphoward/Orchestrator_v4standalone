/**
 * chat.js — Message input, send flow, thread rendering, routing log.
 * Coordinates with sessions.js for resume (thread preload avoids duplicate fetches).
 */

import { api }                             from './api.js';
import { showStatus, hideStatus }          from './ui.js';
import { AGENT_ICONS, escapeHtml, formatMarkdown, truncate } from './utils.js';
import {
    autoRoute, setAutoRoute,
    agents,
    selectedAgentId, setSelectedAgentId,
    activeThreadId, setActiveThreadId,
    currentSessionId,
} from './state.js';
import {
    loadSessions,
    updateStageBadge,
    refreshHeaderState,
    refreshSessionTranscriptCache,
} from './sessions.js';

/**
 * True when `#threadContent` shows the empty or load-error placeholder (not real messages).
 * Uses a DOM marker so edits to placeholder copy cannot break optimistic send.
 */
function _threadHasPlaceholder(threadEl) {
    return Boolean(threadEl?.querySelector('[data-thread-placeholder]'));
}

// ── Input & Routing toggles ──────────────────────────────────────

export function toggleAutoRoute() {
    setAutoRoute(document.getElementById('autoRouteToggle').checked);
    const selector = document.getElementById('manualSelector');
    if (autoRoute) {
        // Just make it a visual indicator instead of completely hiding it
        selector.classList.remove('hidden');
        selector.style.pointerEvents = 'none';
        selector.style.opacity = '0.7';
    } else {
        selector.classList.remove('hidden');
        selector.style.pointerEvents = 'auto';
        selector.style.opacity = '1';
        selectAgent(selectedAgentId);
    }
}

export function selectAgent(id) {
    setSelectedAgentId(id);
    document.querySelectorAll('.agent-tab').forEach(
        t => t.classList.toggle('active', parseInt(t.dataset.agent) === id)
    );
}

export function handleInputKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(e); }
}

// ── Send Flow ────────────────────────────────────────────────────

export async function handleSend(e) {
    if (e) e.preventDefault();
    if (!currentSessionId) return;

    const input   = document.getElementById('messageInput');
    const message = input.value.trim();
    if (!message) return;

    // Instantly clear & yield the input back to the user
    input.value = '';
    document.getElementById('sendBtn').disabled     = true;
    document.getElementById('sendIcon').innerHTML   = '<span class="spinner"></span>';
    showStatus('Routing & Analyzing...');

    // Optimistic render: echo the user's message immediately so the
    // UI feels alive while the backend crunches (2-8 s).
    const threadEl = document.getElementById('threadContent');
    if (threadEl) {
        if (_threadHasPlaceholder(threadEl)) threadEl.innerHTML = '';
        const ghost           = document.createElement('div');
        ghost.className       = 'thread-message user';
        ghost.style.opacity   = '0.6';
        ghost.innerHTML       = `
            <span class="role-label">Consultant</span>
            <div>${formatMarkdown(message)}</div>
        `;
        ghost.dataset.optimistic = 'true';
        threadEl.appendChild(ghost);
        threadEl.scrollTop = threadEl.scrollHeight;
    }

    try {
        const result = autoRoute
            ? await api(`/api/sessions/${currentSessionId}/send`, {
                method: 'POST',
                body:   JSON.stringify({ message }),
              })
            : await api(`/api/sessions/${currentSessionId}/send-manual`, {
                method: 'POST',
                body:   JSON.stringify({ agent_id: selectedAgentId, message }),
              });

        // displayResponse → showThread → loadThread will fully re-render
        // threadContent from the DB, which naturally replaces the ghost div.
        displayResponse(result);
        await loadRoutingLogs();
        await refreshSessionTranscriptCache();

        if (result.session_renamed) {
            document.getElementById('currentSessionTitle').textContent = result.session_renamed;
            loadSessions();
        }
        await refreshHeaderState();
    } catch (err) {
        console.error('Send failed:', err);
        // On error, remove the ghost so the user doesn't see a phantom message
        if (threadEl) {
            threadEl.querySelectorAll('[data-optimistic="true"]').forEach(g => g.remove());
        }
    } finally {
        hideStatus();
        document.getElementById('sendIcon').textContent  = '▶';
        document.getElementById('sendBtn').disabled      = !input.value.trim();
    }
}

// ── Response Display ─────────────────────────────────────────────

/**
 * Updates the routing card and next-question panel, then refreshes the thread for `agent_id`.
 * When `options.preloadedMessages` is set (same shape as `GET .../conversations?agent_id=`),
 * the thread is rendered from that array without a second network call (resume path).
 */
export function displayResponse(result, options = {}) {
    const responseBox = document.getElementById('responseSection');
    responseBox.classList.remove('hidden');
    
    // Add pulse animation to indicate update
    responseBox.classList.remove('pulse-route');
    void responseBox.offsetWidth; // trigger reflow
    responseBox.classList.add('pulse-route');

    const agentId = result.agent_id || selectedAgentId;
    document.getElementById('routeIcon').textContent   = AGENT_ICONS[agentId] || '🤖';
    
    // Explicitly update Route Agent name, falling back dynamically
    const nameById = new Map((agents || []).map((a) => [String(a.id), a.name]));
    const agentName = result.agent_name || nameById.get(String(agentId)) || ('Agent ' + agentId);
    const routeLabel =
        result.routing_reason === 'Manual override' ? 'Manual →' : 'Routed to:';
    document.getElementById('routeAgent').textContent  = `${routeLabel} ${agentName}`;
    document.getElementById('routeReason').textContent = result.routing_reason || '';

    // Subtle update in the "agents box" above the input
    if (autoRoute) {
        selectAgent(agentId);
    }

    if (result.current_gate) updateStageBadge(result.current_gate);

    const parsed = parseAgentResponse(result.response || '');
    const fullQuestion = [parsed.preamble, parsed.question].filter(Boolean).join('\n\n');
    document.getElementById('nextQuestion').innerHTML = formatMarkdown(fullQuestion || 'No specific question suggested.');

    const analysisDetails = document.getElementById('analysisContent').closest('details');
    const pivotDetails    = document.getElementById('pivotContent').closest('details');

    // Keep details collapsed by default — icons signal clickability
    if (parsed.analysis) {
        document.getElementById('analysisContent').innerHTML = formatMarkdown(parsed.analysis);
        if (analysisDetails) {
            analysisDetails.style.display = '';
            analysisDetails.removeAttribute('open');
            analysisDetails.classList.add('has-content');
        }
    } else {
        if (analysisDetails) { analysisDetails.style.display = 'none'; analysisDetails.classList.remove('has-content'); }
    }

    if (parsed.pivot) {
        document.getElementById('pivotContent').innerHTML = formatMarkdown(parsed.pivot);
        if (pivotDetails) {
            pivotDetails.style.display = '';
            pivotDetails.removeAttribute('open');
            pivotDetails.classList.add('has-content');
        }
    } else {
        if (pivotDetails) { pivotDetails.style.display = 'none'; pivotDetails.classList.remove('has-content'); }
    }

    const preloaded = options.preloadedMessages;
    showThread(agentId, preloaded !== undefined ? { preloadedMessages: preloaded } : {});
}

export function parseAgentResponse(text) {
    const r      = { preamble: '', analysis: '', pivot: '', question: '' };
    
    // Extract any text before the SILENT ANALYSIS flag (e.g. the Honest Contract preamble)
    const preambleMatch = text.match(/^([\s\S]*?)(?=🧠\s*(?:SILENT ANALYSIS|Silent Analysis))/i);
    if (preambleMatch && preambleMatch[1].trim()) {
        r.preamble = preambleMatch[1].trim();
    }

    const aMatch = text.match(/🧠\s*(?:SILENT ANALYSIS|Silent Analysis)[^\n]*\n([\s\S]*?)(?=🎯|$)/i);
    const pMatch = text.match(/🎯\s*(?:TACTICAL PIVOT|Tactical Pivot)[^\n]*\n([\s\S]*?)(?=☕|$)/i);
    const qMatch = text.match(/☕\s*(?:YOUR NEXT QUESTION|THE CONSULTANT'S SCRIPT|Next Question)[^\n]*\n([\s\S]*?)$/i);
    
    if (aMatch) r.analysis = aMatch[1].trim();
    if (pMatch) r.pivot    = pMatch[1].trim();
    if (qMatch) r.question = qMatch[1].trim();
    
    if (!r.analysis && !r.pivot && !r.question) r.question = text;
    return r;
}

// ── Threads ──────────────────────────────────────────────────────

/**
 * Activates the thread tab and loads messages for the agent (or uses `preloadedMessages` from the caller).
 */
export function showThread(agentId, opts = {}) {
    setActiveThreadId(agentId);
    document.querySelectorAll('.thread-tab').forEach(
        t => t.classList.toggle('active', parseInt(t.dataset.thread) === agentId)
    );
    loadThread(agentId, opts);
}

/**
 * Fills `#threadContent` from the API or from `opts.preloadedMessages` (same filter as `?agent_id=`).
 */
export async function loadThread(agentId, opts = {}) {
    if (!currentSessionId) return;
    try {
        let msgs;
        if (opts.preloadedMessages !== undefined) {
            msgs = opts.preloadedMessages;
        } else {
            msgs = await api(`/api/sessions/${currentSessionId}/conversations?agent_id=${agentId}`);
        }
        const c    = document.getElementById('threadContent');
        if (msgs.length === 0) {
            c.innerHTML =
                '<p class="thread-empty-placeholder text-themeMuted text-sm italic text-center py-8" data-thread-placeholder>No messages in this thread yet.</p>';
            return;
        }

        // Resolve agent name: per-agent endpoint doesn't JOIN agent table,
        // so m.agent_name is undefined. Look it up from the loaded agents list.
        const { agents } = await import('./state.js');
        const agentRecord = agents.find(a => a.id === agentId);
        const agentLabel  = agentRecord ? agentRecord.name : `Agent ${agentId}`;

        c.innerHTML = msgs.map(m => {
            let displayContent = m.content;
            // DB stores role as 'assistant', not 'model'
            if (m.role === 'assistant' && m.message_type !== 'summary') {
                const p = parseAgentResponse(m.content);
                if (p.analysis || p.pivot || p.question) {
                     displayContent = [p.preamble, p.question].filter(Boolean).join('\n\n');
                }
            }
            return `
            <div class="thread-message ${m.role === 'user' ? 'user' : 'model'}">
                <span class="role-label">${m.role === 'user'
                    ? 'Consultant'
                    : AGENT_ICONS[agentId] + ' ' + escapeHtml(agentLabel)
                }</span>
                <div>${formatMarkdown(displayContent)}</div>
            </div>
            `;
        }).join('');
        c.scrollTop = c.scrollHeight;
    } catch (err) {
        console.error('loadThread failed:', err);
        const c = document.getElementById('threadContent');
        if (c) {
            c.innerHTML =
                '<p class="thread-empty-placeholder text-red-700 text-sm text-center py-8 px-2" data-thread-placeholder>' +
                'Could not load this thread. Try another tab or refresh the page.</p>';
        }
    }
}

// ── Routing Log ──────────────────────────────────────────────────

export async function loadRoutingLogs() {
    if (!currentSessionId) return;
    try {
        const logs = await api(`/api/sessions/${currentSessionId}/routing-logs`);
        const c    = document.getElementById('routingLog');
        if (logs.length === 0) {
            c.innerHTML = '<p class="text-themeMuted text-sm italic">No routing decisions yet.</p>';
            return;
        }
        c.innerHTML = logs.map(l => `
            <div class="routing-entry mb-2">
                <div class="flex justify-between items-center mb-1">
                    <span class="font-bold text-themeAccent">${AGENT_ICONS[l.agent_id] || '🤖'} ${escapeHtml(l.agent_name)}</span>
                    <span class="text-themeMuted text-xs">${new Date(l.timestamp + 'Z').toLocaleTimeString()}</span>
                </div>
                <div class="text-themeText italic">"${escapeHtml(truncate(l.input_text, 80))}"</div>
                ${l.reason ? `<div class="text-themeMuted mt-1 text-xs opacity-80">${escapeHtml(l.reason)}</div>` : ''}
            </div>
        `).join('');
    } catch (err) {
        console.error('loadRoutingLogs failed:', err);
        const c = document.getElementById('routingLog');
        if (c) {
            c.innerHTML =
                '<p class="text-red-700 text-sm italic">Could not load routing log. Try again later.</p>';
        }
    }
}

// ── Window bindings for HTML onclicks ───────────────────────────────
window.toggleAutoRoute    = toggleAutoRoute;
window.selectAgent        = selectAgent;
window.handleInputKeydown = handleInputKeydown;
window.handleSend         = handleSend;
window.showThread         = showThread;
