/**
 * settings_registry.js — Model Registry tab + config export/import.
 * Split out of settings.js to keep concerns isolated.
 */
import {
    api,
    loadModels,
    postVerifyModelIds,
    VERIFY_MODEL_IDS_STORAGE_KEY,
} from './api.js';
import { showStatus, hideStatus, showError, scheduleHideStatus } from './ui.js';
import { downloadBlob } from './download.js';
import { escapeHtml, normalizeSettingsTemperature } from './utils.js';
import { modelRegistry, agents } from './state.js';
import { loadAgents } from './interview_sessions_panel.js';
import { renderAgentSettings } from './settings_agent.js';
import { renderPromptsTab } from './settings_prompts.js';

function _statusOf(m) {
    const s = String(m?.status || '').toLowerCase();
    if (s === 'active') return 'active';
    if (s === 'deprecated') return 'deprecated';
    if (s === 'unlisted') return 'unlisted';
    // Back-compat: treat unknown as deprecated (non-active)
    return 'deprecated';
}

function _agentsReferencingModel(modelId) {
    const id = String(modelId || '').trim();
    if (!id) return [];
    return (agents || []).filter(a => a?.model === id);
}

function _formatAgentNames(agentList) {
    if (!agentList || agentList.length === 0) return '';
    return agentList
        .map(a => a?.name ? `${a.name}` : `Agent ${a?.id ?? '?'}`)
        .join(', ');
}

function _renderVerifyResults(container, data) {
    if (!container || !data) return;
    const esc = escapeHtml;
    const parts = [];

    if (data.error) {
        parts.push(`
            <div class="rounded-lg border border-red-200 bg-red-50 text-red-900 text-sm p-3 space-y-1">
                <div class="font-semibold">Could not complete check</div>
                <p class="text-xs leading-relaxed">${esc(String(data.error))}</p>
            </div>`);
        container.innerHTML = parts.join('');
        return;
    }

    if (data.unknown && data.unknown.length > 0) {
        const usageLines = data.unknown.map((id) => {
            const srcs = (data.usages && data.usages[id]) || [];
            const where = srcs.length ? `<ul class="mt-1 ml-4 list-disc text-xs">${srcs.map((s) => `<li>${esc(s)}</li>`).join('')}</ul>` : '';
            return `<li class="font-mono text-xs mt-2">${esc(id)}${where}</li>`;
        });
        parts.push(`
            <div class="rounded-lg border border-red-200 bg-red-50 text-red-900 p-3 space-y-2 mb-2">
                <div class="font-semibold text-sm">These IDs are not in the list returned for your key</div>
                <p class="text-xs leading-relaxed">If you did not mistype, Google may have retired or renamed the model—compare with current docs.</p>
                <ul class="list-none pl-0">${usageLines.join('')}</ul>
            </div>`);
    } else {
        const n = Array.isArray(data.known) ? data.known.length : 0;
        parts.push(`
            <div class="rounded-lg border border-green-200 bg-green-50 text-green-900 text-sm p-3 mb-2">
                <span class="font-semibold">All clear.</span>
                <span class="text-xs block mt-1 leading-relaxed">All ${n} model ID(s) in use appear in the current list for your key. Preview IDs can change—re-check after Google updates.</span>
            </div>`);
    }

    if (data.maintenance_warnings && data.maintenance_warnings.length > 0) {
        const rows = data.maintenance_warnings.map((w) => {
            const srcs = (w.sources && w.sources.length)
                ? `<div class="text-[10px] mt-1 text-amber-900/80">${esc(w.sources.join(' · '))}</div>`
                : '';
            return `<li class="text-xs mt-2">
                <span class="font-mono font-semibold">${esc(w.id)}</span>
                <div class="text-[11px] mt-0.5">Shutdown: ${esc(w.shutdown || '—')} · Replacement: ${esc(w.replacement || '—')}</div>
                ${srcs}
            </li>`;
        });
        parts.push(`
            <div class="rounded-lg border border-amber-200 bg-amber-50 text-amber-950 p-3 space-y-2">
                <div class="font-semibold text-sm">Schedule maintenance</div>
                <p class="text-xs leading-relaxed">Google has published shutdown dates (or &quot;coming soon&quot;) for models you still use. Plan a migration when convenient.</p>
                <ul class="list-none pl-0">${rows.join('')}</ul>
                <a href="https://ai.google.dev/gemini-api/docs/deprecations" target="_blank" rel="noopener noreferrer" class="text-xs text-themeAccent font-medium hover:underline">Open Gemini deprecations (Google)</a>
                <p class="text-[10px] text-amber-900/70 leading-snug">Amber uses Google&apos;s public deprecations.md; format may drift. Re-run Check after release notes.</p>
            </div>`);
    }

    parts.push(`
        <div class="flex flex-wrap gap-2 mt-2 text-xs text-gray-500">
            <span>Checked: ${esc(data.checked_at || '')}</span>
            <button type="button" class="text-themeAccent hover:underline font-medium" onclick="copyRegistryVerifyJson()">Copy diagnostic JSON</button>
        </div>`);

    container.innerHTML = parts.join('');
}

