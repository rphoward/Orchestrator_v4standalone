/**
 * sessions.js — Session lifecycle: create, select, delete, welcome screen.
 */

import { api, getJsonQuiet }                           from './api.js';
import { showStatus, hideStatus, showError, scheduleHideStatus } from './ui.js';
import { AGENT_ICONS, escapeHtml, escapeJsString }     from './utils.js';
import { downloadBlob }                                from './download.js';
import {
    agents,
    currentSessionId, setCurrentSessionId,
    setAgents,
} from './state.js';

// ── Lazy imports to avoid circular-dep at parse time ──────────────
// chat.js depends on sessions.js (for loadSessions), so we import
// chat functions lazily (at call time) via dynamic helpers.

/** Last GET /api/sessions — used for welcome “resume by client name”. */
let _sessionsSnapshot = [];

function _sessionsListUrl() {
    return '/api/sessions';
}
/** Selected bucket key in welcome resume step 2 (`__empty__` = no client name). */
let _welcomeSelectedClientKey = '';

function _hideSessionBoot() {
    document.getElementById('sessionBootPlaceholder')?.classList.add('hidden');
}

/** Show or hide the "Continue last session" strip on the welcome screen. */
function _refreshWelcomeContinueBar() {
    const bar = document.getElementById('welcomeContinueBar');
    const lab = document.getElementById('welcomeContinueLabel');
    if (!bar || !lab) return;
    const storedId = localStorage.getItem('currentSessionId');
    const s = storedId
        ? _sessionsSnapshot.find((x) => String(x.id) === storedId)
        : null;
    if (s) {
        lab.textContent = s.name || `Session ${s.id}`;
        bar.classList.remove('hidden');
    } else {
        bar.classList.add('hidden');
    }
}

function _hideConversationRestoreBanner() {
    document.getElementById('conversationRestoreBanner')?.classList.add('hidden');
}

function _showConversationRestoreBanner(message) {
    const el = document.getElementById('conversationRestoreBanner');
    const tx = document.getElementById('conversationRestoreBannerText');
    if (tx && message) tx.textContent = message;
    el?.classList.remove('hidden');
}

function _sessionTimeMs(s) {
    const t = s.updated_at || s.created_at;
    if (!t) return 0;
    const d = new Date(t);
    return Number.isNaN(d.getTime()) ? 0 : d.getTime();
}

function _clientKey(s) {
    const c = (s.client_name || '').trim();
    return c ? c.toLowerCase() : '__empty__';
}

function _clientLabelFromSession(s) {
    const c = (s.client_name || '').trim();
    return c || 'No client name';
}

/** Same rows as `GET .../conversations?agent_id=` (see session_routes filter). */
function _messagesForAgent(convos, agentId) {
    return (convos || []).filter((m) => Number(m.agent_id) === Number(agentId));
}

/** Resolve display name from loaded `/api/agents` (falls back when settings not yet loaded). */
function _agentNameFromState(agentId) {
    const a = (agents || []).find((x) => Number(x.id) === Number(agentId));
    return a?.name || `Agent ${agentId}`;
}

// ── Full-session transcript (chronological, read-only) ─────────────

let _transcriptMessages = [];

function _setTranscriptButtonEnabled(enabled) {
    const btn = document.getElementById('sessionTranscriptBtn');
    if (btn) btn.disabled = !enabled;
}

/** Same NaN-safe time extraction as `_sessionTimeMs`, for conversation rows. */
function _messageTimestampMs(m) {
    if (!m?.timestamp) return 0;
    const d = new Date(m.timestamp);
    return Number.isNaN(d.getTime()) ? 0 : d.getTime();
}

function _sortConversationsChronological(convos) {
    const copy = [...(convos || [])];
    copy.sort((a, b) => _messageTimestampMs(a) - _messageTimestampMs(b));
    return copy;
}

