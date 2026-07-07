/**
 * Qanuni API Client — طبقة الربط البرمجي الموحدة
 * يتعامل مع المصادقة، تجديد التوكن، وإرسال الطلبات للواجهة الخلفية (FastAPI)
 */

const API_BASE = window.QANUNI_API_URL || 'http://localhost:8000/api/v1';

// ─── Auth Session Management ────────────────────────────────────────────────

const QaniniAuth = {
  getToken()        { return localStorage.getItem('token'); },
  getRefreshToken() { return localStorage.getItem('refresh_token'); },
  getUser()         { try { return JSON.parse(localStorage.getItem('user')); } catch { return null; } },

  setSession(accessToken, refreshToken, user) {
    localStorage.setItem('token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    localStorage.setItem('user', JSON.stringify(user));
    document.cookie = `token=${encodeURIComponent(accessToken)}; path=/; SameSite=Lax; max-age=${7 * 86400}`;
  },

  clearSession() {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    document.cookie = 'token=; path=/; SameSite=Lax; max-age=0';
  },

  isLoggedIn() {
    return !!this.getToken();
  },

  logout() {
    this.clearSession();
    window.location.href = 'login.html';
  }
};

// ─── Auth Guard (for protected pages) ───────────────────────────────────────

function requireAuth() {
  if (!QaniniAuth.isLoggedIn()) {
    window.location.href = 'login.html';
    return false;
  }
  return true;
}

// ─── Token Refresh Queue ────────────────────────────────────────────────────

let _isRefreshing = false;
let _refreshQueue = [];

function _processQueue(error, token) {
  _refreshQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  _refreshQueue = [];
}

async function _refreshAccessToken() {
  const refreshToken = QaniniAuth.getRefreshToken();
  if (!refreshToken) {
    QaniniAuth.logout();
    throw new Error('No refresh token');
  }

  const res = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken })
  });

  if (!res.ok) {
    QaniniAuth.logout();
    throw new Error('Refresh failed');
  }

  const data = await res.json();
  QaniniAuth.setSession(data.access_token, data.refresh_token, data.user);
  return data.access_token;
}

// ─── Main API Fetch Function ────────────────────────────────────────────────

/**
 * Send an authenticated request to the FastAPI backend.
 * Automatically handles token refresh on 401.
 *
 * @param {string} endpoint - e.g. '/auth/login', '/search/', '/analysis/query'
 * @param {object} options  - { method, body, headers, isFormData }
 * @returns {Promise<any>}  - Parsed JSON response
 */
async function apiFetch(endpoint, options = {}) {
  const { method = 'GET', body, headers = {}, isFormData = false } = options;

  const token = QaniniAuth.getToken();
  const fetchHeaders = { ...headers };

  if (token) {
    fetchHeaders['Authorization'] = `Bearer ${token}`;
  }

  if (!isFormData && method !== 'GET') {
    fetchHeaders['Content-Type'] = 'application/json';
  }

  const fetchOptions = { method, headers: fetchHeaders };

  if (body) {
    fetchOptions.body = isFormData ? body : JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(`${API_BASE}${endpoint}`, fetchOptions);
  } catch (netErr) {
    throw new Error(`خطأ في الاتصال بالخادم: تأكد من تشغيل الواجهة الخلفية (Backend) وصحة الاتصال. (التفاصيل: ${netErr.message || netErr})`);
  }

  // Handle 401 - Token expired → try refresh
  if (res.status === 401 && token) {
    if (_isRefreshing) {
      // Wait for ongoing refresh
      const newToken = await new Promise((resolve, reject) => {
        _refreshQueue.push({ resolve, reject });
      });
      fetchHeaders['Authorization'] = `Bearer ${newToken}`;
      res = await fetch(`${API_BASE}${endpoint}`, { ...fetchOptions, headers: fetchHeaders });
    } else {
      _isRefreshing = true;
      try {
        const newToken = await _refreshAccessToken();
        _processQueue(null, newToken);
        fetchHeaders['Authorization'] = `Bearer ${newToken}`;
        res = await fetch(`${API_BASE}${endpoint}`, { ...fetchOptions, headers: fetchHeaders });
      } catch (err) {
        _processQueue(err, null);
        throw err;
      } finally {
        _isRefreshing = false;
      }
    }
  }

  // Parse response
  if (!res.ok) {
    let errorData;
    try { errorData = await res.json(); } catch { errorData = { detail: `HTTP ${res.status}` }; }
    
    let errorMsg = `Error ${res.status}`;
    if (errorData && errorData.detail) {
      if (typeof errorData.detail === 'string') {
        errorMsg = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        errorMsg = errorData.detail.map(e => {
          const field = e.loc ? e.loc.join('.') : 'field';
          return `${field}: ${e.msg}`;
        }).join(', ');
      } else if (typeof errorData.detail === 'object') {
        errorMsg = JSON.stringify(errorData.detail);
      } else {
        errorMsg = String(errorData.detail);
      }
    }
    
    const err = new Error(errorMsg);
    err.status = res.status;
    err.data = errorData;
    throw err;
  }

  // Handle binary responses (PDF, etc.)
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/pdf') || contentType.includes('octet-stream')) {
    return res.blob();
  }

  return res.json();
}

// ─── Convenience Auth Functions ─────────────────────────────────────────────

async function apiLogin(email, password) {
  const data = await apiFetch('/auth/login', {
    method: 'POST',
    body: { email, password }
  });
  QaniniAuth.setSession(data.access_token, data.refresh_token, data.user);
  return data;
}