/** Called from HTML onclick; bound on window from settings.js */
export async function runRegistryModelVerify() {
    const region = document.getElementById('registryVerifyResults');
    if (!region) return;
    region.innerHTML = `
        <div class="flex items-center gap-2 text-sm text-gray-600 py-2">
            <span class="inline-block w-4 h-4 border-2 border-themeAccent border-t-transparent rounded-full animate-spin" aria-hidden="true"></span>
            <span>Contacting Google…</span>
        </div>`;
    try {
        const data = await postVerifyModelIds();
        if (!data.error && data.checked_at) {
            try {
                sessionStorage.setItem(VERIFY_MODEL_IDS_STORAGE_KEY, JSON.stringify(data));
            } catch (_) { /* ignore quota */ }
        }
        _renderVerifyResults(region, data);
    } catch (e) {
        region.innerHTML = `
            <div class="rounded-lg border border-red-200 bg-red-50 text-red-900 text-sm p-3">
                <div class="font-semibold">Request failed</div>
                <p class="text-xs mt-1">${escapeHtml(e.message || String(e))}</p>
            </div>`;
    }
}

export function copyRegistryVerifyJson() {
    try {
        const raw = sessionStorage.getItem(VERIFY_MODEL_IDS_STORAGE_KEY);
        if (!raw) return;
        const obj = JSON.parse(raw);
        const text = JSON.stringify(obj, null, 2);
        navigator.clipboard.writeText(text).then(() => {
            showStatus('Diagnostic JSON copied.', '✅');
            scheduleHideStatus(2000);
        }).catch(() => showError('Could not copy to clipboard'));
    } catch (_) {
        showError('Nothing to copy yet—run Check first.');
    }
}

