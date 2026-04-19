/**
 * settings_prompts.js — Prompt Library tab.
 * Split out of settings.js to keep concerns isolated.
 */
import { api } from './api.js';
import { showStatus, hideStatus, showError, scheduleHideStatus } from './ui.js';
import { escapeHtml, AGENT_ICONS } from './utils.js';
import { agents } from './state.js';

/** In-memory cache of templates fetched from the server */
let _promptTemplates = [];

/**
 * Renders the full Prompt Library tab:
 *  - fetches all templates from GET /api/prompt-templates
 *  - renders each as an editable card
 *  - renders the "+ New Template" form at the bottom
 */
export async function renderPromptsTab() {
    const container = document.getElementById('promptsSettings');
    if (!container) return;
    container.innerHTML = '<p class="text-xs text-themeMuted">Loading prompt library...</p>';

    try {
        _promptTemplates = await api('/api/prompt-templates');
    } catch (e) {
        container.innerHTML = '<p class="text-xs text-red-500">Failed to load prompt templates.</p>';
        return;
    }

    const agentOptions = agents.map(a =>
        `<option value="${a.id}">${escapeHtml(AGENT_ICONS[a.id] || '')} ${escapeHtml(a.name)}</option>`
    ).join('');

    const cards = _promptTemplates.length === 0
        ? `<div class="prompt-empty-state">
               <div class="prompt-empty-icon">📭</div>
               <p>No prompt templates yet.</p>
               <p class="text-xs mt-1">Create your first one below.</p>
           </div>`
        : _promptTemplates.map((t, i) => {
            const targetName = t.target_agent_id
                ? (agents.find(a => a.id === t.target_agent_id)?.name || `Agent ${t.target_agent_id}`)
                : null;
            return `
            <div class="prompt-template-card" data-tmpl-id="${t.id}">
                <div class="flex items-start justify-between gap-2 mb-3">
                    <div class="flex-1 min-w-0">
                        <input type="text" value="${escapeHtml(t.name)}"
                               data-tmpl-field="name"
                               placeholder="Template name"
                               class="font-semibold text-sm mb-1">
                        <input type="text" value="${escapeHtml(t.description || '')}"
                               data-tmpl-field="description"
                               placeholder="Short description (optional)"
                               class="text-xs text-gray-500 mt-1">
                    </div>
                    <div class="flex items-center gap-1 shrink-0">
                        ${targetName ? `<span class="prompt-target-badge">${escapeHtml(targetName)}</span>` : ''}
                        <button onclick="duplicatePromptTemplate(${t.id})" class="btn-icon text-xs" title="Duplicate">
                            ⧉
                        </button>
                        <button onclick="deletePromptTemplateUI(${t.id})" class="btn-icon text-xs text-red-400 hover:text-red-600" title="Delete">
                            🗑
                        </button>
                    </div>
                </div>

                <div class="flex items-center gap-2 mb-2">
                    <label class="text-xs text-gray-500 shrink-0">Target agent:</label>
                    <select data-tmpl-field="target_agent_id" class="flex-1 text-xs">
                        <option value="">— Any agent —</option>
                        ${agentOptions}
                    </select>
                </div>

                <textarea data-tmpl-field="content"
                          placeholder="Paste or write your system prompt here..."
                          rows="8">${escapeHtml(t.content || '')}</textarea>

                <div class="flex items-center justify-between mt-3 pt-2 border-t border-gray-100">
                    <button onclick="applyPromptToAgent(${t.id})" class="btn-secondary text-xs">
                        ↗ Apply to Agent
                    </button>
                    <button onclick="savePromptTemplate(${t.id})" class="btn-primary text-xs">
                        Save
                    </button>
                </div>
            </div>`;
        }).join('');

    // Restore target_agent_id selects after innerHTML (can't set 'selected' reliably via option string for dynamic values)
    const newTemplateForm = `
        <div class="prompt-new-card" id="promptNewCard">
            <h3 class="text-sm font-bold text-themeAccent mb-3">+ New Template</h3>
            <div class="space-y-2">
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Name <span class="text-red-500">*</span></label>
                    <input type="text" id="newPromptName" placeholder="e.g. Deep Founder Extraction v2">
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Description</label>
                    <input type="text" id="newPromptDescription" placeholder="Short summary of this prompt's purpose">
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Target Agent (optional)</label>
                    <select id="newPromptAgent">
                        <option value="">— Any agent —</option>
                        ${agentOptions}
                    </select>
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1">System Prompt Content <span class="text-red-500">*</span></label>
                    <textarea id="newPromptContent" rows="8" placeholder="Paste your system prompt here..."></textarea>
                </div>
            </div>
            <div id="newPromptError" class="hidden text-xs text-red-600 mt-2"></div>
            <div class="flex justify-end mt-3">
                <button onclick="createPromptTemplate()" class="btn-primary text-xs">Create Template</button>
            </div>
        </div>
    `;

    container.innerHTML = `
        <p class="registry-summary">${_promptTemplates.length} template${_promptTemplates.length !== 1 ? 's' : ''} saved</p>
        ${cards}
        ${newTemplateForm}
    `;

    // Restore select values from data (innerHTML can't set selected on dynamic option values reliably)
    _promptTemplates.forEach((t) => {
        const card = container.querySelector(`[data-tmpl-id="${t.id}"]`);
        if (!card) return;
        const sel = card.querySelector('[data-tmpl-field="target_agent_id"]');
        if (sel && t.target_agent_id != null) sel.value = String(t.target_agent_id);
    });
}

