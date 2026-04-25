/**
 * settings_agent.js — Agent Config tab + shared model dropdown helpers.
 * Split out of settings.js to keep concerns isolated.
 */
import { api, loadModels, VERIFY_MODEL_IDS_STORAGE_KEY } from './api.js';
import { showStatus, hideStatus, showError, scheduleHideStatus } from './ui.js';
import {
    escapeHtml,
    AGENT_ICONS,
    normalizeSettingsTemperature,
    SETTINGS_TEMP_MIN,
    SETTINGS_TEMP_MAX,
} from './utils.js';
import { modelRegistry, agents } from './state.js';
import { loadAgents } from './interview_sessions_panel.js';

// NOTE: localStorage key intentionally stable (UX relies on it).
const ADVANCED_TOGGLE_STORAGE_KEY = 'settings_agents_advanced';

/**
 * Agent temperature: '' clears override (use model default); otherwise quiet clamp via
 * normalizeSettingsTemperature (invalid text → default, out of range → clamp).
 */
function _normalizeAgentTemperatureField(raw) {
    const trimmed = String(raw ?? '').trim();
    if (trimmed === '') return '';
    return normalizeSettingsTemperature(raw);
}

function _getAgentAdvancedEnabled() {
    try {
        return localStorage.getItem(ADVANCED_TOGGLE_STORAGE_KEY) === 'true';
    } catch (_) {
        return false;
    }
}

function _setAgentAdvancedEnabled(v) {
    try {
        localStorage.setItem(ADVANCED_TOGGLE_STORAGE_KEY, v ? 'true' : 'false');
    } catch (_) {}
}

function _statusOf(m) {
    const s = String(m?.status || '').toLowerCase();
    if (s === 'active') return 'active';
    if (s === 'deprecated') return 'deprecated';
    if (s === 'unlisted') return 'unlisted';
    // Back-compat: treat unknown as deprecated (non-active)
    return 'deprecated';
}

function _readLastModelVerify() {
    try {
        const raw = sessionStorage.getItem(VERIFY_MODEL_IDS_STORAGE_KEY);
        if (!raw) return null;
        return JSON.parse(raw);
    } catch (_) {
        return null;
    }
}

function _routerModelVerifyNoteHtml(modelId) {
    const mid = String(modelId || '').trim();
    if (!mid) return '';
    const verify = _readLastModelVerify();
    if (!verify || verify.error) return '';
    let html = '';
    if ((verify.unknown || []).includes(mid)) {
        html += `<p class="text-[10px] text-red-700 mt-2 leading-snug">Router model was <strong>not</strong> in the last Google list check. Open <a href="#" onclick="switchSettingsTab('registry'); return false;" class="underline font-medium">Model Registry</a> and run Check names with Google.</p>`;
    }
    const mw = (verify.maintenance_warnings || []).find((w) => w.id === mid);
    if (mw) {
        html += `<p class="text-[10px] text-amber-900 mt-1 leading-snug">Deprecation notice for router: shutdown <strong>${escapeHtml(String(mw.shutdown || '—'))}</strong>. See <a href="https://ai.google.dev/gemini-api/docs/deprecations" target="_blank" rel="noopener noreferrer" class="underline">Google deprecations</a>.</p>`;
    }
    return html;
}

function _stageTrackingModeOptions(currentMode) {
    const selected = String(currentMode || 'hybrid').toLowerCase();
    const options = [
        ['hybrid', 'Hybrid'],
        ['semantic', 'Semantic'],
        ['off', 'Off'],
    ];
    return options.map(([value, label]) => (
        `<option value="${value}" ${selected === value ? 'selected' : ''}>${label}</option>`
    )).join('');
}

/** Maps GET/PUT `/api/config/stage-tracking` JSON to UI state (API uses `stage_*` keys). */
function _normalizedStageTrackingFromApi(data) {
    if (!data || typeof data !== 'object') {
        return { mode: 'hybrid', judge_interval_turns: 4 };
    }
    const mode = String(data.stage_tracking_mode ?? data.mode ?? 'hybrid').toLowerCase() || 'hybrid';
    const rawInterval = data.stage_tracking_judge_interval ?? data.judge_interval_turns;
    const parsed =
        rawInterval == null || rawInterval === ''
            ? 4
            : Number(rawInterval);
    const judge_interval_turns =
        Number.isFinite(parsed) && parsed > 0 ? parsed : 4;
    return { mode, judge_interval_turns };
}

