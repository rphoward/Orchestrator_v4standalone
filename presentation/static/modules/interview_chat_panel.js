/**
 * interview_chat_panel.js — Message input, send flow, thread rendering, routing log.
 *
 * Coordinates with interview_sessions_panel.js for resume (thread preload
 * avoids duplicate fetches) and reads the active stage pointer from state.js
 * so toggling auto-routing can snap the manual picker to the pointer.
 */

import { api }                             from './api.js';
import { showStatus, hideStatus }          from './ui.js';
import { AGENT_ICONS, escapeHtml, formatMarkdown, truncate } from './utils.js';
import {
    autoRoutingOn, setAutoRoutingOn,
    agents,
    manualRoutingTargetAgentId, setManualRoutingTargetAgentId,
    setOpenChatThreadAgentId,
    lastActiveStagePointer, setLastActiveStagePointer,
    currentSessionId,
} from './state.js';
import {
    loadSessions,
    updateActiveStagePointerBadge,
    refreshHeaderState,
    refreshSessionTranscriptCache,
    snapChatToActiveStagePointer,
} from './interview_sessions_panel.js';

/**
 * True when `#threadContent` shows the empty or load-error placeholder (not real messages).
 * Uses a DOM marker so edits to placeholder copy cannot break optimistic send.
 */
function _threadHasPlaceholder(threadEl) {
    return Boolean(threadEl?.querySelector('[data-thread-placeholder]'));
}

// ── Auto-routing toggle + manual routing picker ─────────────────

/**
 * Flip between auto-routing and manual routing.
 *
 * Either direction snaps the manual picker and the open chat thread to the
 * active stage pointer (earliest unfinished stage 1..4). That way switching
 * modes is always an explicit "come back to forward motion" move.
 */
export function toggleAutoRouting() {
    setAutoRoutingOn(document.getElementById('autoRoutingToggle').checked);
    const picker = document.getElementById('manualRoutingAgentPicker');

    const pointer = lastActiveStagePointer || 1;

    if (autoRoutingOn) {
        picker.classList.add('hidden');
        picker.style.pointerEvents = '';
        picker.style.opacity = '';
        // Keep state consistent even in auto mode; the backend will also
        // respect the pointer on the next turn.
        void snapChatToActiveStagePointer();
    } else {
        picker.classList.remove('hidden');
        picker.style.pointerEvents = 'auto';
        picker.style.opacity = '1';
        // Preselect the pointer agent and open that thread so the next send
        // targets the forward-motion stage by default.
        chooseManualRoutingAgent(pointer);
        showThread(pointer);
    }
}

/**
 * Highlight one of the manual routing tabs. Does not change the open thread —
 * the visible thread only changes when `showThread(id)` is called.
 */
export function chooseManualRoutingAgent(id) {
    setManualRoutingTargetAgentId(id);
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

    input.value = '';
    document.getElementById('sendBtn').disabled     = true;
    document.getElementById('sendIcon').innerHTML   = '<span class="spinner"></span>';
    showStatus('Routing & Analyzing...');

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
        const result = autoRoutingOn
            ? await api(`/api/sessions/${currentSessionId}/send`, {
                method: 'POST',
                body:   JSON.stringify({ message }),
              })
            : await api(`/api/sessions/${currentSessionId}/send-manual`, {
                method: 'POST',
                body:   JSON.stringify({ agent_id: manualRoutingTargetAgentId, message }),
              });

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

    responseBox.classList.remove('pulse-route');
    void responseBox.offsetWidth;
    responseBox.classList.add('pulse-route');

    const agentId = result.agent_id || manualRoutingTargetAgentId;
    document.getElementById('routeIcon').textContent   = AGENT_ICONS[agentId] || '🤖';

    const nameById = new Map((agents || []).map((a) => [String(a.id), a.name]));
    const agentName = result.agent_name || nameById.get(String(agentId)) || ('Agent ' + agentId);
    const routeLabel =
        result.routing_reason === 'Manual override' ? 'Manual →' : 'Routed to:';
    document.getElementById('routeAgent').textContent  = `${routeLabel} ${agentName}`;
    document.getElementById('routeReason').textContent = result.routing_reason || '';

    if (autoRoutingOn) {
        chooseManualRoutingAgent(agentId);
    }

    // The turn result ships the active stage pointer so the badge can update
    // without a second round-trip. Mirror it into state so toggleAutoRouting
    // can snap the picker without fetching /api/sessions.
    if (typeof result.active_stage_pointer === 'number' && result.active_stage_pointer > 0) {
        updateActiveStagePointerBadge(result.active_stage_pointer);
        setLastActiveStagePointer(result.active_stage_pointer);
    }

    const parsed = parseAgentResponse(result.response || '');
    const fullQuestion = [parsed.preamble, parsed.question].filter(Boolean).join('\n\n');
    document.getElementById('nextQuestion').innerHTML = formatMarkdown(fullQuestion || 'No specific question suggested.');

    const analysisDetails = document.getElementById('analysisContent').closest('details');
    const pivotDetails    = document.getElementById('pivotContent').closest('details');

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

    if (result && result.stage_tracking) {
        renderStageTrackingPanel(result.stage_tracking);
    }
}