function _registryCardHtml(m, i) {
    const status = _statusOf(m);
    const badgeClass = status === 'active' ? 'active' : (status === 'unlisted' ? 'unlisted' : 'deprecated');
    const badgeText = status === 'active' ? 'Active' : (status === 'unlisted' ? 'Unlisted' : 'Deprecated');
    return `
        <div class="registry-model-card" data-registry-index="${i}">
            <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-2">
                    <span class="registry-status-badge ${badgeClass}">
                        ${badgeText}
                    </span>
                    <span class="text-xs font-mono text-gray-500">${escapeHtml(m.id)}</span>
                </div>
                <button onclick="deleteRegistryModel(${i})" class="text-red-400 hover:text-red-600 text-sm" title="Remove model">🗑</button>
            </div>

            <div class="grid grid-cols-2 gap-3 mb-3">
                <div>
                    <label class="block text-xs text-gray-400 mb-1">API Model ID</label>
                    <input type="text" value="${escapeHtml(m.id)}" data-reg="id" data-idx="${i}" class="w-full font-mono">
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Display Label</label>
                    <input type="text" value="${escapeHtml(m.label)}" data-reg="label" data-idx="${i}" class="w-full">
                </div>
            </div>

            <p class="text-[10px] font-bold text-gray-500 uppercase tracking-wide mb-2">Assignment defaults</p>
            <div class="flex flex-wrap gap-4 mb-3 items-end">
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Thinking Support</label>
                    <select data-reg="supports_thinking" data-idx="${i}">
                        <option value="true"  ${m.supports_thinking  ? 'selected' : ''}>Yes</option>
                        <option value="false" ${!m.supports_thinking ? 'selected' : ''}>No</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Default Thinking</label>
                    <select data-reg="default_thinking" data-idx="${i}">
                        ${['OFF','MINIMAL','LOW','MEDIUM','HIGH'].map(v =>
                            `<option value="${v}" ${m.default_thinking === v ? 'selected' : ''}>${v}</option>`
                        ).join('')}
                    </select>
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Default Temp</label>
                    <input type="number" value="${m.default_temperature ?? 1.0}" data-reg="default_temperature" data-idx="${i}" min="0.1" max="2" step="0.1" title="0.1–2, numbers only">
                </div>
            </div>

            <details class="mb-3 border border-gray-100 rounded-lg open:border-themeAccent/20">
                <summary class="cursor-pointer text-xs font-semibold text-gray-600 px-3 py-2 select-none hover:bg-gray-50 rounded-lg">
                    Advanced metadata
                </summary>
                <div class="px-3 pb-3 pt-1 space-y-3 border-t border-gray-100">
                    <div class="flex flex-wrap gap-4 items-end">
                        <div>
                            <label class="block text-xs text-gray-400 mb-1">Max Output Tokens</label>
                            <input type="number" value="${m.max_output_tokens ?? 65536}" data-reg="max_output_tokens" data-idx="${i}" min="1" step="1">
                        </div>
                        <div>
                            <label class="block text-xs text-gray-400 mb-1">Context Window</label>
                            <input type="number" value="${m.context_window ?? 1000000}" data-reg="context_window" data-idx="${i}" min="1" step="1">
                        </div>
                    </div>
                    <div class="flex flex-wrap gap-4">
                        <label class="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
                            <input type="checkbox" data-reg="requires_thought_signatures" data-idx="${i}" ${m.requires_thought_signatures ? 'checked' : ''}>
                            Thought Signatures Required
                        </label>
                        <label class="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
                            <input type="checkbox" data-reg="include_thoughts_supported" data-idx="${i}" ${m.include_thoughts_supported ? 'checked' : ''}>
                            Include Thoughts Supported
                        </label>
                        <label class="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
                            <input type="checkbox" data-reg="media_resolution_supported" data-idx="${i}" ${m.media_resolution_supported ? 'checked' : ''}>
                            Media Resolution Supported
                        </label>
                    </div>
                    <div>
                        <label class="block text-xs text-gray-400 mb-1">Notes</label>
                        <input type="text" value="${escapeHtml(m.notes || '')}" data-reg="notes" data-idx="${i}" class="w-full" placeholder="Deprecation date, usage notes...">
                    </div>
                </div>
            </details>

            <div class="flex items-center justify-between mt-2 pt-2 border-t border-gray-100">
                <div class="flex gap-2 flex-wrap">
                    ${status === 'active'
                        ? `<button onclick="toggleModelStatus(${i}, 'deprecated')" class="btn-secondary text-xs text-orange-600 border-orange-200">⚠ Deprecate</button>`
                        : status === 'unlisted'
                            ? `
                                <button onclick="toggleModelStatus(${i}, 'deprecated')" class="btn-secondary text-xs text-orange-600 border-orange-200">⚠ Mark Deprecated</button>
                                <button onclick="toggleModelStatus(${i}, 'active')" class="btn-secondary text-xs text-green-600 border-green-200">✅ Reactivate</button>
                              `
                            : `<button onclick="toggleModelStatus(${i}, 'active')" class="btn-secondary text-xs text-green-600 border-green-200">✅ Reactivate</button>`
                    }
                </div>
                <button onclick="saveRegistryModelCard(${i})" class="btn-primary text-xs">Save</button>
            </div>
        </div>
        `;
}

/**
 * Show/hide model cards from search + filters (indices in modelRegistry unchanged).
 */