function _stageTrackingSummary(settings, prefix = 'Current') {
    const mode = String(settings?.mode || 'hybrid').toLowerCase();
    const label = mode === 'semantic' ? 'Semantic' : mode === 'off' ? 'Off' : 'Hybrid';
    const interval = settings?.judge_interval_turns ?? '';
    const turnText = String(interval) === '1' ? 'turn' : 'turns';
    return `${prefix}: ${label}, judge interval ${interval} ${turnText}.`;
}

/**
 * Human-readable summary of what will run for this agent (model defaults vs overrides).
 */
function _effectiveConfigBlockHtml(agent, modelEntry, thinkingLevel, tempStr, includeThoughts) {
    const m = modelEntry;
    const st = m ? _statusOf(m) : 'unknown';
    const modelLabel = m ? m.label : agent.model;

    let thinkingLine = '';
    if (!m || !m.supports_thinking) {
        thinkingLine =
            'Thinking: <strong>Off</strong> <span class="text-gray-500">(this model does not support thinking)</span>';
    } else if (!thinkingLevel || String(thinkingLevel).trim() === '') {
        thinkingLine = `Thinking: <strong>Model default (${escapeHtml(m.default_thinking || 'MEDIUM')})</strong>`;
    } else {
        thinkingLine = `Thinking: <strong>${escapeHtml(String(thinkingLevel))}</strong> <span class="text-gray-500">(your override)</span>`;
    }

    let tempLine = '';
    if (!tempStr || String(tempStr).trim() === '') {
        const def = m ? Number(m.default_temperature ?? 1).toFixed(1) : '1.0';
        tempLine = `Temperature: <strong>Model default (${def})</strong>`;
    } else {
        tempLine = `Temperature: <strong>${escapeHtml(String(tempStr))}</strong> <span class="text-gray-500">(your override)</span>`;
    }

    const tracesLine = `Reasoning traces: <strong>${includeThoughts ? 'On' : 'Off'}</strong>`;

    let notes = '';
    if (m && st !== 'active') {
        const kind = st === 'deprecated' ? 'deprecated' : 'non-active';
        notes += `<p class="mt-2 text-amber-900 text-[10px] leading-snug">This model is marked <strong>${kind}</strong> in the registry. Prefer an active model for new interviews.</p>`;
    }
    if (includeThoughts && m && !m.include_thoughts_supported) {
        notes +=
            '<p class="mt-2 text-amber-900 text-[10px] leading-snug">Traces are on, but this model is not marked as supporting included thoughts in the registry—turn traces off or pick another model to avoid failures.</p>';
    }

    const verify = _readLastModelVerify();
    const effModelId = String(agent.model || '').trim();
    if (verify && !verify.error && effModelId) {
        if ((verify.unknown || []).includes(effModelId)) {
            notes += `<p class="mt-2 text-red-800 text-[10px] leading-snug">This model ID was not found in the last Google list check—fix it in <a href="#" onclick="switchSettingsTab('registry'); return false;" class="underline font-medium">Model Registry</a> or here, then run Check again.</p>`;
        }
        const mw = (verify.maintenance_warnings || []).find((w) => w.id === effModelId);
        if (mw) {
            notes += `<p class="mt-2 text-amber-900 text-[10px] leading-snug">Google lists a deprecation schedule for this model (shutdown: <strong>${escapeHtml(String(mw.shutdown || '—'))}</strong>). See <a href="https://ai.google.dev/gemini-api/docs/deprecations" target="_blank" rel="noopener noreferrer" class="underline">deprecations</a>.</p>`;
        }
    }

    return `
        <div class="mb-3 p-2 rounded-lg bg-gray-50 border border-gray-100 text-[11px] text-gray-700 leading-relaxed">
            <div class="font-semibold text-gray-600 mb-1">Effective configuration</div>
            <div><span class="text-gray-500">Model:</span> <strong>${escapeHtml(modelLabel)}</strong></div>
            <div class="mt-1">${thinkingLine}</div>
            <div class="mt-1">${tempLine}</div>
            <div class="mt-1">${tracesLine}</div>
            ${notes}
        </div>
    `;
}

