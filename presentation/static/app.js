/**
 * app.js — Entry point for Interview Orchestrator Frontend.
 *
 * Thin orchestrator: imports all feature modules (which self-register
 * their window.* bindings) then bootstraps the app on DOMContentLoaded.
 *
 * Module tree:
 *   app.js
 *   ├── modules/ui.js                           (toast/confirm chrome)
 *   ├── modules/interview_ui_press_feedback.js  (optional UI click sounds)
 *   ├── modules/api.js                          (fetch wrapper, loadModels)
 *   ├── modules/interview_sessions_panel.js     (session CRUD, welcome screen,
 *   │                                            active stage pointer badge,
 *   │                                            stage status tracker dots)
 *   ├── modules/interview_chat_panel.js         (send, threads, routing log,
 *   │                                            auto-routing toggle)
 *   ├── modules/reports.js                      (finalize, triage, report modal)
 *   └── modules/settings.js                     (agent config, model registry, export/import)
 *
 * All modules share state via modules/state.js.
 * No build step required — loaded as <script type="module">.
 */

import './modules/ui.js';
import { initUiFeedback } from './modules/interview_ui_press_feedback.js';
import { loadModels } from './modules/api.js';
import { loadAgents, loadSessions } from './modules/interview_sessions_panel.js';
import './modules/interview_chat_panel.js';
import './modules/reports.js';
import './modules/settings.js';

document.addEventListener('DOMContentLoaded', () => {
    initUiFeedback();

    const input = document.getElementById('messageInput');
    input.addEventListener('input', () => {
        document.getElementById('sendBtn').disabled = !input.value.trim();
    });

    loadModels();
    loadAgents();
    loadSessions().then(() => {
        window.toggleAutoRouting();
    });
});
