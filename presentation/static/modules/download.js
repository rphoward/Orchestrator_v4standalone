/**
 * download.js — Tiny DOM-side-effect helpers (blob downloads).
 * Kept separate from utils.js (which is pure).
 */
 
export function downloadBlob({ data, filename, type }) {
    const url = URL.createObjectURL(new Blob([data], { type }));
    const a   = document.createElement('a');
    a.href     = url;
    a.download = filename;
    a.click();
    // Avoid racing download initiation on slower browsers/devices.
    setTimeout(() => URL.revokeObjectURL(url), 5_000);
}