export function buildModelOptions(selectedModel, opts = {}) {
    const includeDeprecated = opts.includeDeprecated === true;

    const active = [];
    const deprecated = [];
    const unlisted = [];

    for (const m of modelRegistry) {
        const s = _statusOf(m);
        if (s === 'active') active.push(m);
        else if (s === 'unlisted') unlisted.push(m);
        else deprecated.push(m);
    }

    const byLabel = (a, b) =>
        String(a?.label || a?.id || '').localeCompare(
            String(b?.label || b?.id || ''),
            undefined,
            { sensitivity: 'base' }
        );
    active.sort(byLabel);
    deprecated.sort(byLabel);
    unlisted.sort(byLabel);

    const allIds = modelRegistry.map(m => m.id);
    const selectedInRegistry = selectedModel && allIds.includes(selectedModel);
    const selectedModelEntry = selectedInRegistry ? modelRegistry.find(m => m.id === selectedModel) : null;
    const selectedStatus = selectedModelEntry ? _statusOf(selectedModelEntry) : null;

    let html = '';

    // Active (always)
    for (const m of active) {
        html += `<option value="${escapeHtml(m.id)}" ${selectedModel === m.id ? 'selected' : ''}>${escapeHtml(m.label)}</option>`;
    }

    // Deprecated / Unlisted (Agent Config: only when Advanced enabled)
    if (includeDeprecated) {
        if (deprecated.length > 0) {
            html += '<optgroup label="── Deprecated ──">';
            for (const m of deprecated) {
                html += `<option value="${escapeHtml(m.id)}" ${selectedModel === m.id ? 'selected' : ''}>${escapeHtml(m.label)}</option>`;
            }
            html += '</optgroup>';
        }
        if (unlisted.length > 0) {
            html += '<optgroup label="── Unlisted (review) ──">';
            for (const m of unlisted) {
                html += `<option value="${escapeHtml(m.id)}" ${selectedModel === m.id ? 'selected' : ''}>${escapeHtml(m.label)}</option>`;
            }
            html += '</optgroup>';
        }
    } else if (selectedModel && selectedStatus && selectedStatus !== 'active') {
        // Preserve current selection so we don’t “lose” it when Advanced is OFF.
        const labelPrefix = selectedStatus === 'unlisted' ? '🕳️ Unlisted' : '⚠️ Deprecated';
        html += `<optgroup label="── Not recommended ──">`;
        html += `<option value="${escapeHtml(selectedModel)}" selected>${labelPrefix}: ${escapeHtml(selectedModelEntry?.label || selectedModel)}</option>`;
        html += `</optgroup>`;
    }

    // Preserve unknown selections not in registry
    if (selectedModel && !allIds.includes(selectedModel)) {
        html += `<optgroup label="── Not in Registry ──">`;
        html += `<option value="${escapeHtml(selectedModel)}" selected>⚠️ ${escapeHtml(selectedModel)}</option>`;
        html += `</optgroup>`;
    }

    return html;
}

export function buildThinkingOptions(currentLevel) {
    return `
        <option value=""  ${!currentLevel          ? 'selected' : ''}>Off</option>
        <option value="LOW"    ${currentLevel === 'LOW'    ? 'selected' : ''}>Low</option>
        <option value="MEDIUM" ${currentLevel === 'MEDIUM' ? 'selected' : ''}>Medium (Default)</option>
        <option value="HIGH"   ${currentLevel === 'HIGH'   ? 'selected' : ''}>High</option>
    `;
}

export function modelSupportsThinking(modelId) {
    const model = modelRegistry.find(m => m.id === modelId);
    return model ? model.supports_thinking : false;
}

