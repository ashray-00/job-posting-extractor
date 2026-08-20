"""Minimal FastAPI review tool for hand-correcting draft labels.

Run:  uvicorn src.review:app --reload --port 8111
CLI:  python -m src.review --input data/draft.jsonl --output data/reviewed.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

# ---------------------------------------------------------------------------
# Paths & state
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parent.parent


def _parse_cli() -> tuple[Path, Path]:
    """Parse --input / --output from sys.argv (works under uvicorn too)."""
    inp = Path(os.environ.get("REVIEW_INPUT", "data/draft.jsonl"))
    out = Path(os.environ.get("REVIEW_OUTPUT", "data/reviewed.jsonl"))
    if not inp.is_absolute():
        inp = _ROOT / inp
    if not out.is_absolute():
        out = _ROOT / out
    return inp, out


INPUT_PATH, OUTPUT_PATH = _parse_cli()

# In-memory list; output is append-only on disk
_records: list[dict[str, Any]] = []
_done_ids: set[str] = set()


def _load_records() -> None:
    global _records, _done_ids
    _records = []
    if INPUT_PATH.exists():
        with open(INPUT_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    _records.append(json.loads(line))
    _done_ids = set()
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    _done_ids.add(json.loads(line).get("doc_id", ""))


_load_records()

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Label Review Tool")


@app.get("/api/status")
def api_status():
    return {"total": len(_records), "done": len(_done_ids)}


@app.get("/api/next")
def api_next():
    for r in _records:
        if r.get("doc_id") not in _done_ids:
            idx = _records.index(r)
            return {"index": idx, "total": len(_records), "record": r}
    return {"index": -1, "total": len(_records), "record": None}


@app.get("/api/record/{idx}")
def api_record(idx: int):
    if 0 <= idx < len(_records):
        return {"index": idx, "total": len(_records), "record": _records[idx]}
    return JSONResponse({"error": "out of range"}, 404)


@app.post("/api/save")
async def api_save(request: Request):
    body = await request.json()
    doc_id = body.get("doc_id", "")
    out_record = {
        "doc_id": doc_id,
        "text": body.get("text", ""),
        "label": body.get("label", {}),
        "source": body.get("source", ""),
        "lang": body.get("lang", ""),
        "difficulty": body.get("difficulty", "clean"),
        "reviewer_notes": body.get("reviewer_notes", ""),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(out_record, ensure_ascii=False) + "\n")
    _done_ids.add(doc_id)
    return {"ok": True, "done": len(_done_ids), "total": len(_records)}


@app.post("/api/skip")
async def api_skip(request: Request):
    body = await request.json()
    _done_ids.add(body.get("doc_id", ""))
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index():
    return _HTML


# ---------------------------------------------------------------------------
# The entire frontend in one HTML string
# ---------------------------------------------------------------------------

_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Label Review</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, -apple-system, sans-serif; background: #0f1117; color: #e0e0e0; height: 100vh; overflow: hidden; }
.container { display: flex; height: 100vh; }
.left { flex: 1; overflow-y: auto; padding: 20px; border-right: 1px solid #2a2d3a; background: #14161e; }
.right { width: 420px; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 8px; }
.doc-text { white-space: pre-wrap; font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 13px; line-height: 1.6; color: #c8ccd4; }
.doc-text mark { background: #3b5998; color: #fff; border-radius: 2px; padding: 0 2px; }
.doc-text mark.ungrounded { background: #b33a3a; }
.meta { font-size: 11px; color: #888; margin-bottom: 8px; }
#issues { display: none; background: #3b1f1f; border: 1px solid #7f3333; border-radius: 6px; padding: 10px 14px; margin-bottom: 12px; font-size: 13px; color: #fca5a5; line-height: 1.7; }
.issue-tag { display: inline-block; background: #5c2020; padding: 2px 8px; border-radius: 3px; margin: 2px 4px; font-size: 12px; }
h2 { font-size: 15px; color: #9ca3af; margin: 8px 0 4px; border-bottom: 1px solid #2a2d3a; padding-bottom: 4px; }
label { display: block; font-size: 12px; color: #9ca3af; margin-top: 6px; }
input, select, textarea { width: 100%; padding: 5px 8px; font-size: 13px; background: #1e2130; border: 1px solid #333750; border-radius: 4px; color: #e0e0e0; margin-top: 2px; }
input:focus, select:focus, textarea:focus { outline: none; border-color: #5b7bd5; }
textarea { resize: vertical; min-height: 40px; }
.field-row { display: flex; align-items: center; gap: 6px; }
.field-row input, .field-row select { flex: 1; }
.null-check { width: 16px; height: 16px; flex-shrink: 0; accent-color: #5b7bd5; }
.list-group { background: #1a1d2b; border-radius: 4px; padding: 8px; margin-top: 4px; }
.list-item { display: flex; gap: 4px; margin-bottom: 4px; align-items: center; }
.list-item input { flex: 1; }
.btn-sm { padding: 2px 8px; font-size: 11px; cursor: pointer; border: 1px solid #444; border-radius: 3px; background: #252838; color: #ccc; }
.btn-sm:hover { background: #333750; }
.btn-sm.remove { color: #e55; border-color: #a33; }
.lang-item { display: flex; gap: 4px; margin-bottom: 4px; align-items: center; }
.lang-item input { width: 50px; }
.lang-item select { flex: 1; }
.actions { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.actions button { padding: 8px 16px; font-size: 13px; font-weight: 600; border: none; border-radius: 5px; cursor: pointer; }
.btn-save { background: #2563eb; color: #fff; }
.btn-save:hover { background: #1d4ed8; }
.btn-skip { background: #374151; color: #ccc; }
.btn-skip:hover { background: #4b5563; }
.btn-flag { background: #92400e; color: #fbbf24; }
.btn-flag:hover { background: #78350f; }
.progress { font-size: 12px; color: #888; text-align: center; padding: 8px; }
.toast { position: fixed; bottom: 20px; right: 20px; padding: 10px 20px; border-radius: 6px; font-size: 13px; color: #fff; opacity: 0; transition: opacity 0.3s; z-index: 999; }
.toast.show { opacity: 1; }
.toast.ok { background: #166534; }
.toast.err { background: #991b1b; }
.validation-err { color: #f87171; font-size: 11px; margin-top: 2px; }
</style>
</head>
<body>
<div class="container">
  <div class="left">
    <div class="meta" id="meta"></div>
    <div id="issues"></div>
    <div class="doc-text" id="docText">Loading…</div>
  </div>
  <div class="right">
    <div class="progress" id="progress"></div>
    <div id="form"></div>
    <div>
      <label>Difficulty</label>
      <select id="difficulty">
        <option value="clean">clean</option>
        <option value="missing_fields">missing_fields</option>
        <option value="multilingual">multilingual</option>
        <option value="adversarial">adversarial</option>
      </select>
    </div>
    <div>
      <label>Reviewer notes</label>
      <textarea id="notes" rows="2"></textarea>
    </div>
    <div id="valErrors"></div>
    <div class="actions">
      <button class="btn-save" onclick="save()">Save &amp; Next</button>
      <button class="btn-skip" onclick="skip()">Skip</button>
      <button class="btn-flag" onclick="flag()">Flag</button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>

<script>
const ENUM_OPTIONS = {
  seniority: [null,'intern','junior','mid','senior','lead','head'],
  contract_type: [null,'permanent','fixed_term','contract','internship','working_student'],
  workload: [null,'full_time','part_time'],
  salary_period: [null,'year','month','hour'],
  remote_policy: [null,'onsite','hybrid','remote'],
  visa_sponsorship: [null, true, false],
};
const LANG_LEVELS = ['A1','A2','B1','B2','C1','C2','native'];
const NULLABLE_STR = ['title','currency','location_city','location_country'];
const NULLABLE_INT = ['salary_min','salary_max','years_experience_min'];
const LIST_STR = ['required_skills','nice_to_have_skills'];
const FIELD_ORDER = [
  'title','seniority','contract_type','workload',
  'salary_min','salary_max','salary_period','currency',
  'remote_policy','location_city','location_country',
  'required_skills','nice_to_have_skills','years_experience_min',
  'languages','visa_sponsorship'
];

let current = null;
let currentIdx = -1;
let docTextRaw = '';

async function loadNext() {
  const res = await fetch('/api/next');
  const data = await res.json();
  if (data.index === -1) {
    document.getElementById('docText').textContent = 'All done!';
    document.getElementById('form').innerHTML = '';
    updateProgress();
    return;
  }
  currentIdx = data.index;
  current = data.record;
  docTextRaw = current.text || '';
  let metaText = `#${currentIdx} | ${current.doc_id} | source: ${current.source} | lang: ${current.lang}`;
  if (current.complication) metaText += ` | complication: ${current.complication}`;
  document.getElementById('meta').textContent = metaText;

  // Show issues banner if present
  const issuesEl = document.getElementById('issues');
  if (current.issues && current.issues.length > 0) {
    issuesEl.innerHTML = '<strong>⚠ Review needed:</strong> ' +
      current.issues.map(i => `<span class="issue-tag">${escHtml(i)}</span>`).join(' ');
    issuesEl.style.display = 'block';
  } else {
    issuesEl.style.display = 'none';
  }

  buildForm(current.draft_label || current.weak_labels || current.label || {});
  highlightText();
  updateProgress();
}

async function updateProgress() {
  const res = await fetch('/api/status');
  const s = await res.json();
  document.getElementById('progress').textContent = `${s.done} / ${s.total} reviewed`;
}

function buildForm(label) {
  let html = '';
  for (const f of FIELD_ORDER) {
    if (ENUM_OPTIONS[f]) {
      html += buildEnum(f, label[f], ENUM_OPTIONS[f]);
    } else if (NULLABLE_STR.includes(f)) {
      html += buildNullStr(f, label[f]);
    } else if (NULLABLE_INT.includes(f)) {
      html += buildNullInt(f, label[f]);
    } else if (LIST_STR.includes(f)) {
      html += buildListStr(f, label[f] || []);
    } else if (f === 'languages') {
      html += buildLanguages(label[f] || []);
    }
  }
  document.getElementById('form').innerHTML = html;
  document.querySelectorAll('input, select').forEach(el => {
    el.addEventListener('input', highlightText);
    el.addEventListener('change', highlightText);
  });
}

function buildEnum(name, val, options) {
  let opts = options.map(o => {
    const label = o === null ? '— null —' : String(o);
    const sel = (val === o || (val === undefined && o === null)) ? 'selected' : '';
    return `<option value="${o === null ? '__null__' : o}" ${sel}>${label}</option>`;
  }).join('');
  return `<label>${name}</label><select data-field="${name}">${opts}</select>`;
}

function buildNullStr(name, val) {
  const isNull = val === null || val === undefined;
  return `<label>${name}</label>
    <div class="field-row">
      <input type="text" data-field="${name}" value="${isNull ? '' : escHtml(val)}" ${isNull ? 'disabled' : ''}>
      <input type="checkbox" class="null-check" data-null-for="${name}" ${isNull ? 'checked' : ''}
        onchange="toggleNull(this,'${name}')" title="null">
    </div>`;
}

function buildNullInt(name, val) {
  const isNull = val === null || val === undefined;
  return `<label>${name}</label>
    <div class="field-row">
      <input type="number" data-field="${name}" value="${isNull ? '' : val}" ${isNull ? 'disabled' : ''}>
      <input type="checkbox" class="null-check" data-null-for="${name}" ${isNull ? 'checked' : ''}
        onchange="toggleNull(this,'${name}')" title="null">
    </div>`;
}

function buildListStr(name, items) {
  let rows = items.map((v, i) =>
    `<div class="list-item"><input type="text" data-list="${name}" data-idx="${i}" value="${escHtml(v)}">
     <button class="btn-sm remove" onclick="removeListItem(this)">×</button></div>`
  ).join('');
  return `<label>${name}</label>
    <div class="list-group" id="list-${name}">${rows}
      <button class="btn-sm" onclick="addListItem('${name}')">+ add</button>
    </div>`;
}

function buildLanguages(items) {
  let rows = items.map((v, i) => langRow(i, v.lang || '', v.level || 'B1')).join('');
  return `<label>languages</label>
    <div class="list-group" id="list-languages">${rows}
      <button class="btn-sm" onclick="addLangRow()">+ add</button>
    </div>`;
}

function langRow(i, lang, level) {
  const opts = LANG_LEVELS.map(l =>
    `<option value="${l}" ${l===level?'selected':''}>${l}</option>`
  ).join('');
  return `<div class="lang-item">
    <input type="text" data-lang-code="${i}" value="${escHtml(lang)}" placeholder="en" maxlength="2">
    <select data-lang-level="${i}">${opts}</select>
    <button class="btn-sm remove" onclick="removeLangRow(this)">×</button>
  </div>`;
}

function toggleNull(cb, name) {
  const inp = document.querySelector(`[data-field="${name}"]`);
  if (cb.checked) { inp.disabled = true; inp.value = ''; }
  else { inp.disabled = false; inp.focus(); }
  highlightText();
}

function addListItem(name) {
  const group = document.getElementById('list-' + name);
  const items = group.querySelectorAll('.list-item');
  const idx = items.length;
  const div = document.createElement('div');
  div.className = 'list-item';
  div.innerHTML = `<input type="text" data-list="${name}" data-idx="${idx}" value="">
    <button class="btn-sm remove" onclick="removeListItem(this)">×</button>`;
  group.insertBefore(div, group.querySelector('.btn-sm:last-child'));
  div.querySelector('input').addEventListener('input', highlightText);
  div.querySelector('input').focus();
}

function removeListItem(btn) {
  btn.parentElement.remove();
  highlightText();
}

function addLangRow() {
  const group = document.getElementById('list-languages');
  const items = group.querySelectorAll('.lang-item');
  const idx = items.length;
  const div = document.createElement('div');
  div.className = 'lang-item';
  div.innerHTML = langRow(idx, '', 'B1');
  group.insertBefore(div, group.querySelector('.btn-sm:last-child'));
  div.querySelectorAll('input, select').forEach(el => {
    el.addEventListener('input', highlightText);
    el.addEventListener('change', highlightText);
  });
}

function removeLangRow(btn) {
  btn.parentElement.remove();
  highlightText();
}

function getFormValues() {
  const label = {};
  for (const f of FIELD_ORDER) {
    if (ENUM_OPTIONS[f]) {
      const sel = document.querySelector(`[data-field="${f}"]`);
      const v = sel.value;
      if (f === 'visa_sponsorship') {
        label[f] = v === '__null__' ? null : v === 'true';
      } else {
        label[f] = v === '__null__' ? null : v;
      }
    } else if (NULLABLE_STR.includes(f)) {
      const cb = document.querySelector(`[data-null-for="${f}"]`);
      if (cb && cb.checked) { label[f] = null; }
      else {
        const inp = document.querySelector(`[data-field="${f}"]`);
        label[f] = inp.value || null;
      }
    } else if (NULLABLE_INT.includes(f)) {
      const cb = document.querySelector(`[data-null-for="${f}"]`);
      if (cb && cb.checked) { label[f] = null; }
      else {
        const inp = document.querySelector(`[data-field="${f}"]`);
        label[f] = inp.value ? parseInt(inp.value, 10) : null;
      }
    } else if (LIST_STR.includes(f)) {
      const inputs = document.querySelectorAll(`[data-list="${f}"]`);
      label[f] = Array.from(inputs).map(i => i.value.trim()).filter(Boolean);
    } else if (f === 'languages') {
      const codes = document.querySelectorAll('[data-lang-code]');
      const levels = document.querySelectorAll('[data-lang-level]');
      label.languages = [];
      codes.forEach((c, i) => {
        const lang = c.value.trim();
        const level = levels[i] ? levels[i].value : 'B1';
        if (lang) label.languages.push({ lang, level });
      });
    }
  }
  return label;
}

function collectStringValues() {
  const vals = new Set();
  for (const f of FIELD_ORDER) {
    if (NULLABLE_STR.includes(f)) {
      const cb = document.querySelector(`[data-null-for="${f}"]`);
      if (!cb || !cb.checked) {
        const inp = document.querySelector(`[data-field="${f}"]`);
        if (inp && inp.value.trim()) vals.add(inp.value.trim());
      }
    } else if (LIST_STR.includes(f)) {
      document.querySelectorAll(`[data-list="${f}"]`).forEach(inp => {
        if (inp.value.trim()) vals.add(inp.value.trim());
      });
    }
  }
  // also add lang codes
  document.querySelectorAll('[data-lang-code]').forEach(c => {
    if (c.value.trim()) vals.add(c.value.trim());
  });
  return vals;
}

function highlightText() {
  const vals = collectStringValues();
  if (vals.size === 0) {
    document.getElementById('docText').textContent = docTextRaw;
    return;
  }
  let html = escHtml(docTextRaw);
  const textLower = docTextRaw.toLowerCase();

  // sort by length descending to match longer strings first
  const sorted = Array.from(vals).sort((a, b) => b.length - a.length);

  // find all matches with positions, mark grounded vs ungrounded
  const marks = [];
  for (const v of sorted) {
    if (v.length < 2) continue;
    const vLower = v.toLowerCase();
    const found = textLower.includes(vLower);
    marks.push({ value: v, grounded: found });
  }

  // rebuild HTML with highlights
  // use a simple approach: escape first, then replace
  for (const m of marks) {
    const escaped = escHtml(m.value);
    const regex = new RegExp(escRegex(escaped), 'gi');
    const cls = m.grounded ? '' : ' ungrounded';
    html = html.replace(regex, match => `<mark class="${cls}">${match}</mark>`);
  }

  document.getElementById('docText').innerHTML = html;
}

function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function escRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function toast(msg, ok) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show ' + (ok ? 'ok' : 'err');
  setTimeout(() => t.className = 'toast', 2000);
}

async function save() {
  if (!current) return;
  const label = getFormValues();
  const body = {
    doc_id: current.doc_id,
    text: current.text,
    label,
    source: current.source,
    lang: current.lang,
    difficulty: document.getElementById('difficulty').value,
    reviewer_notes: document.getElementById('notes').value,
  };
  const res = await fetch('/api/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.ok) { toast('Saved!', true); loadNext(); }
  else { toast('Error saving', false); }
}

async function skip() {
  if (!current) return;
  await fetch('/api/skip', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ doc_id: current.doc_id }),
  });
  toast('Skipped', true);
  loadNext();
}

function flag() {
  document.getElementById('difficulty').value = 'adversarial';
  document.getElementById('notes').value =
    (document.getElementById('notes').value + ' [FLAGGED]').trim();
  toast('Flagged — click Save to record', true);
}

// keyboard shortcuts
document.addEventListener('keydown', e => {
  if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); save(); }
  if (e.ctrlKey && e.key === 's') { e.preventDefault(); save(); }
  if (e.ctrlKey && e.key === 'ArrowRight') { e.preventDefault(); skip(); }
});

loadNext();
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Label review tool")
    parser.add_argument("--input", type=str, required=True, help="Input JSONL with draft labels")
    parser.add_argument("--output", type=str, required=True, help="Output JSONL for reviewed labels")
    parser.add_argument("--port", type=int, default=8111)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()

    os.environ["REVIEW_INPUT"] = args.input
    os.environ["REVIEW_OUTPUT"] = args.output

    global INPUT_PATH, OUTPUT_PATH
    INPUT_PATH = Path(args.input) if Path(args.input).is_absolute() else _ROOT / args.input
    OUTPUT_PATH = Path(args.output) if Path(args.output).is_absolute() else _ROOT / args.output
    _load_records()

    import uvicorn
    uvicorn.run("src.review:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
