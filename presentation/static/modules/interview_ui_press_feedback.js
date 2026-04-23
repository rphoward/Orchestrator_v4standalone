/**
 * Interview UI press feedback — optional short click sounds for primary controls.
 * Cross-cutting Settings chrome (localStorage + Web Audio); not session/agent domain logic.
 * Wired from app bootstrap so the checkbox is bound even if Settings is never opened.
 * See `.cursor/rules/orchestrator-presentation.mdc`.
 */

const LOCAL_STORAGE_KEY = 'orchestrator_v4_ui_sounds_enabled';

let _audioCtx = null;
let _soundsEnabled = false;
let _pointerBound = false;

function getAudioContext() {
    const Ctor = window.AudioContext || window.webkitAudioContext;
    if (!_audioCtx && Ctor) {
        _audioCtx = new Ctor();
    }
    return _audioCtx;
}

export function playUiClick() {
    const ctx = getAudioContext();
    if (!ctx) return;
    const t = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, t);
    osc.frequency.exponentialRampToValueAtTime(220, t + 0.04);
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(0.05, t + 0.003);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.055);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(t);
    osc.stop(t + 0.07);
}

function isOrInsideDisabled(el) {
    const btn = el.closest('button, [role="button"]');
    if (btn && (btn.disabled || btn.getAttribute('aria-disabled') === 'true')) {
        return true;
    }
    return Boolean(el.closest('fieldset[disabled]')) || Boolean(el.closest('[disabled]'));
}

function isSoundTarget(el) {
    if (isOrInsideDisabled(el)) return false;
    if (el.closest('.btn-primary, .btn-secondary, .btn-icon, .send-button')) return true;
    const tab = el.closest('.settings-tab');
    if (tab && !tab.classList.contains('active')) return true;
    return false;
}

function onPointerDown(ev) {
    if (!_soundsEnabled) return;
    if (!isSoundTarget(ev.target)) return;
    const ctx = getAudioContext();
    if (!ctx) return;
    ctx.resume().then(() => {
        playUiClick();
    });
}

function bindPointerIfNeeded() {
    if (_pointerBound) return;
    document.addEventListener('pointerdown', onPointerDown, true);
    _pointerBound = true;
}

function unbindPointer() {
    if (!_pointerBound) return;
    document.removeEventListener('pointerdown', onPointerDown, true);
    _pointerBound = false;
}

function readStorage() {
    try {
        return localStorage.getItem(LOCAL_STORAGE_KEY) === 'true';
    } catch {
        return false;
    }
}

function persistStorage(on) {
    try {
        localStorage.setItem(LOCAL_STORAGE_KEY, on ? 'true' : 'false');
    } catch {
        /* quota / private mode */
    }
}

export function initUiFeedback() {
    const box = document.getElementById('uiSoundsEnabled');
    if (!box || box.type !== 'checkbox') return;

    _soundsEnabled = readStorage();
    box.checked = _soundsEnabled;
    if (_soundsEnabled) bindPointerIfNeeded();

    box.addEventListener('change', () => {
        _soundsEnabled = box.checked;
        persistStorage(_soundsEnabled);
        if (_soundsEnabled) {
            bindPointerIfNeeded();
        } else {
            unbindPointer();
        }
    });
}