export async function renderAgentSettings() {
    await loadModels();
    const c = document.getElementById('agentSettings');

    const advancedEnabled = _getAgentAdvancedEnabled();

    let rModel = '';
    try {
        const routerData = await api('/api/config/router-model');
        rModel = routerData.model || '';
    } catch (err) {}

    let stageTrackingSettings = { mode: 'hybrid', judge_interval_turns: 4 };
    try {
        const res = await fetch('/api/config/stage-tracking');
        if (res.ok) {
            const stageData = await res.json();
            stageTrackingSettings = _normalizedStageTrackingFromApi(stageData);
        }
    } catch (_) {}

    let maskedKey = '';
    try {
        const keyData = await api('/api/config/api-key');
        maskedKey = keyData.masked_key || '';
    } catch (err) {}

    // Prefer one batch GET for overrides; fall back to per-agent GETs if the route is missing or errors.
    const tLevels = {};
    const temps = {};
    const includeThoughts = {};
    const ids = agents.map((a) => a.id).filter((id) => id != null);
    const qs = ids.length ? `?ids=${encodeURIComponent(ids.join(','))}` : '';
    let batchOk = false;
    try {
        const res = await fetch(`/api/config/agent-overrides${qs}`);
        if (res.ok) {
            const data = await res.json();
            const byId = data.agents || {};
            for (const a of agents) {
                const row = byId[String(a.id)] ?? byId[a.id];
                if (row && typeof row === 'object') {
                    tLevels[a.id] = row.thinking_level ?? '';
                    temps[a.id] = row.temperature ?? '';
                    includeThoughts[a.id] = !!row.include_thoughts;
                } else {
                    tLevels[a.id] = '';
                    temps[a.id] = '';
                    includeThoughts[a.id] = false;
                }
            }
            batchOk = true;
        }
    } catch (_) {
        /* fall through to per-agent */
    }
    if (!batchOk) {
        await Promise.all(agents.map(async (a) => {
            try {
                const tl = (await api(`/api/config/thinking-level/${a.id}`)).thinking_level;
                tLevels[a.id] = tl ?? '';
            } catch (e) { tLevels[a.id] = ''; }
            try {
                temps[a.id] = (await api(`/api/config/temperature/${a.id}`)).temperature ?? '';
            } catch (e) { temps[a.id] = ''; }
            try {
                includeThoughts[a.id] = (await api(`/api/config/include-thoughts/${a.id}`)).include_thoughts;
            } catch (e) { includeThoughts[a.id] = false; }
        }));
    }

    let html = `
        <div class="agent-config-card" style="border-left: 3px solid var(--color-muted, #6B7280); margin-bottom: 1.5rem;">
            <div class="flex items-center justify-between gap-3 mb-2">
                <div class="flex items-center gap-2">
                    <span class="text-xl">🧰</span>
                    <span class="font-semibold">Agent Config</span>
                    <span class="text-xs text-gray-400">(safe defaults; Advanced reveals deprecated/unlisted models)</span>
                </div>
                <label class="flex items-center gap-2 text-xs text-gray-600 cursor-pointer select-none">
                    <input type="checkbox" id="agentAdvancedToggle" ${advancedEnabled ? 'checked' : ''} class="accent-teal-700">
                    Advanced
                </label>
            </div>
            <div class="text-[11px] text-gray-500 flex items-center gap-3">
                <span class="inline-flex items-center gap-1"><span class="inline-block w-2 h-2 rounded-full" style="background:#16a34a"></span>Active</span>
                <span class="inline-flex items-center gap-1"><span class="inline-block w-2 h-2 rounded-full" style="background:#f59e0b"></span>Deprecated</span>
                <span class="inline-flex items-center gap-1"><span class="inline-block w-2 h-2 rounded-full" style="background:#64748b"></span>Unlisted</span>
            </div>
        </div>

        <div class="agent-config-card" style="border-left: 3px solid var(--color-danger, #DC2626); margin-bottom: 1.5rem;">
            <div class="flex items-center gap-2 mb-3">
                <span class="text-xl">🔑</span>
                <span class="font-semibold">Gemini API Key</span>
                <span class="text-xs text-gray-400">(Saved securely to local .env file)</span>
            </div>
            <div class="flex items-center gap-2">
                <input type="password" id="apiKeyInput" placeholder="${maskedKey ? escapeHtml(maskedKey) : 'Paste new Gemini API Key...'}" class="flex-1 text-sm font-mono p-2 border border-themeBorder rounded-md outline-none focus:ring-2 focus:ring-themeAccent transition-all">
                <button onclick="saveApiKey()" class="btn-primary text-xs whitespace-nowrap">Save Key</button>
            </div>
            <p class="text-xs text-gray-400 mt-2">
                This key is kept local. It is NOT stored in SQLite or included in config file exports.
            </p>
        </div>

        <div class="agent-config-card" style="border-left: 3px solid var(--color-teal, #0f766e); margin-bottom: 1.5rem;">
            <div class="flex items-center gap-2 mb-3">
                <span class="text-xl">📡</span>
                <span class="font-semibold">Router Model</span>
                <span class="text-xs text-gray-400">(classifies inputs → picks agent 1-4)</span>
            </div>
            <div class="flex items-center gap-2">
                <select id="routerModelSelect" class="flex-1 text-xs">
                    ${buildModelOptions(rModel, { includeDeprecated: advancedEnabled })}
                </select>
                <button onclick="saveRouterModel()" class="btn-primary text-xs">Save</button>
            </div>
            <p class="text-xs text-gray-400 mt-2">
                The Router strictly forces MINIMAL thinking in the backend for near-instant classification.
            </p>
            ${_routerModelVerifyNoteHtml(rModel)}
        </div>

        <div class="agent-config-card" style="border-left: 3px solid #7c3aed; margin-bottom: 1.5rem;">
            <div class="flex items-center gap-2 mb-3">
                <span class="text-xl">🧭</span>
                <span class="font-semibold">Stage Tracking</span>
                <span class="text-xs text-gray-400">(controls when stage completion is judged)</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                <label class="block text-xs text-gray-500">
                    <span class="block mb-1">Mode</span>
                    <select id="stageTrackingModeSelect" class="w-full text-xs p-2 border border-gray-200 rounded-md">
                        ${_stageTrackingModeOptions(stageTrackingSettings.mode)}
                    </select>
                </label>
                <label class="block text-xs text-gray-500">
                    <span class="block mb-1">Judge interval</span>
                    <input type="number" id="stageTrackingJudgeIntervalInput"
                           value="${escapeHtml(String(stageTrackingSettings.judge_interval_turns ?? ''))}"
                           min="1" step="1"
                           class="w-full text-xs p-2 border border-gray-200 rounded-md">
                </label>
            </div>
            <p class="text-xs text-gray-400 mb-2">
                Hybrid: judge after candidate completion, explicit advance, final report/export, or interval.
            </p>
            <div class="flex items-center justify-between gap-3">
                <p id="stageTrackingSaveResult" class="text-[11px] text-gray-500">${escapeHtml(_stageTrackingSummary(stageTrackingSettings))}</p>
                <button onclick="saveStageTrackingSettings()" class="btn-primary text-xs">Save</button>
            </div>
        </div>

        <div class="agent-config-card" style="border-left: 3px solid #0369a1; margin-bottom: 1.5rem;">
            <div class="flex items-center gap-2 mb-2">
                <span class="text-lg">📎</span>
                <span class="font-semibold">Bulk assign model</span>
            </div>
            <p class="text-xs text-gray-500 mb-3">
                Pick one model and apply it to several agents at once. Each agent keeps its current name and prompt; only the model (and thinking override if needed) is updated on the server.
            </p>
            <div class="mb-2">
                <label class="block text-xs text-gray-500 mb-1" for="bulkAssignModelSelect">Model to assign</label>
                <select id="bulkAssignModelSelect" class="w-full text-xs p-2 border border-gray-200 rounded-md" onchange="updateBulkAssignPreview()">
                    <option value="">— Select a model —</option>
                    ${buildModelOptions('', { includeDeprecated: advancedEnabled })}
                </select>
            </div>
            <div class="flex flex-wrap gap-3 mb-2" id="bulkAssignAgentCheckboxes">
                ${agents.map(a => `
                    <label class="inline-flex items-center gap-2 text-xs text-gray-700 cursor-pointer select-none">
                        <input type="checkbox" data-bulk-agent="${a.id}" checked onchange="updateBulkAssignPreview()">
                        <span>${escapeHtml(a.name || `Agent ${a.id}`)}</span>
                    </label>
                `).join('')}
            </div>
            <p id="bulkAssignPreview" class="text-[11px] text-gray-600 mb-2 min-h-[1.25rem]"></p>
            <button type="button" onclick="applyBulkModelAssign()" class="btn-primary text-xs">Apply to selected agents</button>
        </div>
    `;

    html += agents.map(a => {
        const supportsThinking = modelSupportsThinking(a.model);
        const tl   = tLevels[a.id] ?? '';
        const temp = temps[a.id] ?? '';
        const incl = includeThoughts[a.id] || false;
        const modelMeta = modelRegistry.find((x) => x.id === a.model);

        return `
        <div class="agent-config-card" data-config-id="${a.id}">
            ${_effectiveConfigBlockHtml(a, modelMeta, tl, temp, incl)}
            <div class="flex items-center gap-2 mb-3">
                <span class="text-xl">${AGENT_ICONS[a.id] || '🤖'}</span>
                <input type="text" value="${escapeHtml(a.name)}"
                       class="font-semibold flex-1"
                       data-field="name" data-agent="${a.id}">
            </div>
            <div class="flex items-center gap-2 mb-3">
                <label class="text-xs text-gray-500 w-20">Model:</label>
                <select data-field="model" data-agent="${a.id}"
                        class="flex-1 text-xs"
                        onchange="toggleThinking(${a.id}, this.value)">
                    ${buildModelOptions(a.model, { includeDeprecated: advancedEnabled })}
                </select>
            </div>
            <div class="flex items-center gap-2 mb-3" id="thinking-row-${a.id}"
                 style="display: ${supportsThinking ? 'flex' : 'none'}">
                <label class="text-xs text-gray-500 w-20">Thinking:</label>
                <select data-field="thinking" data-agent="${a.id}" class="flex-1 text-xs">
                    ${buildThinkingOptions(tl)}
                </select>
            </div>
            <div class="flex items-center gap-2 mb-3">
                <label class="text-xs text-gray-500 w-20">Temp:</label>
                <input type="number" data-field="temperature" data-agent="${a.id}"
                       value="${escapeHtml(String(temp))}"
                       min="${SETTINGS_TEMP_MIN}" max="${SETTINGS_TEMP_MAX}" step="0.1"
                       title="0.1–2, numbers only; leave empty for model default"
                       placeholder="Model default"
                       class="flex-1 text-xs">
                <span class="text-xs text-gray-400">${SETTINGS_TEMP_MIN}–${SETTINGS_TEMP_MAX}</span>
            </div>
            <div class="flex items-center gap-2 mb-3">
                <label class="text-xs text-gray-500 w-20">Thoughts:</label>
                <label class="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
                    <input type="checkbox" data-field="include_thoughts" data-agent="${a.id}"
                           ${incl ? 'checked' : ''}
                           class="accent-teal-700">
                    Include reasoning traces (debug mode)
                </label>
            </div>
            <textarea rows="8" data-field="prompt" data-agent="${a.id}"
                      placeholder="System prompt...">${escapeHtml(a.prompt || '')}</textarea>
            <div class="flex justify-end mt-2">
                <button onclick="saveAgentConfig(${a.id})" class="btn-primary text-xs">
                    Save Changes
                </button>
            </div>
        </div>
        `;
    }).join('');

    c.innerHTML = html;

    updateBulkAssignPreview();

    const adv = document.getElementById('agentAdvancedToggle');
    if (adv) {
        adv.addEventListener('change', () => {
            _setAgentAdvancedEnabled(!!adv.checked);
            renderAgentSettings();
        });
    }
}

