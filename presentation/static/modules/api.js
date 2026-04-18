/**
 * api.js — HTTP layer.
 * Provides the api() helper and the loadModels() bootstrapper.
 */

import { showError }       from './ui.js';
import { setModelRegistry } from './state.js';

/**
 * Typed fetch wrapper.
 * - Preserves error_type from the backend so showError() can display contextual hints.
 * - Re-throws so callers can catch and do cleanup (e.g. hideStatus).
 */
export async function api(url, options = {}) {
    try {
        const { headers: userHeaders, body, ...rest } = options;
        const headers = { ...(userHeaders || {}) };
        const hasJsonBody =
            body != null &&
            body !== '' &&
            !(typeof FormData !== 'undefined' && body instanceof FormData);
        if (hasJsonBody && !headers['Content-Type'] && !headers['content-type']) {
            headers['Content-Type'] = 'application/json';
        }
        const response = await fetch(url, {
            ...rest,
            body,
            headers,
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const err       = new Error(errorData.error || `Server error: ${response.status}`);
            err.errorType   = errorData.error_type || 'unknown_error';
            err.status      = response.status;
            throw err;
        }
        return await response.json();
    } catch (err) {
        showError(err.message, err.errorType);
        throw err;
    }
}

/**
 * GET JSON without error toasts — for background sync where failure must not
 * interrupt the user (e.g. transcript cache refresh after a successful send).
 * @returns {Promise<any|null>} Parsed JSON, or `null` if the request failed.
 */
export async function getJsonQuiet(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            console.warn('getJsonQuiet: non-OK', response.status, url);
            return null;
        }
        return await response.json();
    } catch (e) {
        console.error('getJsonQuiet failed', url, e);
        return null;
    }
}

/** sessionStorage key for Settings → Model Registry → Check names with Google (must match Agents tab reader). */
export const VERIFY_MODEL_IDS_STORAGE_KEY = 'orchestrator_verify_models_v1';

/**
 * POST /api/config/verify-model-ids — preflight against Google models.list + deprecations.md.
 * Does not use api() (no global error toast); callers render their own UI.
 */
export async function postVerifyModelIds() {
    const response = await fetch('/api/config/verify-model-ids', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        const err = new Error(data.error || `Server error: ${response.status}`);
        err.status = response.status;
        err.errorType = data.error_type || 'unknown_error';
        throw err;
    }
    return data;
}

/** Fetches and caches the full model registry into shared state. */
export async function loadModels() {
    try {
        const data = await api('/api/models');
        setModelRegistry(data);
    } catch (e) {
        console.error('Failed to load model registry', e);
        setModelRegistry([]);
    }
}