export function applyRegistryFilters() {
    const q = (document.getElementById('registrySearch')?.value || '').trim().toLowerCase();
    const statusFilter = document.getElementById('registryFilterStatus')?.value || 'all';
    const onlyThink = document.getElementById('registryFilterThinking')?.checked === true;
    const onlyInclude = document.getElementById('registryFilterIncludeThoughts')?.checked === true;

    document.querySelectorAll('.registry-model-card').forEach((card) => {
        const idx = parseInt(card.dataset.registryIndex, 10);
        if (Number.isNaN(idx) || idx < 0 || idx >= modelRegistry.length) {
            card.classList.add('hidden');
            return;
        }
        const m = modelRegistry[idx];
        if (!m) {
            card.classList.add('hidden');
            return;
        }

        const hay = `${m.id} ${m.label || ''} ${m.notes || ''}`.toLowerCase();
        const matchQ = !q || hay.includes(q);

        const st = _statusOf(m);
        let matchStatus = true;
        if (statusFilter === 'active') matchStatus = st === 'active';
        else if (statusFilter === 'deprecated') matchStatus = st === 'deprecated';
        else if (statusFilter === 'unlisted') matchStatus = st === 'unlisted';
        else if (statusFilter === 'nonactive') matchStatus = st !== 'active';

        const matchThink = !onlyThink || m.supports_thinking === true;
        const matchInclude = !onlyInclude || m.include_thoughts_supported === true;

        const show = matchQ && matchStatus && matchThink && matchInclude;
        card.classList.toggle('hidden', !show);
    });
}

/** Set status dropdown and re-apply filters (for summary chip clicks). */
export function setRegistryStatusFilter(value) {
    const sel = document.getElementById('registryFilterStatus');
    if (sel) sel.value = value;
    applyRegistryFilters();
}

export function renderRegistryTab() {
    const activeCount     = modelRegistry.filter(m => m.status === 'active').length;
    const deprecatedCount = modelRegistry.filter(m => m.status !== 'active').length;
    const c = document.getElementById('registrySettings');
    if (!c) return;

    const cards = modelRegistry.map((m, i) => _registryCardHtml(m, i)).join('');

    const filterBar = `
        <div class="registry-filter-bar mb-4 p-3 rounded-xl border border-gray-100 bg-white space-y-3">
            <div class="flex flex-col sm:flex-row gap-3 sm:items-end">
                <div class="flex-1 min-w-0">
                    <label class="block text-xs font-semibold text-gray-500 mb-1" for="registrySearch">Search models</label>
                    <input type="search" id="registrySearch" placeholder="ID, label, or notes…" autocomplete="off"
                           class="w-full text-sm p-2 border border-gray-200 rounded-lg"
                           oninput="applyRegistryFilters()">
                </div>
                <div>
                    <label class="block text-xs font-semibold text-gray-500 mb-1" for="registryFilterStatus">Status</label>
                    <select id="registryFilterStatus" class="text-sm p-2 border border-gray-200 rounded-lg" onchange="applyRegistryFilters()">
                        <option value="all">All</option>
                        <option value="active">Active</option>
                        <option value="nonactive">Non-active (deprecated + unlisted)</option>
                        <option value="deprecated">Deprecated</option>
                        <option value="unlisted">Unlisted</option>
                    </select>
                </div>
            </div>
            <div class="flex flex-wrap gap-4 text-xs text-gray-600">
                <label class="inline-flex items-center gap-2 cursor-pointer select-none">
                    <input type="checkbox" id="registryFilterThinking" onchange="applyRegistryFilters()">
                    Only models that support thinking
                </label>
                <label class="inline-flex items-center gap-2 cursor-pointer select-none">
                    <input type="checkbox" id="registryFilterIncludeThoughts" onchange="applyRegistryFilters()">
                    Only models with “include thoughts” supported
                </label>
            </div>
        </div>
    `;

    const newModelForm = `
        <div class="registry-new-model-card">
            <h3 class="text-sm font-bold text-themeAccent mb-3">+ Register New Model</h3>
            <p class="text-xs text-gray-500 mb-3">Enter the exact API model ID string from Google documentation. All other settings have smart defaults for current-generation Gemini models.</p>
            <div class="grid grid-cols-2 gap-3 mb-3">
                <div>
                    <label class="block text-xs text-gray-400 mb-1">API Model ID <span class="text-red-500">*</span></label>
                    <input type="text" id="newModelId" placeholder="e.g. gemini-4.0-flash" class="w-full font-mono">
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Display Label</label>
                    <input type="text" id="newModelLabel" placeholder="e.g. 4.0 Flash (Fast)" class="w-full">
                </div>
            </div>
            <div class="flex flex-wrap gap-4 mb-3 items-end">
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Thinking Support</label>
                    <select id="newModelThinkingSupport">
                        <option value="true" selected>Yes</option>
                        <option value="false">No</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Default Thinking</label>
                    <select id="newModelDefaultThinking">
                        <option value="OFF">OFF</option>
                        <option value="MINIMAL">MINIMAL</option>
                        <option value="LOW">LOW</option>
                        <option value="MEDIUM" selected>MEDIUM</option>
                        <option value="HIGH">HIGH</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Default Temp</label>
                    <input type="number" id="newModelTemp" value="1.0" min="0.1" max="2" step="0.1" title="0.1–2, numbers only">
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Max Output Tokens</label>
                    <input type="number" id="newModelMaxTokens" value="65536" min="1" step="1">
                </div>
            </div>
            <div id="newModelError" class="hidden text-xs text-red-600 mb-2"></div>
            <button onclick="registerNewModel()" class="btn-primary text-xs">Register Model</button>
        </div>
    `;

    c.innerHTML = `
        <div class="flex flex-col gap-2 mb-1">
            <p class="registry-summary text-sm">
                <span class="text-gray-600">${modelRegistry.length} models total</span>
                <span class="text-gray-400 mx-1">·</span>
                <button type="button" class="text-themeAccent hover:underline font-medium" onclick="setRegistryStatusFilter('active')" title="Show active models only">${activeCount} active</button>
                <span class="text-gray-400 mx-1">·</span>
                <button type="button" class="text-themeAccent hover:underline font-medium" onclick="setRegistryStatusFilter('nonactive')" title="Show deprecated and unlisted">${deprecatedCount} non-active</button>
            </p>
            <p class="text-xs text-gray-500 leading-relaxed">
                Model registry is curated here and in SQLite defaults. API model IDs must match names Google documents for Gemini; add or edit entries below—there is no live sync from Google.
            </p>
        </div>
        ${filterBar}
        <div class="registry-verify-panel mb-4 p-3 rounded-xl border border-gray-100 bg-white space-y-2">
            <div class="flex flex-wrap items-center gap-3">
                <button type="button" onclick="runRegistryModelVerify()" class="btn-secondary text-sm">Check names with Google</button>
                <span class="text-xs text-gray-500">Uses your saved GEMINI_API_KEY (models.list + public deprecations.md).</span>
            </div>
            <div id="registryVerifyResults" class="min-h-0"></div>
        </div>
        ${cards}
        ${newModelForm}
        <div class="flex justify-end mt-4 pt-3 border-t border-gray-100">
            <button onclick="saveFullRegistry()" class="btn-primary text-sm">💾 Save All Registry Changes</button>
        </div>
    `;
    applyRegistryFilters();
    const vr = document.getElementById('registryVerifyResults');
    if (vr) {
        try {
            const raw = sessionStorage.getItem(VERIFY_MODEL_IDS_STORAGE_KEY);
            if (raw) _renderVerifyResults(vr, JSON.parse(raw));
        } catch (_) { /* ignore */ }
    }
}