/**
 * Renders the latest `stage_tracking` dict from a turn result or from GET /stage-tracking.
 * Read-only: does not call export or the judge.
 */
function renderStageTrackingPanel(st) {
    const c = document.getElementById('stageTrackingDebug');
    if (!c) return;
    if (!st || typeof st !== 'object') {
        c.innerHTML = '<p class="text-themeMuted text-[11px] italic">No stage tracking data yet. Send a message to populate.</p>';
        return;
    }
    const after = st.stage_flags_after || {};
    const v = st.verdict;
    const ev = st.evaluated_progress || {};
    const lineMode = `Mode: ${st.stage_tracking_mode} · turn: ${st.turn_endpoint} · agent ${st.routed_stage_id}`;
    const lineGate = st.judge_ran
        ? `Gate: ${st.gate_reason} · outcome: ${st.judge_outcome}`
        : `Gate: ${st.gate_reason} (judge skipped)`;
    const lineProg = `Progress: ${ev.summary || '—'} · u=${ev.user_message_count} e=${ev.meaningful_evidence_count} t=${ev.turns_since_judge} · JSON updated: ${st.progress_json_updated}`;
    const lineV = v
        ? `Verdict: complete=${v.stage_complete} conf=${v.confidence} — ${(v.reason || '').slice(0, 200)}`
        : '';
    const fl = [1, 2, 3, 4].map((n) => `${n}=${after[String(n)]}`).join(', ');
    c.innerHTML = [
        `<div>${escapeHtml(lineMode)}</div>`,
        `<div>${escapeHtml(lineGate)}</div>`,
        `<div>${escapeHtml(lineProg)}</div>`,
        v ? `<div>${escapeHtml(lineV)}</div>` : '',
        `<div>Flags: ${escapeHtml(fl)}</div>`,
    ].filter(Boolean).join('');
}

export function parseAgentResponse(text) {
    const r      = { preamble: '', analysis: '', pivot: '', question: '' };

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
    setOpenChatThreadAgentId(agentId);
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

        const { agents } = await import('./state.js');
        const agentRecord = agents.find(a => a.id === agentId);
        const agentLabel  = agentRecord ? agentRecord.name : `Agent ${agentId}`;

        c.innerHTML = msgs.map(m => {
            let displayContent = m.content;
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
        await loadStageTrackingDebug();
    } catch (err) {
        console.error('loadRoutingLogs failed:', err);
        const c = document.getElementById('routingLog');
        if (c) {
            c.innerHTML =
                '<p class="text-red-700 text-sm italic">Could not load routing log. Try again later.</p>';
        }
    }
}

/** Read-only: GET persisted snapshots (no LLM, no export refresh). */
export async function loadStageTrackingDebug() {
    if (!currentSessionId) return;
    const c = document.getElementById('stageTrackingDebug');
    if (!c) return;
    try {
        const data = await api(`/api/sessions/${currentSessionId}/stage-tracking`);
        const arr = data.entries || [];
        const st = arr.length ? arr[arr.length - 1] : null;
        renderStageTrackingPanel(st);
    } catch (err) {
        console.error('loadStageTrackingDebug failed:', err);
        c.innerHTML = '<p class="text-red-700 text-[11px]">Could not load stage tracking (debug).</p>';
    }
}

// ── Window bindings for HTML onclicks ───────────────────────────────
window.toggleAutoRouting        = toggleAutoRouting;
window.chooseManualRoutingAgent = chooseManualRoutingAgent;
window.handleInputKeydown       = handleInputKeydown;
window.handleSend               = handleSend;
window.showThread               = showThread;
