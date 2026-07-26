// dashboard/dashboard.js — FarmerVerify AI Admin Dashboard (Complete)

'use strict';

const API_BASE = 'http://localhost:8000/api/v1/dashboard';
const IMAGE_API = 'http://localhost:8000/api/v1/dashboard/documents';

let currentView = 'overview';
let allDocuments = [];
let selectedDoc = null;

const DOC_TYPES = {
  aadhaar_card:  { label: 'Aadhaar Card',   icon: 'id-card' },
  bank_passbook: { label: 'Bank Passbook',   icon: 'landmark' },
  land_record:   { label: 'Land Record',     icon: 'map' },
  voter_id:      { label: 'Voter ID',        icon: 'vote' },
  other:         { label: 'Other',           icon: 'file' },
};

const STATUS_CFG = {
  verified:     { label: 'Verified',     cls: 'badge-verified' },
  needs_review: { label: 'Needs Review', cls: 'badge-needs_review' },
  rejected:     { label: 'Rejected',     cls: 'badge-rejected' },
  unknown:      { label: 'Unknown',      cls: 'badge-unknown' },
};


// dashboard/dashboard.js — TOP OF FILE — must be before everything else

// ── Global clipboard helper ──────────────────────────────────────────────────
// MUST use function declaration (not const/let/arrow) so onclick="..." can
// find it in the global scope when called from dynamically generated HTML.

window.copyToClipboard = function(text, btn) {
  if (!text || text === '—' || text === 'N/A') {
    alert('Nothing to copy');
    return;
  }

  function onSuccess() {
    if (!btn) return;
    const orig = btn.textContent;
    btn.textContent = '✓ Copied';
    btn.style.cssText += ';color:#2d6a4f;border-color:#2d6a4f;';
    btn.disabled = true;
    setTimeout(() => {
      btn.textContent = orig;
      btn.style.color = '';
      btn.style.borderColor = '';
      btn.disabled = false;
    }, 2000);
  }

  function fallback() {
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.cssText = 'position:fixed;top:0;left:0;width:1px;height:1px;opacity:0;';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      onSuccess();
    } catch(e) {
      alert('Copy failed. Please copy manually: ' + text);
    }
  }

  try {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      navigator.clipboard.writeText(text).then(onSuccess).catch(fallback);
    } else {
      fallback();
    }
  } catch(e) {
    fallback();
  }
};



// ── Toasts ───────────────────────────────────────────────────
function initToast() {
  if (!document.getElementById('toastContainer')) {
    const d = document.createElement('div');
    d.id = 'toastContainer';
    d.className = 'toast-container';
    document.body.appendChild(d);
  }
}

