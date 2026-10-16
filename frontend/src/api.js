const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

const SESSION_KEY = 'audit_session_id';

export function getSessionId() {
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

async function request(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    'X-Session-Id': getSessionId(),
    ...(options.headers || {}),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return null;
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/pdf')) return res.blob();
  return res.json();
}

export function createAudit(url) {
  return request('/api/audits', { method: 'POST', body: JSON.stringify({ url }) });
}

export function getAudit(id) {
  return request(`/api/audits/${id}`);
}

export function getReport(id) {
  return request(`/api/audits/${id}/report`);
}

export function listAudits() {
  return request('/api/audits');
}

export function compareAudits(beforeId, afterId) {
  return request(`/api/audits/${beforeId}/compare/${afterId}`);
}

export function pdfUrl(id) {
  return `${API_BASE}/api/audits/${id}/pdf`;
}

export async function downloadPdf(id) {
  const blob = await request(`/api/audits/${id}/pdf`);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `audit-report.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}
