// ============================================================
//  ShieldNet — popup.js
//  Lógica de la UI del popup
// ============================================================

// ── Elementos del DOM ──
const siteCard     = document.getElementById('siteCard');
const riskIcon     = document.getElementById('riskIcon');
const riskTitle    = document.getElementById('riskTitle');
const domainText   = document.getElementById('domainText');
const scoreBar     = document.getElementById('scoreBar');
const scoreNum     = document.getElementById('scoreNum');
const checksList   = document.getElementById('checksList');
const historyList  = document.getElementById('historyList');
const footerStatus = document.getElementById('footerStatus');
const btnReport    = document.getElementById('btnReport');

// ── Configuración de riesgo → UI ──
const RISK_CONFIG = {
  SAFE: {
    icon: '✅', title: 'Sitio Seguro',
    class: 'safe', barColor: '#3fb950', textColor: 'var(--green)'
  },
  WARNING: {
    icon: '⚠️', title: 'Sitio Sospechoso',
    class: 'warning', barColor: '#d29922', textColor: 'var(--yellow)'
  },
  DANGER: {
    icon: '🚨', title: 'Sitio Peligroso',
    class: 'danger', barColor: '#f85149', textColor: 'var(--red)'
  }
};

// ── Inicializar popup ──
async function init() {
  // Obtener tab activo
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url) return;

  const url = tab.url;
  const domain = extractDomain(url);
  domainText.textContent = domain;

  // Pedir resultado al background
  chrome.runtime.sendMessage({ type: 'GET_CURRENT_RESULT' }, (response) => {
    if (response?.lastResult) {
      renderResult(response.lastResult);
    } else {
      // No hay resultado aún, solicitar análisis
      chrome.runtime.sendMessage({ type: 'ANALYZE_URL', url }, (result) => {
        if (result) renderResult(result);
        else renderError();
      });
    }

    // Actualizar stats
    if (response?.stats) {
      updateStats(response.stats);
    }
  });

  // Cargar historial
  loadHistory();

  // Cargar configuración de toggles
  loadSettings();
}

// ── Renderizar resultado del análisis ──
function renderResult(result) {
  const config = RISK_CONFIG[result.risk] || RISK_CONFIG.WARNING;

  // Actualizar card
  siteCard.className = `site-card ${config.class}`;
  riskIcon.textContent = config.icon;
  riskTitle.textContent = config.title;
  riskTitle.style.color = config.textColor;
  domainText.textContent = result.domain;

  // Score bar
  const pct = result.score;
  scoreBar.style.width = pct + '%';
  scoreBar.style.background = config.barColor;
  scoreNum.textContent = `${pct}/100`;
  scoreNum.style.color = config.textColor;

  // Checks
  renderChecks(result.checks);

  // Guardar en historial
  saveToHistory(result);

  // Footer
  if (result.risk === 'DANGER') {
    footerStatus.innerHTML = '<span style="color: var(--red)">● Peligro detectado</span>';
  } else if (result.risk === 'WARNING') {
    footerStatus.innerHTML = '<span style="color: var(--yellow)">● Precaución recomendada</span>';
  } else {
    footerStatus.innerHTML = '<span style="color: var(--green)">● Sitio verificado</span>';
  }
}

// ── Renderizar lista de checks ──
function renderChecks(checks) {
  if (!checks) return;

  const items = [
    {
      icon: '🔒',
      label: 'Protocolo HTTPS',
      badge: checks.isHTTPS ? 'SEGURO' : 'HTTP ✗',
      type: checks.isHTTPS ? 'ok' : 'bad'
    },
    {
      icon: '📋',
      label: 'Lista negra',
      badge: checks.inBlacklist ? 'BLOQUEADO' : 'LIMPIO',
      type: checks.inBlacklist ? 'bad' : 'ok'
    },
    {
      icon: '🔍',
      label: 'Typosquatting',
      badge: checks.isTyposquatting?.detected
        ? `Imita: ${checks.isTyposquatting.imitates}` : 'OK',
      type: checks.isTyposquatting?.detected ? 'bad' : 'ok'
    },
    {
      icon: '📅',
      label: 'Antigüedad dominio',
      badge: checks.domainAge?.ageCategory === 'NEW' ? '< 30 días'
           : checks.domainAge?.ageCategory === 'RECENT' ? '< 1 año'
           : checks.domainAge?.ageCategory === 'OLD' ? 'Antiguo ✓'
           : 'Desconocido',
      type: checks.domainAge?.ageCategory === 'NEW' ? 'bad'
          : checks.domainAge?.ageCategory === 'RECENT' ? 'warn'
          : 'ok'
    },
    {
      icon: '🌐',
      label: 'Google Safe Browsing',
      badge: !checks.safeBrowsing?.checked ? 'Sin API key'
           : checks.safeBrowsing?.safe ? 'Seguro ✓' : 'AMENAZA ✗',
      type: !checks.safeBrowsing?.checked ? 'info'
          : checks.safeBrowsing?.safe ? 'ok' : 'bad'
    },
    {
      icon: '⚠️',
      label: 'Keywords sospechosas',
      badge: checks.hasSuspiciousKeywords?.detected
        ? checks.hasSuspiciousKeywords.keywords.slice(0, 2).join(', ')
        : 'Ninguna',
      type: checks.hasSuspiciousKeywords?.detected ? 'warn' : 'ok'
    }
  ];

  checksList.innerHTML = items.map(item => `
    <div class="check">
      <div class="check-left">
        <span>${item.icon}</span>
        <span>${item.label}</span>
      </div>
      <span class="badge ${item.type}">${item.badge}</span>
    </div>
  `).join('');
}

