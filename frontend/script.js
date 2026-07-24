const API_BASE = window.AUDITRON_API_BASE || 'http://localhost:8000';

const form      = document.getElementById('audit-form');
const urlInput  = document.getElementById('url-input');
const submitBtn = document.getElementById('submit-btn');
const clearBtn  = document.getElementById('clear-btn');
const loadingEl = document.getElementById('loading');
const errorEl   = document.getElementById('error');
const reportEl  = document.getElementById('report');

urlInput.addEventListener('input', () => {
  if (urlInput.value.length > 0) {
    clearBtn.classList.remove('hidden');
  } else {
    clearBtn.classList.add('hidden');
  }
});

clearBtn.addEventListener('click', () => {
  urlInput.value = '';
  clearBtn.classList.add('hidden');
  urlInput.focus();
  hideAll();
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();

  const rawUrl = urlInput.value.trim();
  if (!rawUrl) {
    showError('Please enter a URL before auditing.', null);
    return;
  }

  hideAll();
  setLoading(true);

  try {
    const res = await fetch(`${API_BASE}/api/audit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: rawUrl }),
    });

    let data;
    try {
      data = await res.json();
    } catch {
      throw new Error('The audit service returned an unreadable response.');
    }

    setLoading(false);

    if (!res.ok) {
      const msg  = data?.error?.message || 'Something went wrong while auditing that page.';
      const code = data?.error?.code    || null;
      showError(msg, code);
      return;
    }

    renderReport(data);
    show(reportEl);

  } catch (err) {
    setLoading(false);
    const msg = err instanceof Error && err.message
      ? err.message
      : 'Could not reach the audit service. Is the backend running and reachable?';
    showError(msg, null);
  }
});

function setLoading(isLoading) {
  if (isLoading) {
    show(loadingEl);
    submitBtn.disabled = true;
    urlInput.disabled  = true;
    clearBtn.classList.add('hidden');
  } else {
    hide(loadingEl);
    submitBtn.disabled = false;
    urlInput.disabled  = false;
    if (urlInput.value.length > 0) {
      clearBtn.classList.remove('hidden');
    }
  }
}

function hideAll() {
  hide(errorEl);
  hide(reportEl);
  hide(loadingEl);
}

function show(el) { el.classList.remove('hidden'); }
function hide(el) { el.classList.add('hidden'); }

function showError(message, code) {
  errorEl.innerHTML = '';

  const msgNode = document.createElement('p');
  msgNode.style.margin = '0';
  msgNode.textContent = message;
  errorEl.appendChild(msgNode);

  if (code) {
    const codeNode = document.createElement('p');
    codeNode.className = 'error-code';
    codeNode.textContent = `Error code: ${code}`;
    errorEl.appendChild(codeNode);
  }

  show(errorEl);
}

function renderReport(report) {
  const statusClass = statusColour(report.status);
  const statusLabel = `${report.status} ${httpStatusText(report.status)}`;

  const altMissing = report.imagesMissingAlt;
  const altTotal   = report.totalImages;
  const altRatio   = altTotal > 0 ? `${altMissing} / ${altTotal}` : '0 images';
  const altClass   = altMissing > 0 ? 'val-warn' : 'val-ok';

  const h1Class = report.h1Count === 1 ? 'val-ok'
                : report.h1Count === 0 ? 'val-warn'
                : 'val-warn';

  const fetchedAtFormatted = formatDate(report.fetchedAt);

  reportEl.innerHTML = `
    <p class="report-heading" title="${escapeHtml(report.url)}">
      ${escapeHtml(truncate(report.url, 72))}
    </p>
    <ul class="report-list">
      <li>
        <strong>HTTP status</strong>
        <span class="${statusClass}">${statusLabel}</span>
      </li>
      <li>
        <strong>Response time</strong>
        <span>${report.responseTimeMs} ms</span>
      </li>
      <li>
        <strong>Title</strong>
        ${report.title
          ? `<span>${escapeHtml(report.title)}</span>`
          : `<span class="val-missing">(none found)</span>`}
      </li>
      <li>
        <strong>Meta description</strong>
        ${report.metaDescription
          ? `<span>${escapeHtml(report.metaDescription)}</span>`
          : `<span class="val-missing">(none found)</span>`}
      </li>
      <li>
        <strong>H1 headings</strong>
        <span class="${h1Class}">${report.h1Count}</span>
      </li>
      <li>
        <strong>Images missing alt</strong>
        <span class="${altClass}">${altRatio}</span>
      </li>
      <li>
        <strong>Word count (approx)</strong>
        <span>${report.approxWordCount.toLocaleString()}</span>
      </li>
      <li>
        <strong>Fetched at</strong>
        <span>${escapeHtml(fetchedAtFormatted)}</span>
      </li>
    </ul>
  `;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = String(str ?? '');
  return div.innerHTML;
}

function truncate(str, maxLen) {
  return str.length > maxLen ? str.slice(0, maxLen - 1) + '…' : str;
}

function statusColour(status) {
  if (status >= 200 && status < 300) return 'val-ok';
  if (status >= 300 && status < 400) return '';
  if (status >= 400 && status < 500) return 'val-warn';
  return 'val-err';
}

function httpStatusText(status) {
  const texts = {
    200: 'OK', 201: 'Created', 204: 'No Content',
    301: 'Moved Permanently', 302: 'Found', 304: 'Not Modified',
    400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden',
    404: 'Not Found', 405: 'Method Not Allowed', 429: 'Too Many Requests',
    500: 'Internal Server Error', 502: 'Bad Gateway', 503: 'Service Unavailable',
    504: 'Gateway Timeout',
  };
  return texts[status] || '';
}

function formatDate(isoString) {
  try {
    return new Date(isoString).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  } catch {
    return isoString;
  }
}