/**
 * Reads current card fields and PUTs to /api/prompt-templates/:id
 */
export async function savePromptTemplate(templateId) {
    const card = document.querySelector(`[data-tmpl-id="${templateId}"]`);
    if (!card) return;

    const name        = card.querySelector('[data-tmpl-field="name"]')?.value.trim();
    const description = card.querySelector('[data-tmpl-field="description"]')?.value.trim();
    const content     = card.querySelector('[data-tmpl-field="content"]')?.value.trim();
    const agentSel    = card.querySelector('[data-tmpl-field="target_agent_id"]');
    const target_agent_id = agentSel?.value ? parseInt(agentSel.value, 10) : null;

    if (!name || !content) {
        showError('Template name and content are required.', 'validation_error');
        return;
    }

    try {
        await api(`/api/prompt-templates/${templateId}`, {
            method: 'PUT',
            body: JSON.stringify({ name, description, content, target_agent_id }),
        });
        showStatus('Template saved.', '✅');
        scheduleHideStatus(2000);
        await renderPromptsTab(); // re-render to sync badge
    } catch (e) { /* api() shows error toast */ }
}

/**
 * Creates a new template from the "+ New Template" form.
 */
export async function createPromptTemplate() {
    const name        = document.getElementById('newPromptName')?.value.trim();
    const description = document.getElementById('newPromptDescription')?.value.trim() || '';
    const content     = document.getElementById('newPromptContent')?.value.trim();
    const agentVal    = document.getElementById('newPromptAgent')?.value;
    const target_agent_id = agentVal ? parseInt(agentVal, 10) : null;
    const errEl       = document.getElementById('newPromptError');

    errEl?.classList.add('hidden');

    if (!name) {
        if (errEl) { errEl.textContent = 'Template name is required.'; errEl.classList.remove('hidden'); }
        return;
    }
    if (!content) {
        if (errEl) { errEl.textContent = 'System prompt content is required.'; errEl.classList.remove('hidden'); }
        return;
    }

    try {
        await api('/api/prompt-templates', {
            method: 'POST',
            body: JSON.stringify({ name, description, content, target_agent_id }),
        });
        showStatus(`Template "${name}" created.`, '✅');
        scheduleHideStatus(2500);
        await renderPromptsTab();
    } catch (e) { /* api() shows error toast */ }
}

/**
 * Duplicates an existing template (creates a copy with "(Copy)" suffix).
 */
export async function duplicatePromptTemplate(templateId) {
    const t = _promptTemplates.find(t => t.id === templateId);
    if (!t) return;
    try {
        await api('/api/prompt-templates', {
            method: 'POST',
            body: JSON.stringify({
                name:            `${t.name} (Copy)`,
                description:     t.description || '',
                content:         t.content,
                target_agent_id: t.target_agent_id,
            }),
        });
        showStatus('Template duplicated.', '✅');
        scheduleHideStatus(2000);
        await renderPromptsTab();
    } catch (e) { /* api() shows error toast */ }
}

/**
 * Deletes a template after confirmation.
 */
export async function deletePromptTemplateUI(templateId) {
    const t = _promptTemplates.find(t => t.id === templateId);
    const label = t?.name || 'this template';
    if (!confirm(`Delete "${label}"? This cannot be undone.`)) return;
    try {
        await api(`/api/prompt-templates/${templateId}`, { method: 'DELETE' });
        showStatus('Template deleted.', '✅');
        scheduleHideStatus(2000);
        await renderPromptsTab();
    } catch (e) { /* api() shows error toast */ }
}

/**
 * Applies a template's content to the target agent's prompt field.
 *
 * Strategy:
 *  1. Determine the target agent: use template's target_agent_id if set,
 *     otherwise use the current card's select value, otherwise ask the user
 *     to pick one (shows an alert telling them to set the target first).
 *  2. Save the template first (to persist any edits).
 *  3. PUT the new prompt content to /api/agents/:id.
 *  4. Invalidate agent cache and re-render the Agent Config tab.
 */
export async function applyPromptToAgent(templateId) {
    const card = document.querySelector(`[data-tmpl-id="${templateId}"]`);
    const t    = _promptTemplates.find(t => t.id === templateId);
    if (!t || !card) return;

    // Prefer the live select value over the stale DB value
    const agentSel = card.querySelector('[data-tmpl-field="target_agent_id"]');
    const agentId  = agentSel?.value ? parseInt(agentSel.value, 10) : t.target_agent_id;

    if (!agentId) {
        showError('Set a target agent before applying.', 'validation_error');
        return;
    }

    const agent = agents.find(a => a.id === agentId);
    const agentName = agent?.name || `Agent ${agentId}`;
    const templateName = t.name;

    if (!confirm(`Apply template "${templateName}" to ${agentName}?\n\nThis will overwrite ${agentName}'s current system prompt. Make sure to export your config first if you want a backup.`)) return;

    // Save any unsaved edits in the card before applying
    const content = card.querySelector('[data-tmpl-field="content"]')?.value.trim();
    if (!content) { showError('Cannot apply an empty prompt.', 'validation_error'); return; }

    try {
        await api(`/api/agents/${agentId}`, {
            method: 'PUT',
            body: JSON.stringify({ prompt: content }),
        });
        const { loadAgents } = await import('./interview_sessions_panel.js');
        await loadAgents();
        showStatus(`Applied to ${agentName}. Open Agent Config to review.`, '✅');
        scheduleHideStatus(4000);
    } catch (e) { /* api() shows error toast */ }
}