function _formatTranscriptTimestamp(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

/**
 * Refresh transcript cache from the server (e.g. after sending a message).
 * Uses getJsonQuiet so failures do not toast after an otherwise successful send.
 * @returns {Promise<boolean>} `true` if the server responded with usable JSON; `false` on network/HTTP failure.
 */
export async function refreshSessionTranscriptCache() {
    if (!currentSessionId) {
        _transcriptMessages = [];
        return true;
    }
    const raw = await getJsonQuiet(`/api/sessions/${currentSessionId}/conversations`);
    if (raw === null) return false;
    const convos = Array.isArray(raw) ? raw : [];
    _transcriptMessages = _sortConversationsChronological(convos);
    return true;
}

function _renderTranscriptRows(msgs) {
    return msgs
        .map((m) => {
            const aid        = m.agent_id;
            const icon       = AGENT_ICONS[String(aid)] ?? AGENT_ICONS[aid] ?? '🤖';
            const agentLabel = _agentNameFromState(aid);
            let roleLabel    = 'Assistant';
            if (m.role === 'user') roleLabel = 'User (consultant)';
            else if (m.role === 'system') roleLabel = 'System';
            const when = _formatTranscriptTimestamp(m.timestamp);
            const mt     = m.message_type || 'chat';
            return `
            <div class="transcript-row border-b border-themeBorder py-3 last:border-b-0">
                <div class="flex flex-wrap items-baseline gap-x-2 gap-y-1 mb-1.5 text-xs">
                    ${when ? `<span class="font-semibold text-themeAccent shrink-0">${escapeHtml(when)}</span>` : ''}
                    <span class="text-themeMuted">${escapeHtml(roleLabel)}</span>
                    <span class="text-themeText font-medium">${icon} ${escapeHtml(agentLabel)}</span>
                    <span class="px-1.5 py-0.5 rounded bg-themeSurface text-[10px] text-themeMuted uppercase border border-themeBorder">${escapeHtml(mt)}</span>
                </div>
                <div class="whitespace-pre-wrap text-themeText leading-relaxed text-sm">${escapeHtml(m.content || '')}</div>
            </div>`;
        })
        .join('');
}

export async function openSessionTranscript() {
    if (!currentSessionId) {
        showError('Select a session first.', 'validation_error');
        return;
    }
    const modal = document.getElementById('transcriptModal');
    const body  = document.getElementById('transcriptModalBody');
    if (!modal || !body) return;

    body.innerHTML =
        '<p class="text-themeMuted text-sm italic text-center py-8">Loading transcript…</p>';
    modal.classList.remove('hidden');

    const ok   = await refreshSessionTranscriptCache();
    const msgs = _transcriptMessages;

    if (!ok && msgs.length === 0) {
        body.innerHTML =
            '<p class="text-themeMuted text-sm text-center py-8 leading-relaxed">Could not load the transcript. Check your connection and try closing and reopening this panel.</p>';
        return;
    }
    if (msgs.length === 0) {
        body.innerHTML =
            '<p class="text-themeMuted text-sm italic text-center py-8">No messages in this session yet.</p>';
    } else {
        body.innerHTML = _renderTranscriptRows(msgs);
    }
}

export function closeSessionTranscript() {
    document.getElementById('transcriptModal')?.classList.add('hidden');
}

/**
 * Reuse `_sessionsSnapshot` when it already contains the target id to avoid an extra GET.
 * @param {string|number} id
 * @param {Array|undefined} explicit — when provided (including `[]`), caller controls the list source
 */
function _sessionsListForSelect(id, explicit) {
    if (explicit !== undefined) return explicit;
    const sid = String(id);
    return _sessionsSnapshot.some((s) => String(s.id) === sid)
        ? _sessionsSnapshot
        : null;
}

/** Group sessions by client for welcome resume UI. */
function _buildWelcomeClientBuckets() {
    const buckets = new Map();
    for (const s of _sessionsSnapshot) {
        const key = _clientKey(s);
        const label = _clientLabelFromSession(s);
        if (!buckets.has(key)) buckets.set(key, { key, label, sessions: [] });
        buckets.get(key).sessions.push(s);
    }
    for (const b of buckets.values()) {
        b.sessions.sort((a, b) => _sessionTimeMs(b) - _sessionTimeMs(a));
    }
    return [...buckets.values()].sort((a, b) =>
        a.label.localeCompare(b.label, undefined, { sensitivity: 'base' })
    );
}

function _renderWelcomeClientList(query) {
    const listEl = document.getElementById('welcomeResumeClientList');
    const emptyMsg = document.getElementById('welcomeResumeNoClients');
    if (!listEl || !emptyMsg) return;

    const q = String(query || '').trim().toLowerCase();
    const buckets = _buildWelcomeClientBuckets();
    const filtered = !q
        ? buckets
        : buckets.filter(
              (b) =>
                  b.label.toLowerCase().includes(q) ||
                  (b.key !== '__empty__' && b.key.includes(q))
          );

    if (filtered.length === 0) {
        listEl.innerHTML = '';
        if (_sessionsSnapshot.length === 0) {
            emptyMsg.classList.add('hidden');
        } else {
            emptyMsg.classList.remove('hidden');
        }
        return;
    }
    emptyMsg.classList.add('hidden');
    listEl.innerHTML = filtered
        .map(
            (b) => `
        <button type="button" onclick="selectWelcomeClient(${JSON.stringify(b.key)})"
                class="w-full text-left px-3 py-2.5 rounded-xl border border-themeBorder hover:bg-themeAccent/5 hover:border-themeAccent/30 transition-colors">
            <div class="text-sm font-semibold text-themeText">${escapeHtml(b.label)}</div>
            <div class="text-[10px] text-themeMuted uppercase tracking-wider">${b.sessions.length} session${b.sessions.length === 1 ? '' : 's'}</div>
        </button>`
        )
        .join('');
}

/** Update the current session ID and header title. */
export async function loadSessions() {
    try {
        const sessions = await api(_sessionsListUrl());
        _sessionsSnapshot = sessions;
        const list     = document.getElementById('sessionList');

        if (sessions.length === 0) {
            list.innerHTML = '<p class="text-themeMuted text-xs italic p-2 text-center">No active sessions.</p>';
            showWelcome();
            return;
        }

        list.innerHTML = sessions.map(s => _sessionItemHtml(s)).join('');

        // Always show the startup (welcome) screen on cold load when no session is
        // already selected in this tab. Silent auto-resume from localStorage hid the
        // welcome UI on every refresh — users could not reach "Ready for Discovery".
        // One-click "Continue last session" restores the old fast path (see below).
        if (!currentSessionId) {
            showWelcome();
        }

    } catch (err) {
        console.error('Failed to load sessions', err);
        showWelcome();
    } finally {
        _hideSessionBoot();
    }
}

/**
 * @param {number} id
 * @param {string} [name]
 * @param {{ sessions?: Array }} [options] — pass `sessions` from loadSessions to skip a duplicate GET /api/sessions
 */
export async function selectSession(id, name, options = {}) {
    closeContextModal();
    setCurrentSessionId(id);
    document.getElementById('currentSessionTitle').textContent = name || `Session ${id}`;

    let sessions = _sessionsListForSelect(id, options.sessions);
    if (sessions === null || sessions === undefined) {
        sessions = await api(_sessionsListUrl());
        _sessionsSnapshot = sessions;
    }
    const session  = sessions.find(s => s.id === id || String(s.id) === String(id));

    if (!session) {
        showError('Session not found. It may have been deleted.', 'validation_error');
        setCurrentSessionId(null);
        await loadSessions();
        return;
    }

    updateStageBadge(session.current_agent_id);
    updateHeaderStageDots(session);
    _setTranscriptButtonEnabled(true);

    // Sidebar privacy: activate when a session is selected
    _setSidebarPrivacyMode(true, session);

    const list = document.getElementById('sessionList');
    list.innerHTML = sessions.map(s => _sessionItemHtml(s)).join('');

    let convos = [];
    let convosFailed = false;
    try {
        convos = await api(`/api/sessions/${id}/conversations`);
    } catch (e) {
        console.error('Failed to load conversations', e);
        convosFailed = true;
        convos = [];
    }

    if (convosFailed) {
        _transcriptMessages = [];
    } else {
        _transcriptMessages = _sortConversationsChronological(convos);
    }

    const resumeAgentId = session.current_agent_id || 1;
    const { loadRoutingLogs, displayResponse, showThread } = await import('./chat.js');

    await loadRoutingLogs();
    document.getElementById('finalizeBtn').disabled = false;

    if (!convosFailed && convos.length > 0) {
        _hideConversationRestoreBanner();
        hideWelcome();

        const reversed = [...convos].reverse();
        const lastAssistant =
            reversed.find(m => m.role === 'assistant' && m.message_type === 'chat')
            || reversed.find(m => m.role === 'assistant' && m.agent_id === resumeAgentId)
            || reversed.find(m => m.role === 'assistant');
        if (lastAssistant) {
            const aid = lastAssistant.agent_id;
            const threadMsgs = _messagesForAgent(convos, aid);
            displayResponse(
                {
                    agent_id: aid,
                    agent_name: lastAssistant.agent_name || `Agent ${aid}`,
                    routing_reason: 'Resumed session',
                    response: lastAssistant.content,
                },
                { preloadedMessages: threadMsgs }
            );
        } else {
            const threadMsgs = _messagesForAgent(convos, resumeAgentId);
            showThread(resumeAgentId, { preloadedMessages: threadMsgs });
        }
    } else {
        // Restore_partial / empty: stay in ACTIVE_WORKSPACE with a non-blocking banner
        document.getElementById('responseSection')?.classList.add('hidden');
        hideWelcome();
        showThread(resumeAgentId);
        if (convosFailed) {
            _showConversationRestoreBanner(
                'Could not load conversation history. You can continue from here, or retry.'
            );
        } else {
            _showConversationRestoreBanner(
                "Session restored, but conversation history couldn't be loaded. You can continue, or retry."
            );
        }
    }
}

/**
 * Payload-driven session creation. Called by:
 *   - Welcome screen form   (passes its own input values)
 *   - Context Modal form    (passes modal input values)
 * No DOM scraping — callers own their own inputs.
 */
export async function startNewSession({ clientName, title } = {}) {
    if (!clientName) {
        showError('Please enter a Client / Project Name.', 'validation_error');
        return;
    }

    // Close the context modal if it is open
    closeContextModal();

    showStatus('Creating and initializing session...');
    try {
        const body = { client_name: clientName };
        if (title) body.name = title;

        const res = await api('/api/sessions', {
            method: 'POST',
            body:   JSON.stringify(body),
        });
        setCurrentSessionId(res.id);
        document.getElementById('currentSessionTitle').textContent = res.name;
        updateStageBadge(1);
        
        // Also ensure header stage dots are reset
        updateHeaderStageDots({
            stage1_complete: false, stage2_complete: false, 
            stage3_complete: false, stage4_complete: false
        });

        const initRes = await api(`/api/sessions/${res.id}/initialize`, { method: 'POST' });

        hideWelcome();
        document.getElementById('finalizeBtn').disabled = false;
        _setTranscriptButtonEnabled(true);

        // Activate sidebar privacy mode immediately — selectSession is skipped
        // by loadSessions() because currentSessionId is already set at this point.
        _setSidebarPrivacyMode(true, res);

        // Display the init response BEFORE loadSessions to avoid a race
        // where selectSession → loadThread fires again.
        const firstAgentResponse = initRes.agents && (initRes.agents['1'] || initRes.agents[1]);
        if (firstAgentResponse) {
            const { displayResponse } = await import('./chat.js');
            displayResponse({
                agent_id: 1,
                agent_name: _agentNameFromState(1),
                routing_reason: 'Session initialized',
                response: firstAgentResponse,
            });
        } else {
            console.warn('Init response had no agent 1 data:', JSON.stringify(initRes));
        }

        await loadSessions();
        const { loadRoutingLogs } = await import('./chat.js');
        await loadRoutingLogs();
        await refreshSessionTranscriptCache();
        hideStatus();
    } catch (err) {
        console.error('Session init failed:', err);
        hideStatus();
    }
}

/** Called by the welcome screen "Start New Session" button. */
export function submitWelcomeForm() {
    const clientName = document.getElementById('newClientName').value.trim();
    const title      = document.getElementById('newSessionName').value.trim();
    // Reset inputs so they're clean on next open
    document.getElementById('newClientName').value = '';
    document.getElementById('newSessionName').value = '';
    startNewSession({ clientName, title });
}

// ── Context Modal ────────────────────────────────────────────────

export async function openContextModal() {
    const modal = document.getElementById('contextModal');
    modal.classList.remove('hidden');

    // Populate the existing-sessions list
    const listEl = document.getElementById('contextSessionList');
    listEl.innerHTML = '<p class="text-xs text-themeMuted italic text-center py-2">Loading…</p>';
    try {
        const sessions = await api(_sessionsListUrl());
        if (sessions.length === 0) {
            listEl.innerHTML = '<p class="text-xs text-themeMuted italic text-center py-2">No past sessions.</p>';
        } else {
            _sessionsSnapshot = sessions;
            // Alphabetical sort by client_name (then by session name as tiebreak)
            const sorted = [...sessions].sort((a, b) => {
                const ca = (a.client_name || '').toLowerCase();
                const cb = (b.client_name || '').toLowerCase();
                if (ca < cb) return -1;
                if (ca > cb) return  1;
                return (a.name || '').toLowerCase().localeCompare((b.name || '').toLowerCase());
            });
            listEl.innerHTML = sorted.map(s => _contextSessionItemHtml(s)).join('');
        }
    } catch (err) {
        listEl.innerHTML = '<p class="text-xs text-red-500 text-center py-2">Failed to load sessions.</p>';
    }

    // Focus the client name input
    document.getElementById('contextClientName').focus();
}

export function closeContextModal() {
    const modal = document.getElementById('contextModal');
    if (modal) modal.classList.add('hidden');
}

/** Called by the context modal "Start Session" button. */
export function submitContextModal() {
    const clientName = document.getElementById('contextClientName').value.trim();
    const title      = document.getElementById('contextSessionTitle').value.trim();
    document.getElementById('contextClientName').value  = '';
    document.getElementById('contextSessionTitle').value = '';
    startNewSession({ clientName, title });
}

export async function deleteSession(event, id) {
    event.stopPropagation();
    if (!confirm('Delete this session permanently?')) return;
    try {
        await api(`/api/sessions/${id}`, { method: 'DELETE' });
        if (currentSessionId === id) setCurrentSessionId(null);
        // If the context modal is open, refresh its list; otherwise refresh the sidebar
        const modal = document.getElementById('contextModal');
        if (modal && !modal.classList.contains('hidden')) {
            openContextModal();
        } else {
            await loadSessions();
        }
    } catch (err) {
        console.error('Delete failed:', err);
    }
}

export function showWelcome() {
    _hideSessionBoot();
    _hideConversationRestoreBanner();
    document.getElementById('welcomeSection').classList.remove('hidden');
    document.getElementById('mainContent').classList.add('hidden');
    document.getElementById('finalizeBtn').disabled = true;
    _setTranscriptButtonEnabled(false);
    _transcriptMessages = [];
    _setSidebarPrivacyMode(false);

    welcomeResumeBack();
    const search = document.getElementById('welcomeResumeSearch');
    if (search) search.value = '';
    _renderWelcomeClientList('');
    _refreshWelcomeContinueBar();
}

/** Welcome-screen: resume the session id stored in localStorage (same as old auto-resume). */
export async function continueLastStoredSession() {
    const storedId = localStorage.getItem('currentSessionId');
    const s = storedId
        ? _sessionsSnapshot.find((x) => String(x.id) === storedId)
        : null;
    if (!s) {
        showError('No saved session to continue.', 'validation_error');
        return;
    }
    await selectSession(s.id, s.name, { sessions: _sessionsSnapshot });
}

export function hideWelcome() {
    _hideSessionBoot();
    document.getElementById('welcomeSection').classList.add('hidden');
    document.getElementById('mainContent').classList.remove('hidden');
}

/** Welcome “resume by client name”: search input handler (from HTML oninput). */
export function onWelcomeResumeSearchInput() {
    const v = document.getElementById('welcomeResumeSearch')?.value ?? '';
    _renderWelcomeClientList(v);
}

/** Step 2 → step 1 in welcome resume flow. */
export function welcomeResumeBack() {
    _welcomeSelectedClientKey = '';
    document.getElementById('welcomeResumeStep1')?.classList.remove('hidden');
    document.getElementById('welcomeResumeStep2')?.classList.add('hidden');
    document.getElementById('welcomeResumeNoSessions')?.classList.add('hidden');
}

/**
 * Pick a client bucket (key from _buildWelcomeClientBuckets) and show sessions.
 * @param {string} key
 */
export function selectWelcomeClient(key) {
    _welcomeSelectedClientKey = key;
    const buckets = _buildWelcomeClientBuckets();
    const bucket = buckets.find(b => b.key === key);
    if (!bucket) return;

    document.getElementById('welcomeResumeStep1')?.classList.add('hidden');
    document.getElementById('welcomeResumeStep2')?.classList.remove('hidden');
    const heading = document.getElementById('welcomeResumeClientHeading');
    if (heading) heading.textContent = bucket.label;

    const listEl = document.getElementById('welcomeResumeSessionList');
    const emptySess = document.getElementById('welcomeResumeNoSessions');
    if (!listEl) return;

    if (bucket.sessions.length === 0) {
        listEl.innerHTML = '';
        emptySess?.classList.remove('hidden');
        return;
    }
    emptySess?.classList.add('hidden');

    const fmtDate = (s) => {
        const t = s.updated_at || s.created_at;
        if (!t) return '';
        const d = new Date(t);
        if (Number.isNaN(d.getTime())) return '';
        return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
    };

    listEl.innerHTML = bucket.sessions
        .map((s) => {
            const when = fmtDate(s);
            const sub = when ? `<div class="text-[10px] text-themeMuted">${escapeHtml(when)}</div>` : '';
            const safeName = escapeJsString(s.name);
            return `
            <button type="button" onclick="selectSession(${s.id}, ${safeName})"
                    class="w-full text-left px-3 py-2.5 rounded-xl border border-themeBorder hover:bg-themeAccent/5 hover:border-themeAccent/30 transition-colors">
                <div class="text-sm font-semibold text-themeText">${escapeHtml(s.name)}</div>
                ${sub}
            </button>`;
        })
        .join('');
}

/** Retry loading conversation after a partial restore (banner). */
export function retryConversationLoad() {
    if (!currentSessionId) return;
    const title = document.getElementById('currentSessionTitle')?.textContent || '';
    selectSession(currentSessionId, title, { sessions: _sessionsSnapshot });
}

/**
 * Shows the active interview stage index (from session `current_agent_id` or send `current_gate`).
 * @param {number|string} stageId
 */
export function updateStageBadge(stageId) {
    const badge = document.getElementById('currentStageBadge');
    if (stageId) {
        badge.textContent = `Stage: ${stageId}`;
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

export function updateHeaderStageDots(session) {
    const container = document.getElementById('headerStageDots');
    if (!container) return; // For safety if missing down the line

    if (!session) { 
        container.classList.add('hidden'); 
        return; 
    }
    
    container.classList.remove('hidden');
    
    const stages = [
        { label: 'Brand',    done: session.stage1_complete },
        { label: 'Founder',  done: session.stage2_complete },
        { label: 'Customer', done: session.stage3_complete },
        { label: 'Arch',     done: session.stage4_complete },
    ];
    
    container.innerHTML = stages.map(st =>
        `<span class="stage-dot ${st.done ? 'done' : 'pending'}" title="${st.label}: ${st.done ? 'Complete' : 'Pending'}"></span>`
    ).join('');
    
    const finalizeBtn = document.getElementById('finalizeBtn');
    const isReady = stages.every(st => st.done);
    if (isReady) {
        finalizeBtn.classList.add('ring-2', 'ring-green-500', 'bg-teal-900');
        finalizeBtn.innerHTML = '📋 Finalize Report <span class="ml-2 px-1 text-[9px] bg-green-500 text-white rounded">READY</span>';
    } else {
        finalizeBtn.classList.remove('ring-2', 'ring-green-500', 'bg-teal-900');
        finalizeBtn.innerHTML = '📋 Finalize Report';
    }
}

export async function refreshHeaderState() {
    if (!currentSessionId) return;
    try {
        const sessions = await api(_sessionsListUrl());
        const session = sessions.find(s => s.id === currentSessionId);
        if (session) {
            updateStageBadge(session.current_agent_id);
            updateHeaderStageDots(session);
        }
    } catch(e) {}
}

/**
 * Align manual agent tabs + active thread with `session.current_agent_id`.
 * Auto-route uses that field as the router anchor; call when turning Auto-Route on so the
 * UI matches what the next `/send` will use (not the last manual tab click).
 */
export async function syncActiveThreadToSessionCurrentAgent() {
    if (!currentSessionId) return;
    try {
        const sessions = await api(_sessionsListUrl());
        const session = sessions.find((s) => s.id === currentSessionId);
        const aid = session?.current_agent_id;
        if (aid == null || aid < 1) return;
        const { selectAgent, showThread } = await import('./chat.js');
        selectAgent(aid);
        await showThread(aid);
    } catch (e) {
        console.warn('syncActiveThreadToSessionCurrentAgent failed:', e);
    }
}

export async function loadAgents() {
    try {
        const data = await api('/api/agents');
        setAgents(data);
        _syncAgentLabelsToDom(data);
    } catch (e) {
        console.error('Failed to load agents', e);
    }
}

// ── Private helpers ──────────────────────────────────────────────

function _syncAgentLabelsToDom(agentList) {
    if (!Array.isArray(agentList) || agentList.length === 0) return;

    const nameById = new Map(agentList.map((a) => [String(a.id), a.name]));
    const ids = Array.from(nameById.keys());

    // Manual selector agent tabs
    document.querySelectorAll('[data-agent]').forEach((btn) => {
        const id = String(btn.dataset.agent);
        if (!ids.includes(id)) return;
        btn.textContent = `${AGENT_ICONS[id] || AGENT_ICONS[Number(id)] || '🤖'} ${nameById.get(id) || ('Agent ' + id)}`;
    });

    // Thread tabs
    document.querySelectorAll('[data-thread]').forEach((btn) => {
        const id = String(btn.dataset.thread);
        if (!ids.includes(id)) return;
        btn.textContent = `${AGENT_ICONS[id] || AGENT_ICONS[Number(id)] || '🤖'} ${nameById.get(id) || ('Agent ' + id)}`;
    });
}

/**
 * Toggle sidebar privacy mode.
 * isActive=true  → hide session list, show active-session card (no client names visible)
 * isActive=false → show session list, hide card (FIRST_LAUNCH / no session)
 */
function _setSidebarPrivacyMode(isActive, session) {
    const list       = document.getElementById('sessionList');
    const activeCard = document.getElementById('activeSidebarSession');
    if (!list || !activeCard) return; // guard during early init

    if (isActive && session) {
        list.classList.add('hidden');
        activeCard.classList.remove('hidden');
        document.getElementById('sidebarSessionName').textContent = session.name        || '';
        document.getElementById('sidebarClientName').textContent  = session.client_name || '';
    } else {
        activeCard.classList.add('hidden');
        list.classList.remove('hidden');
    }
}

function _sessionItemHtml(s) {
    const isActive = s.id === currentSessionId;
    return `
        <div class="flex flex-col p-2 rounded-lg cursor-pointer transition-colors group ${isActive
            ? 'bg-themeAccent/10 text-themeAccent border border-themeAccent/30 shadow-sm'
            : 'text-themeText hover:bg-themeSurface border border-transparent'
        }" onclick="selectSession(${s.id}, ${escapeJsString(s.name)})">
            <div class="flex items-center justify-between">
                <div class="truncate text-sm font-bold flex-1 pr-2">${escapeHtml(s.name)}</div>
                <button onclick="deleteSession(event, ${s.id})" class="hidden group-hover:block text-themeMuted hover:text-red-600 text-lg leading-none" title="Delete">&times;</button>
            </div>
            ${s.client_name ? `<div class="text-[10px] text-themeMuted uppercase tracking-wider font-semibold truncate">${escapeHtml(s.client_name)}</div>` : ''}
        </div>
    `;
}


function _contextSessionItemHtml(s) {
    const safeName   = escapeJsString(s.name);
    const clientLine = s.client_name
        ? `<div class="text-[10px] text-themeMuted uppercase tracking-wider font-bold truncate">${escapeHtml(s.client_name)}</div>`
        : '';

    // Summary line (AI-generated if present, else empty)
    const summaryLine = s.summary
        ? `<div class="text-[11px] text-themeMuted italic truncate mt-0.5" title="${escapeHtml(s.summary)}">${escapeHtml(s.summary)}</div>`
        : '';

    // 4 stage completion dots
    const stages = [
        { label: 'Brand',    done: s.stage1_complete },
        { label: 'Founder',  done: s.stage2_complete },
        { label: 'Customer', done: s.stage3_complete },
        { label: 'Arch',     done: s.stage4_complete },
    ];
    const stageDots = stages.map(st =>
        `<span class="stage-dot ${st.done ? 'done' : 'pending'}" title="${st.label}: ${st.done ? 'Complete' : 'Pending'}"></span>`
    ).join('');

    return `
        <div class="context-session-card group" onclick="selectSession(${s.id}, ${safeName})">
            <div class="flex items-start justify-between gap-2 min-w-0">
                <div class="min-w-0 flex-1">
                    <div class="text-sm font-semibold text-themeText truncate">${escapeHtml(s.name)}</div>
                    ${clientLine}
                    ${summaryLine}
                </div>
                <div class="flex items-center gap-1.5 shrink-0">
                    <button
                        onclick="exportSession(event, ${s.id}, ${safeName})"
                        class="opacity-0 group-hover:opacity-100 transition-opacity text-themeMuted hover:text-themeAccent
                               w-5 h-5 flex items-center justify-center rounded text-sm leading-none"
                        title="Export session">⬇</button>
                    <button
                        onclick="deleteSession(event, ${s.id})"
                        class="opacity-0 group-hover:opacity-100 transition-opacity text-themeMuted hover:text-red-500
                               w-5 h-5 flex items-center justify-center rounded text-sm leading-none"
                        title="Delete session">&times;</button>
                    <span class="text-[10px] text-themeAccent font-bold opacity-0 group-hover:opacity-100 transition-opacity">Resume →</span>
                </div>
            </div>
            <div class="flex items-center gap-1 mt-1.5">
                ${stageDots}
            </div>
        </div>
    `;
}
export async function exportSession(event, id, name) {
    event.stopPropagation();
    let data;
    try {
        data = await api(`/api/sessions/${id}/export`);
    } catch (e) { return; }

    const dateStr       = new Date().toISOString().split('T')[0];
    const safeName      = name.replace(/[^a-z0-9]/gi, '-').toLowerCase() || 'session';
    const suggestedName = `${safeName}-export-${dateStr}.json`;
    const json          = JSON.stringify(data, null, 2);

    if (typeof window.showSaveFilePicker === 'function') {
        try {
            const handle   = await window.showSaveFilePicker({
                suggestedName,
                types: [{ description: 'JSON Session File', accept: { 'application/json': ['.json'] } }],
            });
            const writable = await handle.createWritable();
            await writable.write(json);
            await writable.close();
            showStatus(`Exported: ${handle.name}`, '✅');
            scheduleHideStatus(3000);
        } catch (err) {
            if (err.name === 'AbortError') return;
            downloadBlob({ data: json, filename: suggestedName, type: 'application/json' });
            showStatus(`Exported to Downloads: ${suggestedName}`, '✅');
            scheduleHideStatus(3000);
        }
    } else {
        downloadBlob({ data: json, filename: suggestedName, type: 'application/json' });
        showStatus(`Exported to Downloads: ${suggestedName}`, '✅');
        scheduleHideStatus(3000);
    }
}

export async function importSession() {
    if (typeof window.showOpenFilePicker === 'function') {
        try {
            const [handle] = await window.showOpenFilePicker({
                types:    [{ description: 'JSON Session File', accept: { 'application/json': ['.json'] } }],
                multiple: false,
            });
            const file = await handle.getFile();
            const text = await file.text();
            await _applyImportedSession(text, file.name);
        } catch (err) {
            if (err.name === 'AbortError') return;
            showError('Could not open file: ' + err.message);
        }
    } else {
        // Fallback file input
        let input = document.getElementById('importSessionFallback');
        if (!input) {
            input = document.createElement('input');
            input.type = 'file';
            input.id = 'importSessionFallback';
            input.accept = '.json';
            input.style.display = 'none';
            input.addEventListener('change', async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                const text = await file.text();
                e.target.value = ''; // reset
                await _applyImportedSession(text, file.name);
            });
            document.body.appendChild(input);
        }
        input.click();
    }
}

async function _applyImportedSession(jsonText, filename) {
    let parsed;
    try {
        parsed = JSON.parse(jsonText);
    } catch (e) {
        showError('Invalid JSON file. Could not parse session.', 'validation_error');
        return;
    }

    if (!parsed.orchestrator_export || parsed.orchestrator_export.type !== 'session') {
        showError('Not a valid Orchestrator session export file.', 'validation_error');
        return;
    }

    const sName = parsed.session?.name || 'Unknown';

    const confirmed = confirm(
        `Import session "${sName}"?\n\n` +
        `This will create a new session ending with [Imported].\n`
    );
    if (!confirmed) return;

    try {
        const res = await api('/api/sessions/import', {
            method: 'POST',
            body:   JSON.stringify(parsed),
        });
        showStatus('Session imported.', '✅');
        scheduleHideStatus(2000);
        
        // Refresh context modal
        const modal = document.getElementById('contextModal');
        if (modal && !modal.classList.contains('hidden')) {
            await openContextModal();
        } else {
            await loadSessions();
        }
    } catch (e) { /* error toast handled by api() */ }
}

// ── Window bindings for HTML onclicks ───────────────────────────────
window.startNewSession    = startNewSession;     // payload-driven (new canonical)
window.submitWelcomeForm  = submitWelcomeForm;   // welcome screen button
window.openContextModal   = openContextModal;    // + button
window.closeContextModal  = closeContextModal;
window.submitContextModal = submitContextModal;  // context modal start button
window.selectSession      = selectSession;
window.deleteSession      = deleteSession;
window.exportSession      = exportSession;
window.importSession      = importSession;
window.onWelcomeResumeSearchInput = onWelcomeResumeSearchInput;
window.selectWelcomeClient = selectWelcomeClient;
window.welcomeResumeBack  = welcomeResumeBack;
window.retryConversationLoad = retryConversationLoad;
window.continueLastStoredSession = continueLastStoredSession;
window.openSessionTranscript  = openSessionTranscript;
window.closeSessionTranscript = closeSessionTranscript;