/** Preview line for bulk model assignment (window binding from HTML). */
export function updateBulkAssignPreview() {
    const sel = document.getElementById('bulkAssignModelSelect');
    const modelId = sel?.value;
    const out = document.getElementById('bulkAssignPreview');
    if (!out) return;

    const checked = [...document.querySelectorAll('input[data-bulk-agent]:checked')];
    if (!modelId) {
        out.textContent = checked.length ? 'Choose a model to see a preview.' : '';
        return;
    }

    const m = modelRegistry.find((x) => x.id === modelId);
    const label = m ? m.label : modelId;
    const names = checked.map((cb) => {
        const id = parseInt(cb.dataset.bulkAgent, 10);
        const agent = agents.find((a) => a.id === id);
        return agent?.name || `Agent ${id}`;
    });

    if (names.length === 0) {
        out.textContent = 'Select at least one agent above.';
        return;
    }
    out.textContent = `Will set model "${label}" for: ${names.join(', ')}.`;
}

export async function applyBulkModelAssign() {
    const sel = document.getElementById('bulkAssignModelSelect');
    const modelId = sel?.value;
    if (!modelId) {
        showError('Choose a model from the list first.', 'validation_error');
        return;
    }
    const checked = [...document.querySelectorAll('input[data-bulk-agent]:checked')];
    if (checked.length === 0) {
        showError('Select at least one agent.', 'validation_error');
        return;
    }

    showStatus('Applying model to agents…', '⏳');
    try {
        for (const cb of checked) {
            const id = parseInt(cb.dataset.bulkAgent, 10);
            const card = document.querySelector(`[data-config-id="${id}"]`);
            if (!card) continue;
            const name = card.querySelector('[data-field="name"]')?.value ?? '';
            const prompt = card.querySelector('[data-field="prompt"]')?.value ?? '';
            await api(`/api/agents/${id}`, {
                method: 'PUT',
                body: JSON.stringify({ name, model: modelId, prompt }),
            });
            const supports = modelSupportsThinking(modelId);
            await api(`/api/config/thinking-level/${id}`, {
                method: 'PUT',
                body: JSON.stringify({
                    thinking_level: supports
                        ? (card.querySelector('[data-field="thinking"]')?.value || '')
                        : '',
                }),
            });
        }
        await loadAgents();
        await renderAgentSettings();
        showStatus('Bulk model applied.', '✅');
        scheduleHideStatus(2500);
    } catch (e) {
        console.error(e);
    } finally {
        hideStatus();
    }
}

