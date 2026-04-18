/**
 * utils.js — Pure helpers. No DOM, no state, no side effects.
 */

export const AGENT_ICONS = { 1: '🪞', 2: '🛑', 3: '🎯', 4: '⚙️', 5: '🛡️' };

/** Model + agent temperature fields: quiet clamp; invalid text → default (no error toast). */
export const SETTINGS_TEMP_MIN = 0.1;
export const SETTINGS_TEMP_MAX = 2;
export const SETTINGS_TEMP_DEFAULT = 1;

/**
 * Coerce raw input to a finite temperature in [SETTINGS_TEMP_MIN, SETTINGS_TEMP_MAX].
 * Non-numeric input → SETTINGS_TEMP_DEFAULT. Examples: `3` → `2`, `0` → `0.1`.
 */
export function normalizeSettingsTemperature(raw) {
    const n = parseFloat(String(raw ?? '').trim());
    if (!Number.isFinite(n)) return SETTINGS_TEMP_DEFAULT;
    if (n > SETTINGS_TEMP_MAX) return SETTINGS_TEMP_MAX;
    if (n < SETTINGS_TEMP_MIN) return SETTINGS_TEMP_MIN;
    return n;
}

// When the backend returns an error_type, we show a specific hint
// so the user knows what to do about it.
export const ERROR_HINTS = {
    api_key_error:    '🔑 Check your GEMINI_API_KEY in the .env file.',
    rate_limit_error: '⏳ Gemini rate limit reached. Wait a moment and retry.',
    model_error:      '🔧 Model unavailable. Open Settings → Model Registry to update.',
    agent_not_found:  '❓ Agent not found. This may be a configuration issue.',
    validation_error: '',   // Message is already clear enough
    ai_response_error:'🤖 The AI returned an unusable response. Try again.',
};

/** Text nodes only — no raw HTML passthrough (same contract as former DOM-based escape). */
export function escapeHtml(t) {
    if (t == null) return '';
    return String(t)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/** Safe embedding of a JS value inside HTML attribute onclick handlers (JSON + HTML entity escape). */
export function escapeJsString(t) {
    return escapeHtml(JSON.stringify(String(t)));
}

const _PH_C = '\uE000';
const _PH_L = '\uE001';
const _PH_END = '\uE002';

/** Allow only safe link targets (http(s), same-origin paths, #fragments). */
export function safeMarkdownHref(url) {
    const u = String(url).trim();
    if (!u) return false;
    if (/^(javascript|data|vbscript|file):/i.test(u)) return false;
    if (u.startsWith('/') || u.startsWith('#') || u.startsWith('?')) return true;
    if (u.startsWith('./') || u.startsWith('../')) return true;
    try {
        const parsed = new URL(u, typeof window !== 'undefined' ? window.location.origin : 'https://local.invalid');
        return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch {
        return false;
    }
}

function _splitFencedCode(src) {
    const parts = [];
    let pos = 0;
    const len = src.length;
    while (pos < len) {
        const open = src.indexOf('```', pos);
        if (open === -1) {
            if (pos < len) parts.push({ type: 'md', text: src.slice(pos) });
            break;
        }
        if (open > pos) parts.push({ type: 'md', text: src.slice(pos, open) });
        let cur = open + 3;
        const nl = src.indexOf('\n', cur);
        if (nl === -1) {
            parts.push({ type: 'md', text: src.slice(open) });
            break;
        }
        const info = src.slice(cur, nl).trim();
        cur = nl + 1;
        const close = src.indexOf('```', cur);
        if (close === -1) {
            parts.push({ type: 'md', text: src.slice(open) });
            break;
        }
        parts.push({ type: 'code', lang: info, code: src.slice(cur, close) });
        pos = close + 3;
        if (src[pos] === '\n') pos += 1;
        else if (src[pos] === '\r' && src[pos + 1] === '\n') pos += 2;
    }
    return parts;
}

function _formatInlineMarkdown(raw) {
    const codes = [];
    const links = [];
    let s = raw;
    s = s.replace(/`([^`]+)`/g, (_, code) => {
        const id = codes.length;
        codes.push(code);
        return `${_PH_C}C${id}${_PH_END}`;
    });
    s = s.replace(/\[([^\]]*)\]\(([^)]+)\)/g, (full, label, url) => {
        const u = String(url).trim();
        if (!safeMarkdownHref(u)) return full;
        const id = links.length;
        links.push({ label, url: u });
        return `${_PH_L}L${id}${_PH_END}`;
    });
    s = escapeHtml(s);
    s = s.replace(new RegExp(`${_PH_C}C(\\d+)${_PH_END}`, 'g'), (_, id) =>
        `<code class="md-inline">${escapeHtml(codes[Number(id)])}</code>`);
    s = s.replace(new RegExp(`${_PH_L}L(\\d+)${_PH_END}`, 'g'), (_, id) => {
        const { label, url } = links[Number(id)];
        return `<a href="${escapeHtml(url)}" class="md-link" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
    });
    s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/\*(.+?)\*/g, '<em>$1</em>');
    return s;
}

