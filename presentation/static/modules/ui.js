/**
 * Cross-cutting interview UI shell — not a feature module.
 * Owns: toast bar, status bar, confirm modal — DOM chrome only, no interview rules.
 * See `.cursor/rules/orchestrator-screaming-presentation.mdc` for naming policy.
 */

import { ERROR_HINTS, escapeHtml } from './utils.js';

let _errorHideTimer = null;
let _statusHideTimer = null;
/** Bumps when status content changes or bar hides — stale auto-hide callbacks no-op. */
let _statusHideGen = 0;
/** Bumps when error content changes or bar hides — stale auto-hide callbacks no-op. */
let _errorHideGen = 0;

export function showStatus(text, icon = '⏳') {
    if (_statusHideTimer) {
        clearTimeout(_statusHideTimer);
        _statusHideTimer = null;
    }
    _statusHideGen++;
    document.getElementById('statusBar').classList.remove('hidden');
    document.getElementById('statusText').textContent = text;
    document.getElementById('statusIcon').textContent = icon;
}

export function hideStatus() {
    if (_statusHideTimer) {
        clearTimeout(_statusHideTimer);
        _statusHideTimer = null;
    }
    _statusHideGen++;
    document.getElementById('statusBar').classList.add('hidden');
}

/** Schedule auto-hide of the status toast; clears any previous hide timer. */
export function scheduleHideStatus(ms) {
    if (_statusHideTimer) clearTimeout(_statusHideTimer);
    const myGen = _statusHideGen;
    _statusHideTimer = setTimeout(() => {
        _statusHideTimer = null;
        if (myGen !== _statusHideGen) return;
        document.getElementById('statusBar').classList.add('hidden');
    }, ms);
}

export function showError(text, errorType) {
    /**
     * Contextual error display.
     * If we know the error_type, append a helpful hint so the user
     * knows what to do — not just what went wrong.
     */
    const hint = (errorType && ERROR_HINTS[errorType]) ? ERROR_HINTS[errorType] : '';

    if (_errorHideTimer) {
        clearTimeout(_errorHideTimer);
        _errorHideTimer = null;
    }
    _errorHideGen++;

    const errorBar  = document.getElementById('errorBar');
    const errorText = document.getElementById('errorText');
    const myGen = _errorHideGen;

    errorBar.classList.remove('hidden');
    errorText.innerHTML = escapeHtml(text) + (hint
        ? `<br><span class="text-xs opacity-75">${escapeHtml(hint)}</span>`
        : '');

    // Rate limit errors get a longer display time
    const timeout = errorType === 'rate_limit_error' ? 15000 : 8000;
    _errorHideTimer = setTimeout(() => {
        _errorHideTimer = null;
        if (myGen !== _errorHideGen) return;
        document.getElementById('errorBar').classList.add('hidden');
        _errorHideGen++;
    }, timeout);
}

export function hideError() {
    if (_errorHideTimer) {
        clearTimeout(_errorHideTimer);
        _errorHideTimer = null;
    }
    _errorHideGen++;
    document.getElementById('errorBar').classList.add('hidden');
}

export function showConfirm(t, m, fn) {
    document.getElementById('confirmTitle').textContent   = t;
    document.getElementById('confirmMessage').textContent = m;
    document.getElementById('confirmAction').onclick      = fn;
    document.getElementById('confirmModal').classList.remove('hidden');
}

export function closeConfirm() {
    document.getElementById('confirmModal').classList.add('hidden');
}

// ── Window bindings for HTML onclicks ───────────────────────────────
window.hideError    = hideError;
window.closeConfirm = closeConfirm;

export function confirmQuit() {
    showConfirm(
        'Quit Orchestrator?',
        'This will shut down the server. Any active interview data has already been saved. Close the browser tab after quitting.',
        async () => {
            closeConfirm();
            showStatus('Shutting down…', '⏻');
            try {
                await fetch('/api/shutdown', { method: 'POST' });
            } catch (_) {
                // Fetch will throw a network error once the server is down — that is expected.
            }
            document.body.innerHTML = `
                <div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;color:#6B6256;flex-direction:column;gap:12px">
                    <span style="font-size:2.5rem">⏻</span>
                    <p style="font-weight:600">Orchestrator shut down.</p>
                    <p style="font-size:0.85rem">You may close this tab.</p>
                </div>`;
        }
    );
}
window.confirmQuit = confirmQuit;