function showToast(msg, type = 'info') {
  initToast();
  const c = document.getElementById('toastContainer');
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  const icons = { success: '✓', error: '✗', info: 'i' };
  t.innerHTML = `<strong style="font-size:16px">${icons[type] || 'i'}</strong><span>${msg}</span>`;
  c.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

// ── Sidebar ──────────────────────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// ── Views ────────────────────────────────────────────────────
function switchView(view) {
  currentView = view;
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const viewEl = document.getElementById(`view-${view}`);
  if (viewEl) viewEl.classList.add('active');
  const navEl = document.querySelector(`[data-view="${view}"]`);
  if (navEl) navEl.classList.add('active');

  const titles = {
    'overview': 'Overview', 'all-docs': 'All Documents',
    'auto-verified': 'Auto-Verified (No Review Needed)',
    'needs-review': 'Manual Review Queue',
    'verified': 'Verified Documents', 'rejected': 'Rejected Documents',
    'search': 'Search Documents',
    'cc-visits':   'CC Field Visits',
    'farmer-profiles': 'Farmer Profiles',
  };
  document.getElementById('pageTitle').textContent = titles[view] || 'Dashboard';

  if (view === 'overview') loadOverview();
  else if (view === 'all-docs') loadDocuments();
  else if (view === 'auto-verified') loadAutoVerified();
  else if (view === 'needs-review') loadDocsByStatus('needs_review', 'reviewDocsTable');
  else if (view === 'verified') loadDocsByStatus('verified', 'verifiedDocsTable');
  else if (view === 'rejected') loadDocsByStatus('rejected', 'rejectedDocsTable');
  else if (view === 'cc-visits') loadCCVisits();
  else if (view === 'farmer-profiles') loadFarmerProfiles();
  else if (view === 'deleted-items') loadDeletedItems();
  document.getElementById('sidebar').classList.remove('open');
}





async function loadCCVisits() {
  try {
    const data = await apiGet(`${API_BASE}/cc-visits?limit=100`);
    renderCCTable('ccVisitsTable', data.visits || []);
  } catch (err) {
    console.error('Failed to load CC visits:', err);
    showToast('Failed to load CC field visits', 'error');
    // Show empty state instead of leaving the section blank
    const container = document.getElementById('ccVisitsTable');
    if (container) {
      container.innerHTML = `
        <div class="empty-state">
          <div style="font-size:32px;margin-bottom:8px">⚠️</div>
          <div class="empty-state-title">Could not load CC visits</div>
          <div class="empty-state-text">
            Check that the server is running and try refreshing.
          </div>
        </div>`;
    }
  }
}

function renderCCTable(containerId, visits) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!visits.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📸</div>
        <div class="empty-state-title">No CC Field Visit Photos Yet</div>
        <div class="empty-state-text">
          CC training photos submitted by field staff will appear here.<br>
          Upload a CC training photo via the Swagger UI or test page.
        </div>
      </div>`;
    return;
  }

  function ccStatusBadge(s) {
    const map = {
      verified:     { bg: 'var(--success-bg)', color: 'var(--success)', icon: '✅', label: 'Confirmed'     },
      needs_review: { bg: 'var(--warning-bg)', color: 'var(--warning)', icon: '⏳', label: 'Pending Review' },
      rejected:     { bg: 'var(--danger-bg)',  color: 'var(--danger)',  icon: '❌', label: 'Flagged'        },
    };
    const c = map[s] || map.needs_review;
    return `<span class="badge" style="background:${c.bg};color:${c.color}">${c.icon} ${c.label}</span>`;
  }

  let html = `
    <table>
      <thead>
        <tr>
          <th>Ref ID</th>
          <th>Status</th>
          <th>Persons</th>
          <th>GPS Location</th>
          <th>Date</th>
          <th>Quality</th>
          <th>Location</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>`;

  for (const v of visits) {
    const hasTwo = String(v.has_minimum_two_persons || '').toLowerCase() === 'true';
    const lat = v.gps_latitude  && v.gps_latitude  !== '—' ? v.gps_latitude  : null;
    const lon = v.gps_longitude && v.gps_longitude !== '—' ? v.gps_longitude : null;
    const personsText = (v.persons_detected && v.persons_detected !== '—')
      ? v.persons_detected : '?';

    const personsBadge = hasTwo
      ? `<span class="person-badge person-badge-ok">✅ ${personsText} persons</span>`
      : `<span class="person-badge person-badge-fail">❌ ${personsText} person</span>`;

    const gpsCell = lat && lon
      ? `<a class="gps-link"
            href="https://www.google.com/maps?q=${lat},${lon}"
            target="_blank"
            title="Open in Google Maps">
           📍 ${parseFloat(lat).toFixed(5)}°,
           ${parseFloat(lon).toFixed(5)}°
         </a>`
      : `<span style="color:var(--text-light);font-size:11px">No GPS</span>`;

    const quality = v.quality_score != null
      ? Math.round(v.quality_score) + '%' : '—';

    const locationDesc = v.location_description && v.location_description !== '—'
      ? v.location_description.substring(0, 55) + (v.location_description.length > 55 ? '…' : '')
      : '—';

    const dateDisplay = v.date_visible && v.date_visible !== '—'
      ? v.date_visible : '—';

    const actions = v.status === 'needs_review'
      ? `<div style="display:flex;flex-direction:column;gap:4px">
           <button class="btn-success btn-sm"
                   onclick="quickActionCC('${v.request_id}','verified')">
             ✅ Confirm
           </button>
           <button class="btn-danger btn-sm"
                   onclick="quickActionCC('${v.request_id}','rejected')">
             ❌ Flag
           </button>
         </div>`
      : `<button class="btn-outline btn-sm"
                onclick="openCCDetail('${v.request_id}')">
           View
         </button>`;

    html += `
      <tr onclick="openCCDetail('${v.request_id}')">
        <td class="td-id">${(v.request_id || '—').substring(0, 12)}</td>
        <td>${ccStatusBadge(v.status)}</td>
        <td>${personsBadge}</td>
        <td>${gpsCell}</td>
        <td style="font-size:11px;color:var(--text-muted)">${dateDisplay}</td>
        <td style="font-size:12px">${quality}</td>
        <td style="font-size:11px;color:var(--text-muted);max-width:180px">${locationDesc}</td>
        <td onclick="event.stopPropagation()">${actions}</td>
      </tr>`;
  }

  html += '</tbody></table>';
  container.innerHTML = html;
}

async function quickActionCC(requestId, newStatus) {
  const label = newStatus === 'verified' ? 'confirm this CC visit' : 'flag this CC visit';
  if (!confirm(`Are you sure you want to ${label}?`)) return;
  try {
    await apiPut(`${API_BASE}/documents/${requestId}/status`, {
      status:      newStatus,
      reviewed_by: document.getElementById('adminName')?.textContent || 'admin',
    });
    showToast(`CC visit ${newStatus === 'verified' ? 'confirmed' : 'flagged'}`, 'success');
    loadCCVisits();
  } catch (err) {
    console.error(err);
    showToast('Failed to update status', 'error');
  }
}

async function openCCDetail(requestId) {
  // Reuse the existing openDetail function — it works for CC too
  await openDetail(requestId);
}
// ── API ──────────────────────────────────────────────────────
async function apiGet(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function apiPut(url, body) {
  const r = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ── Formatters ───────────────────────────────────────────────
function fmtDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
    + ' ' + d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

function statusBadge(s) {
  const c = STATUS_CFG[s] || STATUS_CFG.unknown;
  return `<span class="badge ${c.cls}">${c.label}</span>`;
}

function methodBadge(m) {
  if (m === 'auto' || m === 'auto_low_confidence') return '<span class="badge badge-auto-method">Auto</span>';
  if (m === 'manual') return '<span class="badge badge-manual-method">Manual</span>';
  return '<span class="badge badge-unknown">Pending</span>';
}

function docLabel(type) {
  const c = DOC_TYPES[type] || DOC_TYPES.other;
  return c.label;
}

function scoreColor(s) {
  if (s >= 70) return 'score-good';
  if (s >= 40) return 'score-medium';
  return 'score-bad';
}

function trunc(s, n = 20) { return !s ? '—' : s.length > n ? s.slice(0, n) + '…' : s; }

// ══════════════════════════════════════════════════════════════
// OVERVIEW
// ══════════════════════════════════════════════════════════════

async function loadOverview() {
  try {
    const stats = await apiGet(`${API_BASE}/stats`);

    // ── Correct field names matching actual API response ──────────────────────
const total       = stats.total_documents                 || 0;
const needsReview = stats.status_counts?.needs_review     || 0;
const verified    = stats.status_counts?.verified         || 0;
const rejected    = (stats.status_counts?.rejected        || 0)
                  + (stats.status_counts?.duplicate       || 0);
const autoVer     = stats.auto_verified_count             || 0;
const avgTime     = stats.avg_processing_time             || 0;
const byType      = stats.doc_type_counts                 || {};
const ccPending   = stats.cc_pending                      || 0;

document.getElementById('statTotal').textContent        = total;
document.getElementById('statAutoVerified').textContent = autoVer;
document.getElementById('statReview').textContent       = needsReview;
document.getElementById('statVerified').textContent     = verified;
document.getElementById('statRejected').textContent     = rejected;
document.getElementById('statAvgTime').textContent      = avgTime + 's';

const reviewBadge = document.getElementById('reviewBadge');
const autoBadge   = document.getElementById('autoBadge');
const ccBadge     = document.getElementById('ccBadge');
if (reviewBadge) reviewBadge.textContent = needsReview;
if (autoBadge)   autoBadge.textContent   = autoVer;
if (ccBadge)     ccBadge.textContent      = ccPending;

// ── Type breakdown ────────────────────────────────────────────────────────
const bd = document.getElementById('typeBreakdown');
if (bd) {
  bd.innerHTML = '';
  if (Object.keys(byType).length) {
    for (const [type, count] of Object.entries(byType)) {
      bd.innerHTML += `
        <div class="type-chip">
          <span class="type-chip-count">${count}</span>
          <span class="type-chip-label">${docLabel(type)}</span>
        </div>`;
    }
  } else {
    bd.innerHTML = '<div class="empty-state"><div class="empty-state-text">No documents yet</div></div>';
  }
}

    // ── Recent docs ───────────────────────────────────────────────────────
    const docs = await apiGet(`${API_BASE}/documents?limit=10&sort=newest`);
    renderTable('recentDocs', docs.documents || [], false);

  } catch (err) {
    console.error('Overview load failed:', err);
    showToast('Failed to load dashboard', 'error');
  }
}
// Add this button to the dashboard topbar or overview section
async function exportVerifiedFarmers() {
  try {
    const resp = await fetch('http://localhost:8000/api/v1/dashboard/export/verified');
    const data = await resp.json();

    // Build CSV
    const headers = Object.keys(data.farmers[0] || {}).join(',');
    const rows = data.farmers.map(r =>
      Object.values(r).map(v =>
        typeof v === 'string' ? `"${v.replace(/"/g, '""')}"` :
        Array.isArray(v) ? `"${v.join('; ')}"` : v
      ).join(',')
    );
    const csv = [headers, ...rows].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `farmerverify_export_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);

    showToast(`Exported ${data.total_verified} verified farmers`, 'success');
  } catch (e) {
    showToast('Export failed', 'error');
  }
}
// ══════════════════════════════════════════════════════════════
// DOCUMENT LISTS
// ══════════════════════════════════════════════════════════════

async function loadDocuments() {
  const dt = document.getElementById('filterDocType')?.value || '';
  const st = document.getElementById('filterStatus')?.value || '';
  const so = document.getElementById('filterSort')?.value || 'newest';
  let url = `${API_BASE}/documents?sort=${so}&limit=100`;
  if (dt) url += `&doc_type=${dt}`;
  if (st) url += `&status=${st}`;
  try {
    const data = await apiGet(url);
    allDocuments = data.documents || [];
    renderTable('allDocsTable', allDocuments, true);
  } catch (err) {
    console.error('Load docs failed:', err);
    showToast('Failed to load documents', 'error');
  }
}

async function loadAutoVerified() {
  try {
    const data = await apiGet(`${API_BASE}/documents?method=auto&limit=100`);
    renderTable('autoVerifiedTable', data.documents || [], true);
  } catch (err) { console.error(err); }
}

async function loadDocsByStatus(status, containerId) {
  try {
    const data = await apiGet(`${API_BASE}/documents?status=${status}&limit=100`);
    renderTable(containerId, data.documents || [], true);
  } catch (err) { console.error(err); }
}

// ══════════════════════════════════════════════════════════════
// TABLE
// ══════════════════════════════════════════════════════════════

function renderTable(containerId, docs, showActions) {
  const c = document.getElementById(containerId);
  if (!c) return;

  if (!docs.length) {
    c.innerHTML = '<div class="empty-state"><div style="font-size:40px;margin-bottom:12px">📭</div><div class="empty-state-title">No documents found</div><div class="empty-state-text">Documents will appear here once uploaded.</div></div>';
    return;
  }

  let h = `<table><thead><tr>
    <th>Ref ID</th><th>Type</th><th>Name</th><th>Status</th><th>Method</th>
    <th>Quality</th><th>OCR</th><th>Fraud</th><th>Date</th>
    ${showActions ? '<th>Actions</th>' : ''}
  </tr></thead><tbody>`;

  for (const d of docs) {
    const q = d.quality_score != null ? Math.round(d.quality_score) + '%' : '—';
    const o = d.ocr_confidence != null ? Math.round(d.ocr_confidence * 100) + '%' : '—';
    const f = d.fraud_risk != null ? Math.round(d.fraud_risk) + '%' : '—';
    const dup = (d.upload_count || 1) > 1 ? `<span class="badge badge-dup">${d.upload_count}x</span>` : '';

    h += `<tr onclick="openDetail('${d.request_id}')">
      <td class="td-id">${d.request_id || '—'} ${dup}</td>
      <td>${docLabel(d.document_type)}</td>
      <td>${trunc(d.name, 22)}</td>
      <td>${statusBadge(d.status)}</td>
      <td>${methodBadge(d.verification_method)}</td>
      <td>${q}</td><td>${o}</td><td>${f}</td>
      <td style="font-size:11px;color:var(--text-muted)">${fmtDate(d.saved_at)}</td>
      ${showActions ? `<td onclick="event.stopPropagation()">
        <div style="display:flex;gap:4px">
          ${d.status === 'needs_review' ? `
            <button class="btn-success btn-sm" onclick="quickAction('${d.request_id}','verified')">Approve</button>
            <button class="btn-danger btn-sm" onclick="quickAction('${d.request_id}','rejected')">Reject</button>
          ` : `
            <button class="btn-outline btn-sm" onclick="openDetail('${d.request_id}')">View</button>
          `}
        </div>
      </td>` : ''}
    </tr>`;
  }

  h += '</tbody></table>';
  c.innerHTML = h;
}


// ── Image Preview Function ─────────────────────────────────────────

function openImagePreview(requestId) {
  const modal    = document.getElementById('imageModal');
  const imgEl    = document.getElementById('previewImage');

  if (!modal || !imgEl) {
    console.error('Image modal DOM elements not found');
    showToast('Image preview not available', 'error');
    return;
  }

  // Reset and show modal immediately with loading state
  imgEl.src = '';
  imgEl.alt = 'Loading…';
  modal.classList.add('open');

  const imageUrl = `http://localhost:8000/api/v1/dashboard/documents/${requestId}/image`;

  // Pre-load the image
  const tempImg = new Image();

  tempImg.onload = () => {
    imgEl.src = imageUrl;
    imgEl.alt = 'Document image';
  };

  tempImg.onerror = () => {
    imgEl.alt = 'Image could not be loaded';
    imgEl.src = '';
    // Show error message inside modal
    const inner = modal.querySelector('.image-modal-inner');
    if (inner && !inner.querySelector('.img-error-msg')) {
      const errMsg = document.createElement('div');
      errMsg.className = 'img-error-msg';
      errMsg.style.cssText = 'color:#fff;text-align:center;padding:40px 20px;font-size:14px;';
      errMsg.innerHTML = '⚠️ Image not available<br><small style="opacity:0.7">The document image could not be loaded.</small>';
      inner.appendChild(errMsg);
    }
  };

  tempImg.src = imageUrl;
}




