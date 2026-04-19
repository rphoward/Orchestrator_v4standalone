/**
 * app.js — Entry point for Interview Orchestrator Frontend.
 *
 * Thin orchestrator: imports all feature modules (which self-register
 * their window.* bindings) then bootstraps the app on DOMContentLoaded.
 *
 * Module tree:
 *   app.js
 *   ├── modules/ui.js                        (toast/confirm chrome)
 *   ├── modules/interview_ui_press_feedback.js (optional UI click sounds)
 *   ├── modules/api.js                       (fetch wrapper, loadModels)
 *   ├── modules/sessions.js                  (session CRUD, welcome screen)
 *   ├── modules/chat.js                      (send, threads, routing log)
 *   ├── modules/reports.js                   (finalize, triage, report modal)
 *   └── modules/settings.js                  (agent config, model registry, export/import)
 *
 * All modules share state via modules/state.js.
 * No build step required — loaded as <script type="module">.
 */

import './modules/ui.js';
import { initUiFeedback } from './modules/interview_ui_press_feedback.js';
import { loadModels } from './modules/api.js';
import { loadAgents, loadSessions } from './modules/sessions.js';
import './modules/chat.js';
import './modules/reports.js';
import './modules/settings.js';

document.addEventListener('DOMContentLoaded', () => {
    initUiFeedback();

    // Enable send button only when input has content
    const input = document.getElementById('messageInput');
    input.addEventListener('input', () => {
        document.getElementById('sendBtn').disabled = !input.value.trim();
    });

    // Bootstrap data — toggle after session restore may complete
    loadModels();
    loadAgents();
    loadSessions().then(() => {
        window.toggleAutoRoute();
    });
});
