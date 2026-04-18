/**
 * reports.js — Finalize flow, triage modal, report modal, download.
 */

import { api }                            from './api.js';
import { showStatus, hideStatus, showError, showConfirm, closeConfirm } from './ui.js';
import { AGENT_ICONS, escapeHtml, formatMarkdown } from './utils.js';
import { downloadBlob }                   from './download.js';
import { agents, currentSessionId, currentReport, setCurrentReport } from './state.js';

function _grandSynthesisFilename() {
    const day = new Date().toISOString().split('T')[0];
    const sid = currentSessionId != null ? String(currentSessionId) : 'unknown';
    return `Grand-Synthesis-session-${sid}-${day}.md`;
}

// ── Finalization ─────────────────────────────────────────────────

export function showFinalizeConfirm() {
    showConfirm(
        'Finalize Interview?',
        'This will ask each agent to summarize their findings and generate the Architecture Specification.',
        () => startFinalize(false)
    );
}

export async function startFinalize(force = false) {
    if (!currentSessionId) return;
    closeConfirm();
    closeTriage();
    showStatus('Evaluating agent readiness & summarizing...');
    document.getElementById('finalizeBtn').disabled = true;

    try {
        const result = await api(`/api/sessions/${currentSessionId}/finalize`, {
            method: 'POST',
            body:   JSON.stringify({ force }),
        });

        if (result.status === 'warning') {
            hideStatus();
            document.getElementById('finalizeBtn').disabled = false;
            showTriageModal(result.sparse_agents);
            return;
        }

        setCurrentReport(result);
        if (result.errors?.length > 0) {
            showError('Some agents had issues: ' + result.errors.join('; '));
        }
        showReport(result);
    } catch (err) {
        console.error(err);
    } finally {
        hideStatus();
        document.getElementById('finalizeBtn').disabled = false;
    }
}

// ── Triage Modal ─────────────────────────────────────────────────

export function showTriageModal(sparse) {
    const list = document.getElementById('triageAgentList');
    list.innerHTML = sparse.map(a => `<li>${AGENT_ICONS[a.id]} ${escapeHtml(a.name)}</li>`).join('');
    document.getElementById('triageModal').classList.remove('hidden');
}

export function closeTriage() {
    document.getElementById('triageModal').classList.add('hidden');
}

export function forcePartialReport() {
    startFinalize(true);
}

// ── Report Modal ─────────────────────────────────────────────────

export function showReport(r) {
    document.getElementById('reportModal').classList.remove('hidden');
    document.getElementById('reportContent').innerHTML = formatMarkdown(r.synthesis || 'No synthesis generated.');

    const nameById = new Map((agents || []).map((a) => [String(a.id), a.name]));
    document.getElementById('payloadsContent').innerHTML = Object.entries(r.payloads || {}).map(([id, txt]) => `
        <div class="bg-themeSurface rounded-lg p-3 border border-themeBorder">
            <h4 class="text-xs font-bold text-themeAccent mb-1 uppercase">${AGENT_ICONS[id] || '🤖'} ${nameById.get(String(id)) || 'Agent ' + id}</h4>
            <div class="text-xs text-themeText whitespace-pre-wrap">${formatMarkdown(txt)}</div>
        </div>
    `).join('');
}

export function closeReport() {
    document.getElementById('reportModal').classList.add('hidden');
}

/** Primary finalize download: Grand Synthesis only (markdown). */
export function downloadReport() {
    if (!currentReport) return;
    const text = currentReport.synthesis ?? '';
    downloadBlob({ data: text, filename: _grandSynthesisFilename(), type: 'text/markdown' });
}

/** Optional archival download: per-agent payloads + synthesis (legacy single .txt). */
export function downloadFullBundleReport() {
    if (!currentReport) return;
    const nameById = new Map((agents || []).map((a) => [String(a.id), a.name]));
    let t = 'INTERVIEW ORCHESTRATOR - FINAL REPORT\n' + '='.repeat(50) +
        `\nGenerated: ${new Date().toLocaleString()}\n\n`;
    for (const [id, c] of Object.entries(currentReport.payloads || {})) {
        t += `\n--- ${nameById.get(String(id)) || 'Agent ' + id} ---\n${c}\n`;
    }
    t += '\n\n' + '='.repeat(50) + '\nGRAND SYNTHESIS\n' + '='.repeat(50) + `\n\n${currentReport.synthesis || ''}`;

    const day = new Date().toISOString().split('T')[0];
    const sid = currentSessionId != null ? String(currentSessionId) : 'unknown';
    downloadBlob({
        data:     t,
        filename: `Interview-full-bundle-session-${sid}-${day}.txt`,
        type:     'text/plain',
    });
}

// ── Window bindings for HTML onclicks ───────────────────────────────
window.showFinalizeConfirm = showFinalizeConfirm;
window.closeTriage         = closeTriage;
window.forcePartialReport  = forcePartialReport;
window.closeReport              = closeReport;
window.downloadReport           = downloadReport;
window.downloadFullBundleReport = downloadFullBundleReport;