// ── Close Image Modal ──────────────────────────────────────────────

function closeImageModal() {
  document.getElementById('imageModal')?.classList.remove('open');
  const img = document.getElementById('previewImage');
  if (img) img.src = '';
}


// ══════════════════════════════════════════════════════════════
// QUICK ACTIONS
// ══════════════════════════════════════════════════════════════

async function quickAction(id, status) {
  if (!confirm(`Mark document ${id} as "${status}"?`)) return;
  try {
    await apiPut(`${API_BASE}/documents/${id}/status`, {
      status,
      reviewed_by: document.getElementById('adminName')?.textContent || 'admin',
    });
    showToast(`Document updated to ${status}`, 'success');
    refreshCurrentView();
  } catch (err) {
    console.error(err);
    showToast('Failed to update', 'error');
  }
}

// ══════════════════════════════════════════════════════════════
// DETAIL MODAL
// ══════════════════════════════════════════════════════════════

async function openDetail(requestId) {
  try {
    const doc = await apiGet(`${API_BASE}/documents/${requestId}`);
    selectedDoc = doc;
    renderDetail(doc);
    document.getElementById('detailModal').classList.add('open');
  } catch (err) {
    console.error(err);
    showToast('Failed to load details', 'error');
  }
}

function closeModal() {
  document.getElementById('detailModal').classList.remove('open');
  selectedDoc = null;
}


function openImagePreview(requestId) {
  const img = document.getElementById('previewImage');
  img.src = `${IMAGE_API}/${requestId}/image`;
  document.getElementById('imageModal').classList.add('open');
}