export function toggleModelStatus(index, newStatus) {
    if (index < 0 || index >= modelRegistry.length) return;
    const model = modelRegistry[index];
    if (!model) return;
    const label = model.label || model.id || 'this model';
    const referencedBy = _agentsReferencingModel(model?.id);
    if (referencedBy.length > 0) {
        const list = _formatAgentNames(referencedBy);
        const ok = confirm(
            `"${label}" is currently assigned to: ${list}\n\n` +
            `Change status to "${newStatus}" anyway?`
        );
        if (!ok) return;
    }
    modelRegistry[index].status = newStatus;
    saveFullRegistry().then((ok) => { if (ok) renderRegistryTab(); });
}

export function deleteRegistryModel(index) {
    if (index < 0 || index >= modelRegistry.length) return;
    const model = modelRegistry[index];
    if (!model) return;
    const label = model.label || model.id || 'this model';
    const referencedBy = _agentsReferencingModel(model?.id);
    if (referencedBy.length > 0) {
        const list = _formatAgentNames(referencedBy);
        const ok = confirm(
            `Remove "${label}" from the registry?\n\n` +
            `This model is still assigned to: ${list}.\n` +
            `Removing it may break those agents until you assign a different model in Agent Config.\n\n` +
            `Choose OK to remove from the registry anyway, or Cancel to keep it.`
        );
        if (!ok) return;
    } else {
        if (!confirm(`Remove "${label}" from the registry? This cannot be undone.`)) return;
    }
    modelRegistry.splice(index, 1);
    saveFullRegistry().then((ok) => { if (ok) renderRegistryTab(); });
}