function _parsePipeTableCells(line) {
    const t = line.trim();
    if (!t.includes('|')) return null;
    let s = t;
    if (s.startsWith('|')) s = s.slice(1);
    if (s.endsWith('|')) s = s.slice(0, -1);
    const parts = s.split('|').map((x) => x.trim());
    return parts.length ? parts : null;
}

function _isPipeSeparatorRow(line) {
    const cells = _parsePipeTableCells(line);
    if (!cells || cells.length < 1) return false;
    return cells.every((c) => /^:?-{3,}:?$/.test(c));
}

function _cellAlignment(sepCell) {
    const c = sepCell.trim();
    const left = c.startsWith(':');
    const right = c.endsWith(':');
    if (left && right) return 'center';
    if (right) return 'right';
    return 'left';
}

function _thTdAlignAttr(align) {
    if (align === 'center') return ' style="text-align:center"';
    if (align === 'right') return ' style="text-align:right"';
    return '';
}

/** GitHub-style pipe table; header row + separator required. */
function _tryConsumeTable(lines, i) {
    if (i + 1 >= lines.length) return null;
    const headerCells = _parsePipeTableCells(lines[i]);
    if (!headerCells || headerCells.length < 1) return null;
    if (!_isPipeSeparatorRow(lines[i + 1])) return null;
    const sepCells = _parsePipeTableCells(lines[i + 1]);
    if (!sepCells || sepCells.length !== headerCells.length) return null;
    const align = sepCells.map(_cellAlignment);
    const bodyRows = [];
    let j = i + 2;
    while (j < lines.length) {
        if (lines[j].trim() === '') break;
        const cells = _parsePipeTableCells(lines[j]);
        if (!cells || cells.length !== headerCells.length) break;
        bodyRows.push(cells);
        j++;
    }
    let html = '<table class="md-table"><thead><tr>';
    for (let k = 0; k < headerCells.length; k++) {
        html += `<th scope="col"${_thTdAlignAttr(align[k])}>${_formatInlineMarkdown(headerCells[k])}</th>`;
    }
    html += '</tr></thead><tbody>';
    for (const row of bodyRows) {
        html += '<tr>';
        for (let k = 0; k < row.length; k++) {
            html += `<td${_thTdAlignAttr(align[k])}>${_formatInlineMarkdown(row[k])}</td>`;
        }
        html += '</tr>';
    }
    html += '</tbody></table>';
    return { html, end: j };
}

/** Consecutive `>` lines (GFM-style paragraph breaks via blank line between quoted blocks). */
function _tryConsumeBlockquote(lines, start) {
    if (start >= lines.length || !/^\s*>/.test(lines[start])) return null;
    const paragraphs = [];
    let current = [];
    let j = start;
    while (j < lines.length) {
        const line = lines[j];
        if (/^\s*>/.test(line)) {
            current.push(line.replace(/^\s*>\s?/, ''));
            j++;
        } else if (line.trim() === '' && j + 1 < lines.length && /^\s*>/.test(lines[j + 1])) {
            if (current.length) {
                paragraphs.push(current.join(' '));
                current = [];
            }
            j++;
        } else {
            break;
        }
    }
    if (current.length) paragraphs.push(current.join(' '));
    if (!paragraphs.length) return null;
    const inner = paragraphs.map((p) => `<p class="md-bq-p">${_formatInlineMarkdown(p)}</p>`).join('');
    return { html: `<blockquote class="md-bq">${inner}</blockquote>`, end: j };
}

/** Indent depth for nesting: two spaces per level; tab counts as four spaces. */
function _measureWsIndent(ws) {
    let n = 0;
    for (const ch of ws) {
        if (ch === ' ') n++;
        else if (ch === '\t') n += 4;
    }
    return n;
}

function _parseListLine(line) {
    const mUl = line.match(/^(\s*)([-*])\s+(.*)$/);
    if (mUl) {
        const depth = Math.floor(_measureWsIndent(mUl[1]) / 2);
        return { depth, type: 'ul', content: mUl[3] };
    }
    const mOl = line.match(/^(\s*)(\d+)\.\s+(.*)$/);
    if (mOl) {
        const depth = Math.floor(_measureWsIndent(mOl[1]) / 2);
        return { depth, type: 'ol', content: mOl[3] };
    }
    return null;
}

