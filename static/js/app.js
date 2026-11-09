/**
 * AI Plagiarism Intelligence – Main JS
 * Handles API calls, dynamic UI, and chart rendering
 */

const API = {
  base: '/api',

  async json(path, opts = {}) {
    const res = await fetch(this.base + path, {
      headers: { 'Content-Type': 'application/json' },
      ...opts,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
  },

  get:  (path)        => API.json(path),
  post: (path, body)  => API.json(path, { method: 'POST', body: JSON.stringify(body) }),
};

/* ── Verdict badge HTML ─────────────────────────────────────── */
function verdictBadge(verdict) {
  const cls = { clean: 'badge-clean', suspicious: 'badge-suspicious', flagged: 'badge-flagged' };
  const lbl = { clean: '✓ Clean', suspicious: '⚠ Suspicious', flagged: '✗ Flagged' };
  return `<span class="${cls[verdict] || 'badge-suspicious'}">${lbl[verdict] || verdict}</span>`;
}

/* ── Risk colour ────────────────────────────────────────────── */
function riskClass(score) {
  if (score >= 0.75) return 'high';
  if (score >= 0.45) return 'medium';
  return 'low';
}

/* ── Format percent ─────────────────────────────────────────── */
function pct(v) { return (v * 100).toFixed(1) + '%'; }

/* ── Progress bar HTML ──────────────────────────────────────── */
function progressBar(score) {
  const cls = riskClass(score);
  return `
    <div class="progress-wrap">
      <div class="progress-bar ${cls}" style="width:${pct(score)}"></div>
    </div>
    <small style="color:var(--ibm-gray-70)">${pct(score)}</small>
  `;
}

/* ── Load courses into <select> ─────────────────────────────── */
async function loadCourseSelect(selectEl) {
  selectEl.innerHTML = '<option value="">Loading…</option>';
  try {
    const courses = await API.get('/assignments/courses');
    if (!courses.length) {
      selectEl.innerHTML = '<option value="">No courses yet — create one below</option>';
      return;
    }
    selectEl.innerHTML = '<option value="">Select course…</option>' +
      courses.map(c => `<option value="${c.id}">${c.code} – ${c.name}</option>`).join('');
  } catch (e) {
    console.error('Failed to load courses', e);
    selectEl.innerHTML = '<option value="">⚠ Could not load courses</option>';
  }
}

/* ── Load assignments into <select> ────────────────────────── */
async function loadAssignmentSelect(selectEl, courseId) {
  if (!courseId) { selectEl.innerHTML = '<option value="">Select a course first…</option>'; return; }
  selectEl.innerHTML = '<option value="">Loading…</option>';
  try {
    const assignments = await API.get(`/assignments?course_id=${courseId}`);
    if (!assignments.length) {
      selectEl.innerHTML = '<option value="">No assignments yet — create one below</option>';
      return;
    }
    selectEl.innerHTML = '<option value="">Select assignment…</option>' +
      assignments.map(a => `<option value="${a.id}">${a.title}</option>`).join('');
  } catch (e) {
    console.error('Failed to load assignments', e);
    selectEl.innerHTML = '<option value="">⚠ Could not load assignments</option>';
  }
}

/* ── Toast notification ─────────────────────────────────────── */
function toast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `alert alert-${type}`;
  el.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:999;min-width:260px;box-shadow:0 4px 12px rgba(0,0,0,.15)';
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

/* ── Mini donut SVG (score ring) ────────────────────────────── */
function donutRing(score, color) {
  const r = 36, cx = 44, cy = 44;
  const circumference = 2 * Math.PI * r;
  const dash = score * circumference;
  return `
    <svg width="88" height="88" viewBox="0 0 88 88">
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#e0e0e0" stroke-width="8"/>
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${color}" stroke-width="8"
        stroke-dasharray="${dash} ${circumference}"
        stroke-dashoffset="${circumference * 0.25}"
        stroke-linecap="round" transform="rotate(-90 ${cx} ${cy})"/>
      <text x="${cx}" y="${cy+5}" text-anchor="middle" font-size="14" font-weight="700" fill="${color}">
        ${Math.round(score*100)}%
      </text>
    </svg>`;
}

/* ── Expose globally ────────────────────────────────────────── */
window.PlagiarismApp = {
  API, verdictBadge, riskClass, pct, progressBar,
  loadCourseSelect, loadAssignmentSelect, toast, donutRing,
};