function renderDetail(doc) {
  const fields = doc.extracted_fields || {};
  const quality = doc.quality || {};
  const ocr = doc.ocr || {};
  const fraud = doc.fraud || {};
  const matching = doc.matching || {};

  document.getElementById('modalTitle').textContent = `Document: ${doc.request_id || 'Unknown'}`;

  let b = '';

  // ── Document Image Preview ──
  if (doc._image_path) {
    const isPdfDoc    = (doc._image_path || '').toLowerCase().endsWith('.pdf')
                        || doc.is_pdf === true;
    const imageUrl    = `${IMAGE_API}/${doc.request_id}/image`;
    const totalPages  = doc.total_pages || doc.pages_processed || '';

    if (isPdfDoc) {
      b += `
        <div class="detail-section">
          <div class="detail-section-title">
            <i data-lucide="file-text" style="width:16px;height:16px"></i> Document
          </div>
          <div style="
            width:100%;
            background:linear-gradient(135deg,#f0fdf4,#e8f5e9);
            border:2px dashed #a7f3d0;
            border-radius:12px;
            display:flex;
            flex-direction:column;
            align-items:center;
            justify-content:center;
            gap:12px;
            padding:28px 20px;
            text-align:center;
          ">
            <span style="font-size:52px;line-height:1">📄</span>
            <div>
              <div style="font-size:15px;font-weight:700;color:#2d6a4f;margin-bottom:4px">
                PDF Document
              </div>
              <div style="font-size:12px;color:#6b7280">
                ${totalPages ? `${totalPages} pages` : 'Multi-page document'}
              </div>
            </div>
            <div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center">
              <button
                onclick="openPdfInBrowser('${imageUrl}')"
                style="
                  display:inline-flex;align-items:center;gap:6px;
                  background:#2d6a4f;color:white;
                  padding:8px 18px;border-radius:8px;
                  border:none;cursor:pointer;
                  font-size:13px;font-weight:600;
                ">
                📄 Open PDF
              </button>
              <button
                onclick="downloadPdf('${imageUrl}', '${doc.request_id}')"
                style="
                  display:inline-flex;align-items:center;gap:6px;
                  background:#f3f4f6;color:#374151;
                  padding:8px 18px;border-radius:8px;
                  border:1px solid #e5e7eb;cursor:pointer;
                  font-size:13px;font-weight:600;
                ">
                ⬇ Download PDF
              </button>
            </div>
          </div>
        </div>`;
    } else {
      b += `
        <div class="detail-section">
          <div class="detail-section-title">
            <i data-lucide="image" style="width:16px;height:16px"></i> Document Image
          </div>
          <div class="doc-preview-container" onclick="openImagePreview('${doc.request_id}')">
            <div style="text-align:center">
              <img src="${imageUrl}" alt="Document"
                onerror="this.parentElement.innerHTML='<div style=padding:20px;color:var(--text-muted)>📷 Image not available</div>'" />
              <div class="doc-preview-label">Click to enlarge</div>
            </div>
          </div>
        </div>`;
    }
  }
  // ── Overview ──
  b += `
    <div class="detail-section">
      <div class="detail-section-title">
        <i data-lucide="clipboard-list" style="width:16px;height:16px"></i> Overview
      </div>
      <div class="detail-grid">
        <div class="detail-item"><span class="detail-label">Status</span><span class="detail-value">${statusBadge(doc.status)}</span></div>
        <div class="detail-item"><span class="detail-label">Verification</span><span class="detail-value">${methodBadge(doc.verification_method)}</span></div>
        <div class="detail-item"><span class="detail-label">Document Type</span><span class="detail-value">${docLabel(doc.document_type)}</span></div>


<div class="detail-item">
  <span class="detail-label">Reference ID</span>
  <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
    <span class="detail-value mono" id="ref-id-${doc.request_id}">${doc.request_id || '—'}</span>
    <button
      class="copy-btn"
      onclick="copyToClipboard('${(doc.request_id || '').replace(/'/g, "\\'")}', this)"
      title="Copy Reference ID">
      Copy
    </button>
  </div>
</div>
        <div class="detail-item"><span class="detail-label">Farmer ID</span><span class="detail-value mono">${doc.farmer_id || '—'}</span></div>
        <div class="detail-item"><span class="detail-label">Submitted</span><span class="detail-value">${fmtDate(doc._saved_at)}</span></div>
        <div class="detail-item"><span class="detail-label">Processing Time</span><span class="detail-value">${doc.processing_time || '—'}s</span></div>
        <div class="detail-item"><span class="detail-label">Upload Count</span><span class="detail-value">${doc.upload_count || 1} ${(doc.upload_count || 1) > 1 ? '<span class="badge badge-dup">duplicate</span>' : ''}</span></div>
      </div>
    </div>`;

  // ── Extracted Fields ──
  const fe = Object.entries(fields).filter(([k, v]) => v != null && !k.startsWith('_') && k !== 'raw_fields' && k !== 'document_type');
  // Replace the extracted fields section:
if (fe.length) {
    b += `
      <div class="detail-section">
        <div class="detail-section-title">
          <i data-lucide="file-text" style="width:16px;height:16px"></i> Extracted Fields (OCR)
        </div>
        <div class="detail-grid">
          ${fe.map(([k, v]) => {
            const safeVal = String(v).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
            return `
              <div class="detail-item">
                <span class="detail-label">${k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
                <div style="display:flex;align-items:flex-start;gap:6px;flex-wrap:wrap">
                  <span class="detail-value" style="flex:1;min-width:0;word-break:break-all">${v}</span>
                  <button
                    class="copy-btn"
                    onclick="copyToClipboard('${safeVal}', this)"
                    title="Copy value">
                    Copy
                  </button>
                </div>
              </div>`;
          }).join('')}
        </div>
      </div>`;
}


// ── OCR Raw Text Section with Extract Button ──────────────────────────────
const rawText = (doc.ocr && doc.ocr.raw_text) ? doc.ocr.raw_text : '';

b += `
  <div class="detail-section" id="ocr-section-${doc.request_id}">
    <div class="detail-section-title" style="display:flex;justify-content:space-between;align-items:center">
      <span>
        <i data-lucide="scan-text" style="width:16px;height:16px"></i> OCR Extracted Data
      </span>
      <div style="display:flex;gap:8px">
        <button
          class="btn-outline btn-sm"
          onclick="toggleOcrRaw('${doc.request_id}')"
          id="ocr-toggle-${doc.request_id}">
          Show Raw Text
        </button>
        <button
          class="btn-primary btn-sm btn-icon"
          onclick="extractOcrTable('${doc.request_id}')"
          title="Extract all OCR fields to a formatted table">
          <i data-lucide="table" style="width:14px;height:14px"></i> Extract Details
        </button>
      </div>
    </div>

    <!-- Tabular extraction output — hidden by default, shown on button click -->
    <div id="ocr-table-${doc.request_id}" style="display:none;margin-top:12px">
      <!-- Populated by extractOcrTable() -->
    </div>

    <!-- Raw text — hidden by default -->
    <div id="ocr-raw-${doc.request_id}"
         style="display:none;background:#f8f8f8;border:1px solid #e0e0e0;
                border-radius:8px;padding:12px;font-size:11px;
                font-family:monospace;white-space:pre-wrap;
                max-height:200px;overflow-y:auto;margin-top:8px;
                color:#333;line-height:1.6;">
      ${rawText ? rawText.replace(/</g,'&lt;').replace(/>/g,'&gt;') : 'No raw text available'}
    </div>
  </div>`;

  // ── Scores ──
  const qs = quality.overall_score != null ? Math.round(quality.overall_score) : null;
  const oc = ocr.confidence != null ? Math.round((typeof ocr.confidence === 'number' && ocr.confidence <= 1 ? ocr.confidence * 100 : ocr.confidence)) : null;
  const fr = fraud.risk_score != null ? Math.round(fraud.risk_score) : null;
  const ms = matching.overall_score != null ? Math.round(matching.overall_score) : null;

  b += `
    <div class="detail-section">
      <div class="detail-section-title">
        <i data-lucide="bar-chart-2" style="width:16px;height:16px"></i> Scores
      </div>
      <div class="detail-grid">
        ${qs != null ? `<div class="detail-item"><span class="detail-label">Image Quality</span><span class="detail-value">${qs}%</span><div class="score-bar"><div class="score-bar-fill ${scoreColor(qs)}" style="width:${qs}%"></div></div></div>` : ''}
        ${oc != null ? `<div class="detail-item"><span class="detail-label">OCR Confidence</span><span class="detail-value">${oc}%</span><div class="score-bar"><div class="score-bar-fill ${scoreColor(oc)}" style="width:${oc}%"></div></div></div>` : ''}
        ${ms != null ? `<div class="detail-item"><span class="detail-label">DB Match</span><span class="detail-value">${ms}%</span><div class="score-bar"><div class="score-bar-fill ${scoreColor(ms)}" style="width:${ms}%"></div></div></div>` : ''}
        ${fr != null ? `<div class="detail-item"><span class="detail-label">Fraud Risk</span><span class="detail-value">${fr}%</span><div class="score-bar"><div class="score-bar-fill ${scoreColor(100 - fr)}" style="width:${fr}%"></div></div>
          <div style="font-size:10px;color:var(--text-light);margin-top:2px">${fr <= 30 ? 'Low risk — normal compression artifacts' : fr <= 60 ? 'Medium — review recommended' : 'High — possible tampering'}</div>
        </div>` : ''}
      </div>
    </div>`;


  

  // ── Fraud Flags ──
  const flags = fraud.flags || [];
  if (flags.length) {
    b += `
      <div class="detail-section">
        <div class="detail-section-title">
          <i data-lucide="shield-alert" style="width:16px;height:16px"></i> Fraud Detection Details
        </div>
        <div style="display:flex;flex-direction:column;gap:6px">
          ${flags.map(f => {
            const text = typeof f === 'string' ? f : (f.description || f.flag || JSON.stringify(f));
            return `<div style="background:var(--bg);padding:8px 12px;border-radius:6px;font-size:12px;display:flex;align-items:center;gap:8px">
              <i data-lucide="alert-circle" style="width:14px;height:14px;color:var(--warning);flex-shrink:0"></i>
              <span>${text}</span>
            </div>`;
          }).join('')}
          <div style="font-size:11px;color:var(--text-light);margin-top:4px;padding:4px 8px">
            Note: ELA (Error Level Analysis) can flag normal JPEG compression. Scores below 30% are typically safe.
          </div>
        </div>
      </div>`;
  }


  b += `
    <div class="detail-section">
      <div class="detail-section-title" style="display:flex;justify-content:space-between;align-items:center">
        <span><i data-lucide="sparkles" style="width:16px;height:16px"></i> AI Review Assistant</span>
        <button id="ai-review-btn-${doc.request_id}"
                class="btn-primary btn-sm"
                onclick="runAiReview('${doc.request_id}')">
          🤖 Ask AI
        </button>
      </div>
      <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px">
        AI-powered analysis — consistency checks, red flags, and approval recommendation.
      </div>
      <div id="ai-review-panel-${doc.request_id}" style="display:none"></div>
    </div>`;

  // ── Admin Notes ──
  b += `
    <div class="detail-section">
      <div class="detail-section-title">
        <i data-lucide="edit-3" style="width:16px;height:16px"></i> Admin Notes
      </div>
      <textarea id="adminNotesInput" class="admin-notes-input" placeholder="Add notes…">${doc.admin_notes || ''}</textarea>
      ${doc.reviewed_by ? `<div style="font-size:11px;color:var(--text-light);margin-top:4px">Last reviewed by: ${doc.reviewed_by} at ${fmtDate(doc.reviewed_at)}</div>` : ''}
    </div>`;

  // ── Audit Trail ──
  if (doc.admin_history && doc.admin_history.length) {
    b += `
      <div class="detail-section">
        <div class="detail-section-title">
          <i data-lucide="history" style="width:16px;height:16px"></i> Audit Trail
        </div>
        <div style="display:flex;flex-direction:column;gap:4px">
          ${doc.admin_history.map(h => {
            const statusChange = h.updates?.status || '';
            return `<div style="background:var(--bg);padding:8px 12px;border-radius:6px;font-size:11px;display:flex;justify-content:space-between;align-items:center">
              <span><strong>${h.by || 'admin'}</strong> ${statusChange ? `changed status to <strong>${statusChange}</strong>` : 'updated'}</span>
              <span style="color:var(--text-light)">${fmtDate(h.timestamp)}</span>
            </div>`;
          }).join('')}
        </div>
      </div>`;
  }






 // ── Set modal body — ONCE ──────────────────────────────────────────────
  document.getElementById('modalBody').innerHTML = b;
  if (window.lucide) lucide.createIcons();

  // ── Footer — declare footerHtml FIRST, then build, then set ────────────
  const id            = doc.request_id;
  const currentStatus = doc.status;
  let footerHtml      = '';   // declared before any use

  if (currentStatus === 'needs_review') {
    footerHtml = `
      <button class="btn-success btn-icon" onclick="updateStatus('${id}','verified')">
        <i data-lucide="check-circle" style="width:14px;height:14px"></i> Approve
      </button>
      <button class="btn-danger btn-icon" onclick="updateStatus('${id}','rejected')">
        <i data-lucide="x-circle" style="width:14px;height:14px"></i> Reject
      </button>`;
  } else if (currentStatus === 'verified') {
    footerHtml = `
      <button class="btn-outline btn-icon" onclick="updateStatus('${id}','needs_review')">
        <i data-lucide="undo-2" style="width:14px;height:14px"></i> Send Back
      </button>
      <button class="btn-danger btn-icon"
              onclick="if(confirm('Reject this verified document?')) updateStatus('${id}','rejected')">
        <i data-lucide="x-circle" style="width:14px;height:14px"></i> Reject
      </button>`;
  } else if (currentStatus === 'rejected') {
    footerHtml = `
      <button class="btn-success btn-icon" onclick="updateStatus('${id}','verified')">
        <i data-lucide="check-circle" style="width:14px;height:14px"></i> Approve
      </button>
      <button class="btn-outline btn-icon" onclick="updateStatus('${id}','needs_review')">
        <i data-lucide="undo-2" style="width:14px;height:14px"></i> Send Back
      </button>`;
  }

  // Add Delete + Download JSON + Close — ONCE, at the end
  footerHtml += `
    <button class="btn-danger btn-sm" style="margin-left:auto"
            onclick="softDeleteDocument('${id}')"
            title="Soft delete — recoverable within 30 days">
      🗑️ Delete
    </button>
    <button class="btn-outline btn-icon" onclick="downloadResultJson('${id}')">
      ⬇ Download JSON
    </button>
    <button class="btn-outline" onclick="closeModal()">Close</button>`;

  // Set footer — ONCE
  document.getElementById('modalFooter').innerHTML = footerHtml;
  if (window.lucide) lucide.createIcons();

} 

// ══════════════════════════════════════════════════════════════
// AI REVIEW ASSISTANT
// ══════════════════════════════════════════════════════════════

async function runAiReview(requestId) {
  const container = document.getElementById(`ai-review-panel-${requestId}`);
  const btn       = document.getElementById(`ai-review-btn-${requestId}`);

  if (!container) return;

  // Show loading state
  if (btn) {
    btn.disabled    = true;
    btn.textContent = '🤖 Analyzing…';
  }

  container.style.display = 'block';
  container.innerHTML = `
    <div style="display:flex;align-items:center;gap:12px;padding:16px;
                background:#f0fdf4;border-radius:8px;border:1px solid #bbf7d0">
      <div style="font-size:24px">🤖</div>
      <div>
        <div style="font-weight:600;color:#2d6a4f;font-size:13px">AI is analyzing this document…</div>
        <div style="font-size:11px;color:#6b7280;margin-top:2px">Checking consistency, flags, and generating recommendation</div>
      </div>
      <div style="margin-left:auto">
        <div class="typing-indicator" style="display:flex;gap:4px">
          <div style="width:6px;height:6px;border-radius:50%;background:#2d6a4f;animation:bounce 1s infinite"></div>
          <div style="width:6px;height:6px;border-radius:50%;background:#2d6a4f;animation:bounce 1s infinite 0.15s"></div>
          <div style="width:6px;height:6px;border-radius:50%;background:#2d6a4f;animation:bounce 1s infinite 0.3s"></div>
        </div>
      </div>
    </div>`;

  try {
    const resp = await fetch(`${API_BASE}/documents/${requestId}/ai-review`, {
      method: 'POST',
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const data              = resp.ok ? await resp.json() : null;
    const analysis          = data?.analysis           || 'AI review unavailable.';
    const mode              = data?.mode               || 'unknown';
    const visualCrossCheck  = data?.visual_cross_check ?? false;

    // ── Visual cross-check badge ──────────────────────────────────────────
    const crossCheckBadge = visualCrossCheck
        ? `<div style="
                display:inline-flex;
                align-items:center;
                gap:6px;
                background:#d1fae5;
                color:#2d6a4f;
                padding:5px 12px;
                border-radius:12px;
                font-size:11px;
                font-weight:600;
                border:1px solid #a7f3d0;
           ">
               🖼️ Visual cross-check performed — fields verified against document image
           </div>`
        : `<div style="
                display:inline-flex;
                align-items:center;
                gap:6px;
                background:#fff3e0;
                color:#e65100;
                padding:5px 12px;
                border-radius:12px;
                font-size:11px;
                font-weight:600;
                border:1px solid #fed7aa;
           ">
               ⚠️ Visual cross-check not available — text analysis only
           </div>`;

    // ── Mode badge ────────────────────────────────────────────────────────
    const modeBadge = mode === 'live'
        ? `<span style="
                background:rgba(255,255,255,0.2);
                padding:2px 8px;
                border-radius:10px;
                font-size:10px;
           ">LLM Vision API • Live</span>`
        : `<span style="
                background:rgba(255,255,255,0.15);
                padding:2px 8px;
                border-radius:10px;
                font-size:10px;
           ">Demo Mode</span>`;

    // ── Render the AI analysis ────────────────────────────────────────────
    container.innerHTML = `
      <div style="background:#f8fffe;border:1px solid #bbf7d0;border-radius:10px;overflow:hidden">

        <!-- Header -->
        <div style="background:linear-gradient(135deg,#2d6a4f,#40916c);padding:12px 16px;
                    display:flex;align-items:center;justify-content:space-between">
          <div style="display:flex;align-items:center;gap:8px;color:#fff">
            <span style="font-size:18px">🤖</span>
            <span style="font-weight:700;font-size:14px">AI Review Assistant</span>
            ${modeBadge}
          </div>
          <button onclick="document.getElementById('ai-review-panel-${requestId}').style.display='none'"
                  style="background:rgba(255,255,255,0.2);border:none;color:#fff;cursor:pointer;
                         border-radius:50%;width:24px;height:24px;font-size:14px;
                         display:flex;align-items:center;justify-content:center">✕</button>
        </div>

        <!-- Visual cross-check badge -->
        <div style="padding:10px 16px 0 16px;display:flex;align-items:center;flex-wrap:wrap;gap:6px;">
          ${crossCheckBadge}
        </div>

        <!-- Analysis content -->
        <div style="padding:14px 16px;">
          ${renderMarkdown(analysis)}
        </div>

        <!-- Footer note -->
        <div style="padding:8px 16px;background:#f0fdf4;border-top:1px solid #bbf7d0;
                    font-size:10px;color:#6b7280">
          ⚠️ AI analysis is advisory only. Human review is always the final authority.
        </div>

      </div>`;

    if (btn) {
      btn.disabled    = false;
      btn.textContent = '🤖 Re-analyze';
    }

    showToast('AI analysis complete', 'success');

  } catch (err) {
    console.error('AI review failed:', err);
    container.innerHTML = `
      <div style="background:#fde8e8;border:1px solid #fca5a5;border-radius:8px;
                  padding:12px 16px;font-size:12px;color:#c62828">
        ⚠️ AI analysis unavailable. Check your VPN connection and try again.
      </div>`;
    if (btn) {
      btn.disabled    = false;
      btn.textContent = '🤖 Ask AI';
    }
    showToast('AI review failed — check VPN', 'error');
  }
}

function renderMarkdown(text) {
  // Minimal markdown: bold, headers, line breaks
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^### (.+)$/gm,   '<div style="font-weight:700;font-size:13px;color:#2d6a4f;margin:10px 0 4px">$1</div>')
    .replace(/^## (.+)$/gm,    '<div style="font-weight:800;font-size:14px;color:#1b4332;margin:12px 0 6px;border-bottom:1px solid #bbf7d0;padding-bottom:4px">$1</div>')
    .replace(/\n/g, '<br>');
}







async function downloadResultJson(requestId) {
  try {
    const resp = await fetch(`http://localhost:8000/api/v1/extract/${requestId}/json`);
    const data = await resp.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `farmerverify_${requestId}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('JSON downloaded', 'success');
  } catch (e) {
    showToast('Download failed', 'error');
  }
}




// ══════════════════════════════════════════════════════════════
// OCR TABLE EXTRACTOR — standalone functions, NOT inside renderDetail
// ══════════════════════════════════════════════════════════════

function toggleOcrRaw(requestId) {
  const raw = document.getElementById(`ocr-raw-${requestId}`);
  const btn = document.getElementById(`ocr-toggle-${requestId}`);
  if (!raw) return;
  const hidden = raw.style.display === 'none';
  raw.style.display = hidden ? 'block' : 'none';
  if (btn) btn.textContent = hidden ? 'Hide Raw Text' : 'Show Raw Text';
}

function extractOcrTable(requestId) {
  const container = document.getElementById(`ocr-table-${requestId}`);
  if (!container) return;

  const doc = selectedDoc;
  if (!doc) {
    container.innerHTML = '<p style="color:#999;font-size:12px">No document data available.</p>';
    container.style.display = 'block';
    return;
  }

  const fields   = doc.extracted_fields || {};
  const ocrInfo  = doc.ocr      || {};
  const quality  = doc.quality  || {};
  const matching = doc.matching || {};
  const fraud    = doc.fraud    || {};

  const allRows = [];

  Object.entries(fields).forEach(([k, v]) => {
    if (v == null || k.startsWith('_') || k === 'document_type') return;
    allRows.push({
      section: 'Extracted Field',
      field:   k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      value:   String(v),
    });
  });

  allRows.push({ section: 'Document Info', field: 'Reference ID',    value: doc.request_id    || '—' });
  allRows.push({ section: 'Document Info', field: 'Document Type',   value: (doc.document_type || '').replace(/_/g,' ') });
  allRows.push({ section: 'Document Info', field: 'Status',          value: doc.status        || '—' });
  allRows.push({ section: 'Document Info', field: 'Submitted',       value: doc.saved_at      || '—' });
  allRows.push({ section: 'Document Info', field: 'Processing Time', value: (doc.processing_time || '—') + 's' });

  if (quality.overall_score  != null) allRows.push({ section: 'Pipeline Score', field: 'Image Quality',  value: Math.round(quality.overall_score) + '%' });
  if (ocrInfo.confidence     != null) allRows.push({ section: 'Pipeline Score', field: 'OCR Confidence', value: Math.round((ocrInfo.confidence <= 1 ? ocrInfo.confidence * 100 : ocrInfo.confidence)) + '%' });
  if (matching.overall_score != null) allRows.push({ section: 'Pipeline Score', field: 'DB Match Score', value: Math.round(matching.overall_score) + '%' });
  if (fraud.risk_score       != null) allRows.push({ section: 'Pipeline Score', field: 'Fraud Risk',     value: Math.round(fraud.risk_score) + '%' });
  if (ocrInfo.language_detected)      allRows.push({ section: 'Pipeline Score', field: 'Language',       value: ocrInfo.language_detected });

  if (!allRows.length) {
    container.innerHTML = '<p style="color:#999;font-size:12px;padding:8px">No data extracted yet.</p>';
    container.style.display = 'block';
    return;
  }

  const sections = {};
  allRows.forEach(r => {
    if (!sections[r.section]) sections[r.section] = [];
    sections[r.section].push(r);
  });

  const csvString = ['Section,Field,Value',
    ...allRows.map(r => `"${r.section}","${r.field}","${r.value.replace(/"/g,'""')}"`)
  ].join('\n');

  const sectionColors = {
    'Extracted Field': { bg: '#f0fdf4', border: '#bbf7d0', header: '#16a34a' },
    'Document Info':   { bg: '#eff6ff', border: '#bfdbfe', header: '#2563eb' },
    'Pipeline Score':  { bg: '#fefce8', border: '#fde68a', header: '#d97706' },
  };

  let html = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
      <span style="font-size:12px;font-weight:600;color:var(--primary-dark)">${allRows.length} fields extracted</span>
      <div style="display:flex;gap:8px">
        <button class="btn-outline btn-sm" id="csv-btn-${requestId}" onclick="copyOcrCsv('${requestId}')">Copy All (CSV)</button>
        <button class="btn-outline btn-sm" id="json-btn-${requestId}" onclick="copyOcrJson('${requestId}')">Copy as JSON</button>
      </div>
    </div>`;

  Object.entries(sections).forEach(([sName, rows]) => {
    const c = sectionColors[sName] || { bg: '#f9fafb', border: '#e5e7eb', header: '#374151' };
    html += `
      <div style="margin-bottom:12px;border:1px solid ${c.border};border-radius:8px;overflow:hidden">
        <div style="background:${c.bg};padding:6px 12px;font-size:11px;font-weight:700;
                    color:${c.header};text-transform:uppercase;letter-spacing:0.5px">${sName}</div>
        <table style="width:100%;border-collapse:collapse;font-size:12px">
          <thead><tr style="background:#f9fafb">
            <th style="padding:6px 12px;text-align:left;font-weight:600;color:#6b7280;border-bottom:1px solid #e5e7eb;width:40%">Field</th>
            <th style="padding:6px 12px;text-align:left;font-weight:600;color:#6b7280;border-bottom:1px solid #e5e7eb">Value</th>
            <th style="padding:6px 12px;text-align:center;font-weight:600;color:#6b7280;border-bottom:1px solid #e5e7eb;width:70px">Copy</th>
          </tr></thead>
          <tbody>`;

    rows.forEach((row, idx) => {
      const rowBg  = idx % 2 === 0 ? '#fff' : '#fafafa';
      const fieldId = `ocr-val-${requestId}-${idx}-${sName.replace(/\s/g,'')}`;
      html += `
            <tr style="background:${rowBg};border-bottom:1px solid #f0f0f0">
              <td style="padding:7px 12px;color:#374151;font-weight:500">${row.field}</td>
              <td style="padding:7px 12px;color:#111827;word-break:break-all">
                <span id="${fieldId}">${row.value}</span>
              </td>
              <td style="padding:7px 12px;text-align:center">
                <button class="copy-btn"
                        onclick="copyToClipboard(document.getElementById('${fieldId}').textContent, this)"
                        style="font-size:10px;padding:2px 8px">Copy</button>
              </td>
            </tr>`;
    });

    html += '</tbody></table></div>';
  });

  container.innerHTML = html;
  container.style.display = 'block';
  if (window.lucide) lucide.createIcons();

  const csvBtn  = document.getElementById(`csv-btn-${requestId}`);
  const jsonBtn = document.getElementById(`json-btn-${requestId}`);
  if (csvBtn)  csvBtn.dataset.csv  = csvString;
  if (jsonBtn) jsonBtn.dataset.json = JSON.stringify(fields, null, 2);
}

function copyOcrCsv(requestId) {
  const btn = document.getElementById(`csv-btn-${requestId}`);
  const csv = btn ? btn.dataset.csv : '';
  if (!csv) return;
  window.copyToClipboard(csv, btn);
  showToast('All fields copied as CSV', 'success');
}

function copyOcrJson(requestId) {
  const btn  = document.getElementById(`json-btn-${requestId}`);
  const json = btn ? btn.dataset.json : '';
  if (!json) return;
  window.copyToClipboard(json, btn);
  showToast('Fields copied as JSON', 'success');
}

function markCopied(btn) {
  if (!btn) { showToast('Copied!', 'success'); return; }
  const orig = btn.innerHTML;
  const origColor  = btn.style.color;
  const origBorder = btn.style.borderColor;
  btn.innerHTML = '✓';
  btn.style.color = '#2d6a4f';
  btn.style.borderColor = '#2d6a4f';
  btn.disabled = true;
  setTimeout(() => {
    btn.innerHTML = orig;
    btn.style.color = origColor;
    btn.style.borderColor = origBorder;
    btn.disabled = false;
  }, 2000);
}





// ══════════════════════════════════════════════════════════════
// STATUS UPDATE
// ══════════════════════════════════════════════════════════════

async function updateStatus(id, status) {
  const notes = document.getElementById('adminNotesInput')?.value || '';
  const admin = document.getElementById('adminName')?.textContent || 'admin';

  let reason = '';
  if (status === 'rejected') {
    reason = prompt('Rejection reason (optional):') || '';
  }

  try {
    await apiPut(`${API_BASE}/documents/${id}/status`, {
      status,
      admin_notes: notes,
      reviewed_by: admin,
      rejection_reason_admin: reason,
    });
    showToast(`Document updated to "${status}"`, 'success');
    closeModal();
    refreshCurrentView();
  } catch (err) {
    console.error(err);
    showToast('Failed to update status', 'error');
  }
}

// ══════════════════════════════════════════════════════════════
// SEARCH
// ══════════════════════════════════════════════════════════════

async function handleGlobalSearch() {
  const q = document.getElementById('globalSearch').value.trim();
  if (!q) return;
  switchView('search');
  document.getElementById('advancedSearchInput').value = q;
  await handleAdvancedSearch();
}

async function handleAdvancedSearch() {
  const q = document.getElementById('advancedSearchInput').value.trim();
  if (!q || q.length < 2) { showToast('Enter at least 2 characters', 'info'); return; }

  try {
    const data = await apiGet(`${API_BASE}/search?q=${encodeURIComponent(q)}&limit=50`);
    const c = document.getElementById('searchResults');

    if (!data.documents?.length) {
      c.innerHTML = '<div class="empty-state"><div style="font-size:40px;margin-bottom:12px">🔍</div><div class="empty-state-title">No results</div><div class="empty-state-text">Try a different search term.</div></div>';
      return;
    }

    let h = `<div style="margin-bottom:12px;font-size:13px;color:var(--text-muted)">Found <strong>${data.count}</strong> results for "<strong>${q}</strong>"</div>`;
    h += '<table><thead><tr><th>Ref ID</th><th>Type</th><th>Name</th><th>Aadhaar</th><th>Account</th><th>Status</th><th>Date</th></tr></thead><tbody>';
    for (const d of data.documents) {
      h += `<tr onclick="openDetail('${d.request_id}')">
        <td class="td-id">${d.request_id}</td>
        <td>${docLabel(d.document_type)}</td>
        <td>${d.name || '—'}</td>
        <td style="font-family:monospace;font-size:11px">${d.aadhaar_number || '—'}</td>
        <td style="font-family:monospace;font-size:11px">${d.account_number || '—'}</td>
        <td>${statusBadge(d.status)}</td>
        <td style="font-size:11px;color:var(--text-muted)">${fmtDate(d.saved_at)}</td>
      </tr>`;
    }
    h += '</tbody></table>';
    c.innerHTML = h;

  } catch (err) { console.error(err); showToast('Search failed', 'error'); }
}

document.getElementById('globalSearch')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') handleGlobalSearch();
});
document.getElementById('advancedSearchInput')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') handleAdvancedSearch();
});

// ══════════════════════════════════════════════════════════════
// REFRESH
// ══════════════════════════════════════════════════════════════

function refreshData() { refreshCurrentView(); showToast('Dashboard refreshed', 'info'); }

function refreshCurrentView() {
  switch (currentView) {
    case 'overview': loadOverview(); break;
    case 'all-docs': loadDocuments(); break;
    case 'auto-verified': loadAutoVerified(); break;
    case 'needs-review': loadDocsByStatus('needs_review', 'reviewDocsTable'); break;
    case 'verified': loadDocsByStatus('verified', 'verifiedDocsTable'); break;
    case 'rejected': loadDocsByStatus('rejected', 'rejectedDocsTable'); break;
  }
}

// ══════════════════════════════════════════════════════════════
// FARMER PROFILES
// ══════════════════════════════════════════════════════════════

async function loadFarmerProfiles(searchQuery) {
  const container = document.getElementById('farmerProfilesContainer');
  if (!container) return;

  container.innerHTML = '<div style="padding:40px;text-align:center;color:#9ca3af">Loading...</div>';

  try {
    let url = `${API_BASE}/farmers?limit=100`;
    if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;
    const data = await apiGet(url);
    renderFarmerProfiles(data.profiles || []);
  } catch (err) {
    console.error('Failed to load farmer profiles:', err);
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">👤</div>
        <div class="empty-state-title">Could not load profiles</div>
        <div class="empty-state-text">Upload some documents first.</div>
      </div>`;
  }
}

function searchFarmers() {
  const q = document.getElementById('farmerSearchInput')?.value?.trim() || '';
  loadFarmerProfiles(q || undefined);
}

document.getElementById('farmerSearchInput')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') searchFarmers();
});