// ── Actualizar estadísticas ──
function updateStats(stats) {
  document.getElementById('statBlocked').textContent   = stats.blocked   || 0;
  document.getElementById('statSuspicious').textContent = stats.suspicious || 0;
  document.getElementById('statSafe').textContent      = stats.safe      || 0;
}

function renderError() {
  riskIcon.textContent = '❓';
  riskTitle.textContent = 'No analizable';
  domainText.textContent = 'URL del sistema o vacía';
  checksList.innerHTML = '<div style="color: var(--muted); padding: 8px 12px; font-size: 12px;">No se puede analizar esta página.</div>';
}

// ── Historial ──
function saveToHistory(result) {
  chrome.storage.local.get('history', ({ history = [] }) => {
    // Evitar duplicados seguidos
    if (history[0]?.domain === result.domain) return;
    
    history.unshift({
      domain: result.domain,
      risk: result.risk,
      score: result.score,
      time: Date.now()
    });

    // Guardar máximo 50 entradas
    if (history.length > 50) history = history.slice(0, 50);
    chrome.storage.local.set({ history });
  });
}

function loadHistory() {
  chrome.storage.local.get('history', ({ history = [] }) => {
    if (history.length === 0) {
      historyList.innerHTML = '<div style="color: var(--muted); text-align: center; padding: 20px; font-size: 12px;">Sin historial en esta sesión</div>';
      return;
    }

    const riskEmoji = { SAFE: '✅', WARNING: '⚠️', DANGER: '🚨' };
    
    historyList.innerHTML = history.map(item => {
      const time = new Date(item.time).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
      return `
        <div class="history-item">
          <div style="display:flex; align-items:center; gap:8px;">
            <span>${riskEmoji[item.risk] || '❓'}</span>
            <span class="history-domain">${item.domain}</span>
          </div>
          <div style="display:flex; align-items:center; gap:8px; flex-shrink:0">
            <span class="badge ${item.risk === 'SAFE' ? 'ok' : item.risk === 'WARNING' ? 'warn' : 'bad'}">${item.score}</span>
            <span style="color:var(--muted); font-size:10px">${time}</span>
          </div>
        </div>
      `;
    }).join('');
  });
}

// ── Toggles / Configuración ──
function loadSettings() {
  chrome.storage.local.get('settings', ({ settings = {} }) => {
    const defaults = {
      protection: true, adblocker: true,
      trackers: true, phishing: true, notifications: true
    };
    const merged = { ...defaults, ...settings };

    document.querySelectorAll('[data-setting]').forEach(toggle => {
      const key = toggle.dataset.setting;
      toggle.className = `toggle-switch ${merged[key] ? 'on' : 'off'}`;
    });
  });
}

// ── Event Listeners ──

// Tabs
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');

    if (tab.dataset.tab === 'history') loadHistory();
  });
});

// Toggles
document.querySelectorAll('[data-setting]').forEach(toggle => {
  toggle.parentElement.addEventListener('click', () => {
    const isOn = toggle.classList.contains('on');
    toggle.className = `toggle-switch ${isOn ? 'off' : 'on'}`;
    
    const key = toggle.dataset.setting;
    chrome.storage.local.get('settings', ({ settings = {} }) => {
      settings[key] = !isOn;
      chrome.storage.local.set({ settings });
    });
  });
});

// Botón reportar
btnReport.addEventListener('click', () => {
  chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
    if (!tab?.url) return;
    const domain = extractDomain(tab.url);
    const reportUrl = `https://www.google.com/safebrowsing/report_phish/?hl=es&url=${encodeURIComponent(tab.url)}`;
    chrome.tabs.create({ url: reportUrl });
  });
});

// ── Helpers ──
function extractDomain(url) {
  try { return new URL(url).hostname.replace(/^www\./, ''); }
  catch { return url; }
}

// ── Iniciar ──
init();