export function toggleThinking(agentId, modelValue) {
    const row = document.getElementById(`thinking-row-${agentId}`);
    const supports = modelSupportsThinking(modelValue);
    if (row) row.style.display = supports ? 'flex' : 'none';

    // Decision: if model doesn't support thinking, auto-clear override to default ("")
    if (!supports) {
        const card = document.querySelector(`[data-config-id="${agentId}"]`);
        const thinkingSel = card?.querySelector('[data-field="thinking"]');
        if (thinkingSel) thinkingSel.value = '';
    }
}

export async function saveAgentConfig(id) {
    const card = document.querySelector(`[data-config-id="${id}"]`);
    if (!card) return;

    const tempInput = card.querySelector('[data-field="temperature"]');
    const tempValue = _normalizeAgentTemperatureField(tempInput?.value ?? '');
    if (tempInput) {
        if (tempValue === '') tempInput.value = '';
        else tempInput.value = String(tempValue);
    }

    try {
        const selectedModel = card.querySelector('[data-field="model"]').value;
        await api(`/api/agents/${id}`, { method: 'PUT', body: JSON.stringify({
            name:   card.querySelector('[data-field="name"]').value,
            model:  selectedModel,
            prompt: card.querySelector('[data-field="prompt"]').value,
        })});

        const supportsThinking = modelSupportsThinking(selectedModel);
        await api(`/api/config/thinking-level/${id}`, { method: 'PUT', body: JSON.stringify({
            thinking_level: supportsThinking
                ? (card.querySelector('[data-field="thinking"]')?.value || '')
                : '',
        })});

        await api(`/api/config/temperature/${id}`, { method: 'PUT', body: JSON.stringify({
            temperature: tempValue,
        })});

        const inclEl = card.querySelector('[data-field="include_thoughts"]');
        if (inclEl) {
            await api(`/api/config/include-thoughts/${id}`, { method: 'PUT', body: JSON.stringify({
                include_thoughts: inclEl.checked,
            })});
        }

        await loadAgents();
        showStatus('Saved.', '✅');
        scheduleHideStatus(2000);
    } catch (e) {}
}