function renderFarmerProfiles(profiles) {
  const container = document.getElementById('farmerProfilesContainer');
  if (!container) return;

  if (!profiles.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">👤</div>
        <div class="empty-state-title">No Farmer Profiles Yet</div>
        <div class="empty-state-text">
          Upload Aadhaar, Land Record, and Bank Passbook documents.<br>
          They will automatically be grouped here by farmer.
        </div>
      </div>`;
    return;
  }

  let html = `<div style="display:flex;flex-direction:column;gap:16px">`;

  for (const p of profiles) {
    const isComplete = p.onboarding_complete;
    const score      = p.avg_onboarding_score || 0;
    const scoreColor = score >= 80 ? '#2d6a4f' : score >= 60 ? '#e65100' : '#c62828';
    const progressPct = Math.round((p.docs_verified?.length || 0) / 3 * 100);

    // Document chips
    const DOC_ICONS = {
      aadhaar_card:  '🆔', bank_passbook: '🏦',
      land_record:   '🏞️', voter_id:      '🗳️',
    };
    const DOC_LABELS = {
      aadhaar_card: 'Aadhaar', bank_passbook: 'Passbook',
      land_record: 'Land Record', voter_id: 'Voter ID',
    };

    const docChips = (p.documents || []).map(d => {
      const isVerified = d.status === 'verified';
      const chipColor  = isVerified ? '#2d6a4f' : '#e65100';
      const chipBg     = isVerified ? '#d8f3dc' : '#fff3e0';
      return `<span style="display:inline-flex;align-items:center;gap:4px;
                            background:${chipBg};color:${chipColor};
                            padding:3px 10px;border-radius:12px;font-size:11px;
                            font-weight:600;white-space:nowrap">
                ${DOC_ICONS[d.document_type] || '📄'} ${DOC_LABELS[d.document_type] || d.document_type}
                ${isVerified ? '✓' : '⏳'}
              </span>`;
    }).join(' ');

    const missingChips = (p.docs_missing_labels || []).map(label =>
      `<span style="display:inline-flex;align-items:center;gap:4px;
                    background:#fde8e8;color:#c62828;
                    padding:3px 10px;border-radius:12px;font-size:11px;
                    font-weight:600;white-space:nowrap">
         ❌ ${label} Missing
       </span>`
    ).join(' ');

    html += `
      <div style="background:#fff;border:1px solid ${isComplete ? '#bbf7d0' : '#e5e7eb'};
                  border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06)">

        <!-- Header -->
        <div style="padding:16px 20px;display:flex;align-items:center;gap:16px;
                    border-bottom:1px solid #f0f0f0;flex-wrap:wrap">

          <!-- Avatar -->
          <div style="width:48px;height:48px;border-radius:50%;
                      background:${isComplete ? '#d8f3dc' : '#f3f4f6'};
                      display:flex;align-items:center;justify-content:center;
                      font-size:20px;flex-shrink:0">
            ${isComplete ? '✅' : '👤'}
          </div>

          <!-- Name and Aadhaar -->
          <div style="flex:1;min-width:150px">
            <div style="font-weight:700;font-size:15px;color:#1a1a2e">
              ${p.farmer_name || 'Unknown Farmer'}
            </div>
            ${p.farmer_name_local ? `<div style="font-size:12px;color:#6b7280">${p.farmer_name_local}</div>` : ''}
            <div style="font-size:11px;color:#9ca3af;margin-top:2px;font-family:monospace">
              Aadhaar: ${p.aadhaar_number || '—'}
            </div>
          </div>

          <!-- Onboarding status badge -->
          <div style="text-align:center">
            ${isComplete
              ? `<div style="background:#d8f3dc;color:#2d6a4f;padding:6px 16px;
                             border-radius:20px;font-size:12px;font-weight:700">
                   ✅ Fully Onboarded
                 </div>`
              : `<div style="background:#fff3e0;color:#e65100;padding:6px 16px;
                             border-radius:20px;font-size:12px;font-weight:700">
                   ⏳ ${p.onboarding_progress}
                 </div>`
            }
          </div>

          <!-- Onboarding score -->
          <div style="text-align:center;min-width:80px">
            <div style="font-size:28px;font-weight:800;color:${scoreColor};line-height:1">${score}</div>
            <div style="font-size:10px;color:#9ca3af">Score / 100</div>
          </div>
        </div>

        <!-- Progress bar -->
        <div style="height:4px;background:#f0f0f0">
          <div style="height:100%;width:${progressPct}%;
                      background:${isComplete ? '#2d6a4f' : '#e65100'};
                      transition:width 0.5s"></div>
        </div>

        <!-- Documents section -->
        <div style="padding:12px 20px;display:flex;flex-wrap:wrap;gap:6px;align-items:center">
          <span style="font-size:11px;color:#9ca3af;margin-right:4px">Submitted:</span>
          ${docChips || '<span style="font-size:11px;color:#9ca3af">No documents yet</span>'}
          ${missingChips ? `
            <span style="font-size:11px;color:#9ca3af;margin-left:8px">Missing:</span>
            ${missingChips}
          ` : ''}
        </div>

        <!-- Individual document scores (collapsible) -->
        <div style="padding:0 20px 12px">
          <div style="display:flex;flex-wrap:wrap;gap:8px">
            ${(p.documents || []).map(d => `
              <div onclick="openDetail('${d.request_id}')"
                   style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;
                          padding:8px 12px;cursor:pointer;transition:all 0.15s;
                          min-width:120px"
                   onmouseover="this.style.borderColor='#2d6a4f'"
                   onmouseout="this.style.borderColor='#e5e7eb'">
                <div style="font-size:11px;font-weight:600;color:#374151">
                  ${DOC_ICONS[d.document_type] || '📄'} ${DOC_LABELS[d.document_type] || d.document_type}
                </div>
                ${d.onboarding_score != null ? `
                  <div style="margin-top:4px">
                    <div style="display:flex;justify-content:space-between;font-size:10px;color:#9ca3af">
                      <span>Score</span>
                      <span style="font-weight:600;color:${
                        d.onboarding_score >= 80 ? '#2d6a4f' :
                        d.onboarding_score >= 60 ? '#e65100' : '#c62828'
                      }">${d.onboarding_score}</span>
                    </div>
                    <div style="height:3px;background:#e5e7eb;border-radius:2px;margin-top:2px">
                      <div style="height:100%;width:${d.onboarding_score}%;
                                  background:${
                                    d.onboarding_score >= 80 ? '#2d6a4f' :
                                    d.onboarding_score >= 60 ? '#e65100' : '#c62828'
                                  };border-radius:2px"></div>
                    </div>
                  </div>
                ` : ''}
                <div style="margin-top:4px">${statusBadge(d.status) || d.status}</div>
                <div style="font-size:9px;color:#9ca3af;margin-top:2px;font-family:monospace">
                  ${(d.request_id || '').substring(0, 10)}…
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>`;
  }

  html += `</div>`;
  container.innerHTML = html;

  if (window.lucide) lucide.createIcons();
}