function _normalizeListDepths(items) {
    if (!items.length) return;
    const minD = Math.min(...items.map((x) => x.depth));
    items.forEach((x) => x.depth -= minD);
    for (let k = 1; k < items.length; k++) {
        if (items[k].depth > items[k - 1].depth + 1) {
            items[k].depth = items[k - 1].depth + 1;
        }
    }
}

function _renderListTree(items, start, baseDepth) {
    if (start >= items.length || items[start].depth !== baseDepth) {
        return { html: '', next: start };
    }
    const firstType = items[start].type;
    const tag = firstType === 'ul' ? 'ul' : 'ol';
    let html = `<${tag} class="md-list">`;
    let i = start;
    while (i < items.length && items[i].depth === baseDepth) {
        const it = items[i];
        if (it.type !== firstType) break;
        const content = _formatInlineMarkdown(it.content);
        i++;
        let nestedHtml = '';
        if (i < items.length && items[i].depth > baseDepth) {
            const nested = _renderListTree(items, i, baseDepth + 1);
            nestedHtml = nested.html;
            i = nested.next;
        }
        html += `<li>${content}${nestedHtml}</li>`;
    }
    html += `</${tag}>`;
    return { html, next: i };
}

function _renderAllListBlocks(items) {
    const parts = [];
    let i = 0;
    while (i < items.length) {
        const t0 = items[i].type;
        let j = i + 1;
        while (j < items.length && !(items[j].depth === 0 && items[j].type !== t0)) {
            j++;
        }
        const slice = items.slice(i, j);
        const r = _renderListTree(slice, 0, 0);
        parts.push(r.html);
        i = j;
    }
    return parts.join('');
}

function _tryConsumeList(lines, start) {
    if (start >= lines.length || !_parseListLine(lines[start])) return null;
    const items = [];
    let j = start;
    while (j < lines.length) {
        const line = lines[j];
        const t = line.trimEnd();
        if (t === '') {
            if (j + 1 < lines.length && _parseListLine(lines[j + 1])) {
                j++;
                continue;
            }
            break;
        }
        const parsed = _parseListLine(line);
        if (!parsed) break;
        items.push(parsed);
        j++;
    }
    if (items.length === 0) return null;
    _normalizeListDepths(items);
    const html = _renderAllListBlocks(items);
    return { html, end: j };
}

function _formatSingleLineBlock(trimmed) {
    if (trimmed === '') return '<br>';
    if (/^\s*([-*_])\1{2,}\s*$/.test(trimmed)) {
        return '<hr class="md-hr">';
    }
    const h = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
        const level = Math.min(h[1].length, 6);
        const tagN = Math.min(level + 1, 6);
        const inner = _formatInlineMarkdown(h[2]);
        return `<h${tagN} class="md-h">${inner}</h${tagN}>`;
    }
    return _formatInlineMarkdown(trimmed);
}

function _formatBlockLines(mdText) {
    const lines = mdText.split(/\r?\n/);
    const out = [];
    let i = 0;
    while (i < lines.length) {
        const trimmed = lines[i].trimEnd();
        if (trimmed === '') {
            out.push('<br>');
            i++;
            continue;
        }
        const table = _tryConsumeTable(lines, i);
        if (table) {
            out.push(table.html);
            i = table.end;
            continue;
        }
        const bq = _tryConsumeBlockquote(lines, i);
        if (bq) {
            out.push(bq.html);
            i = bq.end;
            continue;
        }
        const lst = _tryConsumeList(lines, i);
        if (lst) {
            out.push(lst.html);
            i = lst.end;
            continue;
        }
        out.push(_formatSingleLineBlock(trimmed));
        i++;
    }
    return out.join('');
}

/**
 * Renders a safe subset of Markdown for AI/chat content.
 * Fenced ``` code ```, pipe tables, blockquotes, headings #–######, hr ---,
 * nested bullet/ordered lists (two spaces per indent level; tab = four spaces),
 * inline `code`, links, **bold**, *italic*.
 * HTML in source is escaped; link hrefs are allowlisted.
 */
export function formatMarkdown(text) {
    if (text == null || text === '') return '';
    const parts = _splitFencedCode(String(text));
    return parts
        .map((p) => {
            if (p.type === 'code') {
                const langSan = p.lang ? String(p.lang).replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 32) : '';
                const langAttr = langSan ? ` class="md-lang-${langSan}"` : '';
                return `<pre class="md-fence"><code${langAttr}>${escapeHtml(p.code)}</code></pre>`;
            }
            if (!p.text) return '';
            return _formatBlockLines(p.text);
        })
        .join('');
}

export function truncate(t, m) {
    return t && t.length > m ? t.substring(0, m) + '...' : t;
}