async function apiRegister({ email, password, full_name, phone, role }) {
  const data = await apiFetch('/auth/register', {
    method: 'POST',
    body: { email, password, full_name, phone, role }
  });
  QaniniAuth.setSession(data.access_token, data.refresh_token, data.user);
  return data;
}

// ─── Dashboard / Subscription ───────────────────────────────────────────────

async function apiGetUsage() {
  return apiFetch('/subscriptions/usage');
}

async function apiGetSubscription() {
  return apiFetch('/subscriptions/me');
}

// ─── Cases ──────────────────────────────────────────────────────────────────

async function apiListCases(skip = 0, limit = 20) {
  return apiFetch(`/cases/?skip=${skip}&limit=${limit}`);
}

async function apiCreateCase(data) {
  return apiFetch('/cases/', { method: 'POST', body: data });
}

async function apiGetCase(caseId) {
  return apiFetch(`/cases/${caseId}`);
}

async function apiDeleteCase(caseId) {
  return apiFetch(`/cases/${caseId}`, { method: 'DELETE' });
}

// ─── Documents ──────────────────────────────────────────────────────────────

async function apiListDocuments(caseId = null) {
  const params = caseId ? `?case_id=${caseId}` : '';
  return apiFetch(`/documents/${params}`);
}

async function apiUploadDocument(file, title, docType, caseId) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('title', title || file.name);
  formData.append('doc_type', docType || 'other');
  if (caseId) formData.append('case_id', caseId);
  return apiFetch('/documents/upload', { method: 'POST', body: formData, isFormData: true });
}

async function apiReprocessAdvanced(docId) {
  return apiFetch(`/documents/${docId}/reprocess-advanced`, { method: 'POST' });
}

// ─── Search ─────────────────────────────────────────────────────────────────

async function apiSearch(query, docType = null, page = 1, size = 10, category = null, divisionId = null) {
  let url = `/search/?q=${encodeURIComponent(query)}&page=${page}&size=${size}`;
  if (docType) url += `&doc_type=${encodeURIComponent(docType)}`;
  if (category) url += `&category=${encodeURIComponent(category)}`;
  if (divisionId) url += `&division_id=${encodeURIComponent(divisionId)}`;
  return apiFetch(url);
}

// ─── Laws Library ────────────────────────────────────────────────────────────

async function apiListLaws(category = null, skip = 0, limit = 50) {
  let url = `/laws/?skip=${skip}&limit=${limit}`;
  if (category && category !== 'all') url += `&category=${encodeURIComponent(category)}`;
  return apiFetch(url);
}

async function apiSearchLaws(q, category = null, year = null) {
  let url = `/laws/search?q=${encodeURIComponent(q || '')}`;
  if (category && category !== 'all') url += `&category=${encodeURIComponent(category)}`;
  if (year) url += `&year=${year}`;
  return apiFetch(url);
}

async function apiGetLaw(lawId) {
  return apiFetch(`/laws/${lawId}`);
}

async function apiLegalTree() {
  return apiFetch('/legal-tree');
}


// ─── AI Analysis (RAG) ─────────────────────────────────────────────────────

async function apiQuery(question, topK = 5) {
  return apiFetch('/analysis/query', { method: 'POST', body: { question, top_k: topK } });
}

async function apiAnalyze(text, analysisType = 'general') {
  return apiFetch('/analysis/analyze', { method: 'POST', body: { text, analysis_type: analysisType } });
}

async function apiDraft(docType, context, instructions = '') {
  return apiFetch('/analysis/draft', { method: 'POST', body: { doc_type: docType, context, instructions } });
}

async function apiDraftToPdf(text, title, docType) {
  return apiFetch('/analysis/draft-to-pdf', { method: 'POST', body: { text, title, doc_type: docType } });
}

async function apiDraftToDocx(text, title, docType) {
  return apiFetch('/analysis/draft-to-docx', { method: 'POST', body: { text, title, doc_type: docType } });
}

async function apiExtractText(file) {
  const formData = new FormData();
  formData.append('file', file);
  return apiFetch('/analysis/extract-text', { method: 'POST', body: formData, isFormData: true });
}

// ─── UI Helpers ─────────────────────────────────────────────────────────────

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
    padding: 12px 28px; border-radius: 12px; font-size: 14px; font-weight: 500;
    z-index: 99999; animation: fadeInUp 0.3s ease; direction: rtl;
    color: #fff; box-shadow: 0 8px 32px rgba(0,0,0,0.2);
    background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6'};
  `;
  document.body.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3500);
}

function setLoadingState(btn, loading, originalText) {
  if (loading) {
    btn.disabled = true;
    btn.dataset.originalText = btn.textContent;
    btn.textContent = 'جارٍ التحميل...';
    btn.style.opacity = '0.7';
  } else {
    btn.disabled = false;
    btn.textContent = originalText || btn.dataset.originalText || 'إرسال';
    btn.style.opacity = '1';
  }
}

function updateUserUI() {
  const user = QaniniAuth.getUser();
  if (!user) return;
  document.querySelectorAll('[data-user-name]').forEach(el => el.textContent = user.full_name);
  document.querySelectorAll('[data-user-email]').forEach(el => el.textContent = user.email);
  document.querySelectorAll('[data-user-role]').forEach(el => {
    const roles = { admin: 'مدير', lawyer: 'محامي', client: 'مستخدم', reviewer: 'مراجع' };
    el.textContent = roles[user.role] || user.role;
  });
}