export function saveRegistryModelCard(index) {
    if (index < 0 || index >= modelRegistry.length) return;
    const prev = modelRegistry[index];
    if (!prev) return;

    /** Read fields from this card only (avoids document-wide querySelector collisions). */
    const card = document.querySelector(`.registry-model-card[data-registry-index="${index}"]`);
    if (!card) {
        console.warn('saveRegistryModelCard: no card for index', index);
        return;
    }

    const get = (field) => {
        const el = card.querySelector(`[data-reg="${field}"]`);
        if (!el) return undefined;
        if (el.type === 'checkbox') return Boolean(el.checked);
        if (el.type === 'number') {
            const raw = String(el.value ?? '').trim();
            if (raw === '') return undefined;
            const n = parseFloat(raw);
            return Number.isFinite(n) ? n : undefined;
        }
        return el.value;
    };

    const idRaw = get('id');
    const labelRaw = get('label');
    const thinkingSel = get('supports_thinking');
    const defaultThinkingRaw = get('default_thinking');

    const nextTemp = normalizeSettingsTemperature(get('default_temperature') ?? '');
    const maxTok = get('max_output_tokens');
    const ctxWin = get('context_window');
    const reqSig = get('requires_thought_signatures');
    const incIncl = get('include_thoughts_supported');
    const mediaRes = get('media_resolution_supported');
    const notesVal = get('notes');

    modelRegistry[index] = {
        ...prev,
        id:                          (typeof idRaw === 'string' ? idRaw.trim() : '') || prev.id,
        label:                       (typeof labelRaw === 'string' ? labelRaw.trim() : '') || (typeof idRaw === 'string' ? idRaw.trim() : '') || prev.label,
        supports_thinking:           thinkingSel === 'true',
        default_thinking:            typeof defaultThinkingRaw === 'string' && defaultThinkingRaw
            ? defaultThinkingRaw
            : (prev.default_thinking || 'MEDIUM'),
        temperature_range:           prev.temperature_range || [0.0, 2.0],
        default_temperature:         nextTemp,
        max_output_tokens:           maxTok ?? 65536,
        context_window:              ctxWin ?? 1000000,
        requires_thought_signatures: reqSig === true,
        include_thoughts_supported:  incIncl === true,
        media_resolution_supported:  mediaRes === true,
        status:                      prev.status,
        output_modalities:           prev.output_modalities || ['text'],
        notes:                       typeof notesVal === 'string' ? notesVal : (prev.notes || ''),
    };

    const tempEl = card.querySelector('[data-reg="default_temperature"]');
    if (tempEl) tempEl.value = String(nextTemp);

    saveFullRegistry().then((ok) => {
        if (ok) {
            showStatus('Model saved.', '✅');
            scheduleHideStatus(2000);
        }
    });
}

export async function registerNewModel() {
    const id    = document.getElementById('newModelId')?.value.trim();
    const label = document.getElementById('newModelLabel')?.value.trim();
    const errEl = document.getElementById('newModelError');

    if (errEl) errEl.classList.add('hidden');

    if (!id) {
        if (errEl) {
            errEl.textContent = 'API Model ID is required.';
            errEl.classList.remove('hidden');
        }
        return;
    }
    if (modelRegistry.some(m => m.id === id)) {
        if (errEl) {
            errEl.textContent = `Model "${id}" already exists in the registry.`;
            errEl.classList.remove('hidden');
        }
        return;
    }

    modelRegistry.push({
        id,
        label:                       label || id,
        supports_thinking:           document.getElementById('newModelThinkingSupport')?.value === 'true',
        default_thinking:            document.getElementById('newModelDefaultThinking')?.value || 'MEDIUM',
        temperature_range:           [0.0, 2.0],
        default_temperature:         normalizeSettingsTemperature(document.getElementById('newModelTemp')?.value ?? ''),
        max_output_tokens:           parseInt(document.getElementById('newModelMaxTokens')?.value) || 65536,
        context_window:              1000000,
        requires_thought_signatures: true,
        include_thoughts_supported:  true,
        media_resolution_supported:  false,
        output_modalities:           ['text'],
        status:                      'active',
        notes:                       '',
    });

    const saved = await saveFullRegistry();
    if (!saved) return;
    renderRegistryTab();
    showStatus(`Model "${id}" registered.`, '✅');
    scheduleHideStatus(2500);
}