async function softDeleteDocument(requestId) {
  if (!confirm(
    'Are you sure you want to delete this document?\n\n' +
    'The document will be hidden from the dashboard but can be recovered within 30 days.'
  )) return;

  const admin = document.getElementById('adminName')?.textContent || 'admin';

  try {
    const r = await fetch(
      `${API_BASE}/documents/${requestId}?reviewed_by=${encodeURIComponent(admin)}`,
      { method: 'DELETE' }
    );
    if (!r.ok) throw new Error(`HTTP ${r.status}`);

    showToast('Document deleted. Can be recovered within 30 days.', 'success');
    closeModal();
    refreshCurrentView();
  } catch (err) {
    console.error('Delete failed:', err);
    showToast('Failed to delete document.', 'error');
  }
}

async function restoreDocument(requestId) {
  if (!confirm('Restore this document? It will reappear in the dashboard.')) return;

  const admin = document.getElementById('adminName')?.textContent || 'admin';

  try {
    const r = await fetch(
      `${API_BASE}/documents/${requestId}/restore?reviewed_by=${encodeURIComponent(admin)}`,
      { method: 'POST' }
    );
    if (!r.ok) throw new Error(`HTTP ${r.status}`);

    showToast('Document restored successfully.', 'success');
    refreshCurrentView();
  } catch (err) {
    console.error('Restore failed:', err);
    showToast('Failed to restore document.', 'error');
  }
}


