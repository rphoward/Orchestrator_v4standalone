/**
 * settings.js — Agent config, model registry, config export/import.
 */

import {
    buildModelOptions,
    buildThinkingOptions,
    modelSupportsThinking,
    renderAgentSettings,
    toggleThinking,
    saveAgentConfig,
    saveRouterModel,
    saveApiKey,
    updateBulkAssignPreview,
    applyBulkModelAssign,
} from './settings_agent.js';

import {
    renderRegistryTab,
    toggleModelStatus,
    deleteRegistryModel,
    saveRegistryModelCard,
    registerNewModel,
    saveFullRegistry,
    exportFullConfig,
    importFullConfig,
    importConfigFallback,
    applyRegistryFilters,
    setRegistryStatusFilter,
    runRegistryModelVerify,
    copyRegistryVerifyJson,
} from './settings_registry.js';

import {
    renderPromptsTab,
    savePromptTemplate,
    createPromptTemplate,
    duplicatePromptTemplate,
    deletePromptTemplateUI,
    applyPromptToAgent,
} from './settings_prompts.js';

// ── Modal open/close ─────────────────────────────────────────────

export function openSettings() {
    document.getElementById('settingsModal').classList.remove('hidden');
    switchSettingsTab('agents'); // always open on Agent Config
}

export function closeSettings() {
    document.getElementById('settingsModal').classList.add('hidden');
}

// ── Tab System ───────────────────────────────────────────────────

export function switchSettingsTab(tabName) {
    const tabs = ['agents', 'registry', 'prompts'];
    tabs.forEach(t => {
        const panel = document.getElementById(`settingsTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
        const btn   = document.getElementById(`tabBtn${t.charAt(0).toUpperCase() + t.slice(1)}`);
        if (panel) panel.classList.toggle('hidden', t !== tabName);
        if (btn)   btn.classList.toggle('active',  t === tabName);
    });

    if (tabName === 'agents')   renderAgentSettings();
    if (tabName === 'registry') renderRegistryTab();
    if (tabName === 'prompts')  renderPromptsTab();
}

// ── DOMContentLoaded: wire Import Config label ───────────────────
document.addEventListener('DOMContentLoaded', () => {
    const importLabel = document.querySelector('label[title="Restore settings from a previously exported config file"]');
    if (importLabel) {
        importLabel.addEventListener('click', (e) => {
            if (typeof window.showOpenFilePicker === 'function') {
                e.preventDefault();
                importFullConfig();
            }
        });
    }
});

// ── Window bindings for HTML onclicks ───────────────────────────────
window.openSettings          = openSettings;
window.closeSettings         = closeSettings;
window.switchSettingsTab     = switchSettingsTab;
window.saveRouterModel       = saveRouterModel;
window.saveAgentConfig       = saveAgentConfig;
window.toggleThinking        = toggleThinking;
window.renderRegistryTab     = renderRegistryTab;
window.toggleModelStatus     = toggleModelStatus;
window.deleteRegistryModel   = deleteRegistryModel;
window.saveRegistryModelCard = saveRegistryModelCard;
window.registerNewModel      = registerNewModel;
window.saveFullRegistry      = saveFullRegistry;
window.applyRegistryFilters    = applyRegistryFilters;
window.setRegistryStatusFilter = setRegistryStatusFilter;
window.runRegistryModelVerify  = runRegistryModelVerify;
window.copyRegistryVerifyJson  = copyRegistryVerifyJson;
window.updateBulkAssignPreview = updateBulkAssignPreview;
window.applyBulkModelAssign    = applyBulkModelAssign;
window.exportFullConfig      = exportFullConfig;
window.importFullConfig      = importFullConfig;
window.importConfigFallback  = importConfigFallback;
window.saveApiKey            = saveApiKey;
// Prompt Library
window.renderPromptsTab          = renderPromptsTab;
window.savePromptTemplate        = savePromptTemplate;
window.createPromptTemplate      = createPromptTemplate;
window.duplicatePromptTemplate   = duplicatePromptTemplate;
window.deletePromptTemplateUI    = deletePromptTemplateUI;
window.applyPromptToAgent        = applyPromptToAgent;

// Re-export for any module-level imports (keep public surface stable)
export {
    buildModelOptions,
    buildThinkingOptions,
    modelSupportsThinking,
    renderAgentSettings,
    toggleThinking,
    saveAgentConfig,
    saveRouterModel,
    saveApiKey,
    updateBulkAssignPreview,
    applyBulkModelAssign,
    renderRegistryTab,
    toggleModelStatus,
    deleteRegistryModel,
    saveRegistryModelCard,
    registerNewModel,
    saveFullRegistry,
    applyRegistryFilters,
    setRegistryStatusFilter,
    runRegistryModelVerify,
    copyRegistryVerifyJson,
    exportFullConfig,
    importFullConfig,
    importConfigFallback,
    renderPromptsTab,
    savePromptTemplate,
    createPromptTemplate,
    duplicatePromptTemplate,
    deletePromptTemplateUI,
    applyPromptToAgent,
};