export async function saveRouterModel() {
    try {
        await api('/api/config/router-model', { method: 'PUT', body: JSON.stringify({
            model: document.getElementById('routerModelSelect').value,
        })});
        showStatus('Saved.', '✅');
        scheduleHideStatus(2000);
    } catch (e) {}
}

export async function saveStageTrackingSettings() {
    const modeEl = document.getElementById('stageTrackingModeSelect');
    const intervalEl = document.getElementById('stageTrackingJudgeIntervalInput');
    try {
        const saved = await api('/api/config/stage-tracking', {
            method: 'PUT',
            body: JSON.stringify({
                stage_tracking_mode: modeEl?.value ?? '',
                stage_tracking_judge_interval: intervalEl?.value ?? '',
            }),
        });
        const norm = _normalizedStageTrackingFromApi(saved);
        if (modeEl) modeEl.value = norm.mode || 'hybrid';
        if (intervalEl) intervalEl.value = String(norm.judge_interval_turns ?? '');
        const result = document.getElementById('stageTrackingSaveResult');
        const summary = _stageTrackingSummary(norm, 'Saved');
        if (result) result.textContent = summary;
        showStatus(summary, '✅');
        scheduleHideStatus(2500);
    } catch (e) {}
}

export async function saveApiKey() {
    const input = document.getElementById('apiKeyInput');
    const val = input.value.trim();
    if (!val) {
        showError('Please enter an API key to save.', 'validation_error');
        return;
    }
    try {
        const res = await api('/api/config/api-key', {
            method: 'PUT',
            body: JSON.stringify({ api_key: val })
        });
        input.value = '';
        input.placeholder = res.masked_key;
        showStatus('API Key saved to .env', '✅');
        scheduleHideStatus(2000);
    } catch (e) {}
}