async function loadDeletedItems() {
  const container = document.getElementById('deletedItemsTable');
  if (!container) return;

  try {
    // Call the deleted items endpoint
    const resp = await fetch(`${API_BASE}/documents/deleted`);
    const data = resp.ok ? await resp.json() : { documents: [] };
    const docs = data.documents || [];

    if (!docs.length) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🗑️</div>
          <div class="empty-state-title">No Deleted Items</div>
          <div class="empty-state-text">
            Documents deleted by admins will appear here and can be restored within 30 days.
          </div>
        </div>`;
      return;
    }

    let h = `
      <table>
        <thead>
          <tr>
            <th>Ref ID</th>
            <th>Type</th>
            <th>Name</th>
            <th>Status (before delete)</th>
            <th>Deleted By</th>
            <th>Deleted At</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>`;

    for (const d of docs) {
      const fields = d.extracted_fields || {};
      const name   = fields.name || fields.name_local || '—';

      h += `
        <tr>
          <td class="td-id">${(d.request_id || '—').substring(0, 12)}</td>
          <td>${docLabel(d.document_type)}</td>
          <td>${trunc(name, 22)}</td>
          <td>${statusBadge(d.status)}</td>
          <td style="font-size:11px;color:var(--text-muted)">${d.deleted_by || '—'}</td>
          <td style="font-size:11px;color:var(--text-muted)">${fmtDate(d.deleted_at)}</td>
          <td>
            <button
              class="btn-outline btn-sm"
              onclick="restoreDocument('${d.request_id}')"
              style="color:#2d6a4f;border-color:#2d6a4f">
              ↩️ Restore
            </button>
          </td>
        </tr>`;
    }

    h += '</tbody></table>';
    container.innerHTML = h;

  } catch (err) {
    console.error('Failed to load deleted items:', err);
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-title">Could not load deleted items</div>
      </div>`;
  }
}