/** @returns {Promise<boolean>} true if persisted; false on validation failure or API error */
export async function saveFullRegistry() {
    const emptyIds = modelRegistry.filter(m => !m.id?.trim());
    if (emptyIds.length > 0) {
        showError('Every model must have an API Model ID.', 'validation_error');
        return false;
    }
    try {
        await api('/api/models', { method: 'PUT', body: JSON.stringify({ models: modelRegistry }) });
        return true;
    } catch (e) {
        return false;
    }
}

// ── Config Export / Import (File System Access API) ───────────────

/**
 * Export: uses showSaveFilePicker() for a real native Save As dialog.
 * Falls back to blob download if the API is unavailable (non-Chrome).
 */
export async function exportFullConfig() {
    let data;
    try {
        data = await api('/api/export-full-config');
    } catch (e) { return; }

    const dateStr       = new Date().toISOString().split('T')[0];
    const json          = JSON.stringify(data, null, 2);
    const suggestedName = `orchestrator-config-${dateStr}.json`;

    if (typeof window.showSaveFilePicker === 'function') {
        try {
            const handle   = await window.showSaveFilePicker({
                suggestedName,
                types: [{ description: 'JSON Config File', accept: { 'application/json': ['.json'] } }],
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

/**
 * Import: uses showOpenFilePicker() for a real native Open dialog.
 * Falls back to triggering the hidden <input type="file"> in the HTML.
 */
export async function importFullConfig() {
    if (typeof window.showOpenFilePicker === 'function') {
        try {
            const [handle] = await window.showOpenFilePicker({
                types:    [{ description: 'JSON Config File', accept: { 'application/json': ['.json'] } }],
                multiple: false,
            });
            const file = await handle.getFile();
            const text = await file.text();
            await _applyImportedConfig(text, file.name);
        } catch (err) {
            if (err.name === 'AbortError') return;
            showError('Could not open file: ' + err.message);
        }
    } else {
        document.getElementById('importFileFallback')?.click();
    }
}

/** Fallback handler called by the hidden <input type="file"> in the HTML */
export async function importConfigFallback(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    e.target.value = ''; // reset so same file can be re-selected
    await _applyImportedConfig(text, file.name);
}

/** Shared: parse, preview, confirm, and POST the config document */
async function _applyImportedConfig(jsonText, filename) {
    let parsed;
    try {
        parsed = JSON.parse(jsonText);
    } catch (e) {
        showError('Invalid JSON file. Could not parse config.', 'validation_error');
        return;
    }

    if (!parsed.orchestrator_config) {
        showError('Not a valid Orchestrator config file (missing header).', 'validation_error');
        return;
    }

    const agentCount = parsed.agents?.length ?? 0;
    const modelCount = parsed.model_registry?.length ?? 0;
    const exportedAt = parsed.orchestrator_config?.exported_at
        ? new Date(parsed.orchestrator_config.exported_at).toLocaleString()
        : 'unknown date';

    const confirmed = confirm(
        `Import config from "${filename}"?\n\n` +
        `• ${agentCount} agents\n` +
        `• ${modelCount} models in registry\n` +
        `• Exported: ${exportedAt}\n\n` +
        `This will replace your current agent configs, prompts, and model registry.\n` +
        `Export your current config first if you want a backup.`
    );
    if (!confirmed) return;

    try {
        const result = await api('/api/import-full-config', {
            method: 'POST',
            body:   JSON.stringify(parsed),
        });
        await loadModels();
        await loadAgents();
        // Re-render whichever tab is currently active
        const agentTabActive = !document.getElementById('settingsTabAgents').classList.contains('hidden');
        const registryTabActive = !document.getElementById('settingsTabRegistry').classList.contains('hidden');
        if (agentTabActive) renderAgentSettings();
        else if (registryTabActive) renderRegistryTab();
        else renderPromptsTab(); // Default to prompts if neither of the others is active
        showStatus(`Imported: ${result.agents_updated} agents, ${result.models_updated} models updated.`, '✅');
        scheduleHideStatus(4000);
    } catch (e) { /* api() already showed the error toast */ }
}