// Modal close handlers
document.getElementById('detailModal')?.addEventListener('click', e => { if (e.target.id === 'detailModal') closeModal(); });
document.getElementById('imageModal')?.addEventListener('click', e => { if (e.target.id === 'imageModal') closeImageModal(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeModal(); closeImageModal(); } });




// ── Expose functions called from HTML onclick attributes ──────────────────────
// All functions used in onclick="..." must be on window to be accessible
// from dynamically generated HTML and inline event handlers.

window.searchFarmers        = searchFarmers;
window.loadFarmerProfiles   = loadFarmerProfiles;
window.renderFarmerProfiles = renderFarmerProfiles;
// ══════════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════════

// Initialize Lucide icons
document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();
});


function markCopied(btn) {
  if (!btn) { showToast('Copied!', 'success'); return; }
  const orig = btn.innerHTML;
  const origColor  = btn.style.color;
  const origBorder = btn.style.borderColor;
  btn.innerHTML = '✓';
  btn.style.color = '#2d6a4f';
  btn.style.borderColor = '#2d6a4f';
  btn.disabled = true;
  setTimeout(() => {
    btn.innerHTML = orig;
    btn.style.color = origColor;
    btn.style.borderColor = origBorder;
    btn.disabled = false;
  }, 2000);
}


// ── PDF helpers ───────────────────────────────────────────────────────────────
function openPdfInBrowser(url) {
  // Open PDF in a new tab — browser will display it inline
  window.open(url, '_blank', 'noopener,noreferrer');
}

function downloadPdf(url, requestId) {
  // Force download
  const a       = document.createElement('a');
  a.href        = url;
  a.download    = `document_${requestId}.pdf`;
  a.target      = '_blank';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  showToast('PDF download started', 'success');
}
// ══════════════════════════════════════════════════════════════
// EXPOSE ALL FUNCTIONS TO WINDOW (required for onclick= attributes)
// ══════════════════════════════════════════════════════════════
window.switchView             = switchView;
window.toggleSidebar          = toggleSidebar;
window.refreshData            = refreshData;
window.handleGlobalSearch     = handleGlobalSearch;
window.handleAdvancedSearch   = handleAdvancedSearch;
window.openDetail             = openDetail;
window.closeModal             = closeModal;
window.openImagePreview       = openImagePreview;
window.closeImageModal        = closeImageModal;
window.updateStatus           = updateStatus;
window.quickAction            = quickAction;
window.quickActionCC          = quickActionCC;
window.openCCDetail           = openCCDetail;
window.copyToClipboard        = copyToClipboard;
window.markCopied             = markCopied;
window.downloadResultJson     = downloadResultJson;
window.exportVerifiedFarmers  = exportVerifiedFarmers;
window.searchFarmers          = searchFarmers;
window.loadFarmerProfiles     = loadFarmerProfiles;
window.toggleOcrRaw           = toggleOcrRaw;
window.extractOcrTable        = extractOcrTable;
window.copyOcrCsv             = copyOcrCsv;
window.copyOcrJson            = copyOcrJson;
window.runAiReview = runAiReview;
window.softDeleteDocument = softDeleteDocument;
window.restoreDocument    = restoreDocument;
window.loadDeletedItems   = loadDeletedItems;
window.openPdfInBrowser = openPdfInBrowser;
window.downloadPdf      = downloadPdf;




// Init
loadOverview();
setInterval(() => {
  if (currentView === 'overview' || currentView === 'needs-review') {
    refreshCurrentView();
  }
}, 30000);


