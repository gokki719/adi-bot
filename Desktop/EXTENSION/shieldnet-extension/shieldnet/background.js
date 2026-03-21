// ============================================================
//  ShieldNet — background.js (Service Worker) v1.1
// ============================================================

importScripts('domainScorer.js');

// ── Listas negras offline ──
const BLACKLIST = new Set([
  "secure-login-banorte.xyz", "bancomer-seguro.net", "paypal-verify.tk",
  "amazon-soporte.ml", "apple-id-locked.cf", "netflix-actualizar.ga",
  "microsoft-support-alert.com", "google-security-check.tk",
  "sat-devolucion.xyz", "imss-tramites-online.ml", "bbva-seguridad.cf",
  "hsbc-verificacion.tk", "santander-alerta.ga", "banamex-secure.ml",
  // Dominios de scam conocidos
  "defenseoptimizedcyberlightweight.autos",
  "lightweight-safe-fast-guard.autos",
  "cloud-storage-alert.com", "cloudsecure-alert.net",
  "storage-limit-warning.com", "account-suspended-alert.com"
]);

// ── Dominios legítimos ──
const LEGIT_DOMAINS = [
  "banorte.com", "bancomer.com", "bbva.mx", "hsbc.com.mx",
  "santander.com.mx", "banamex.com", "paypal.com", "amazon.com.mx",
  "apple.com", "microsoft.com", "google.com", "netflix.com",
  "sat.gob.mx", "imss.gob.mx", "facebook.com", "instagram.com",
  "outlook.com", "hotmail.com", "live.com", "onedrive.com"
];

// ── TLDs de muy alto riesgo (casi nunca usados por sitios legítimos) ──
const DANGEROUS_TLDS = new Set([
  '.tk', '.ml', '.ga', '.cf', '.gq',
  '.autos', '.sbs', '.cyou', '.cfd', '.moscow',
  '.bond', '.hair', '.beauty', '.makeup', '.skin',
  '.zip', '.mov' // TLDs nuevos usados en phishing
]);

let stats = { blocked: 0, suspicious: 0, safe: 0, adsBlocked: 0 };
let siteCache = new Map();

// ============================================================
//  LISTENER principal
// ============================================================
chrome.webNavigation.onBeforeNavigate.addListener(async (details) => {
  if (details.frameId !== 0) return;
  const url = details.url;
  if (!url.startsWith('http')) return;

  try {
    const result = await analyzeDomain(url);
    siteCache.set(extractDomain(url), result);
    await chrome.storage.local.set({ lastResult: result, stats });

    chrome.tabs.sendMessage(details.tabId, {
      type: 'DOMAIN_RESULT', result
    }).catch(() => {});

    if (result.risk === 'DANGER') {
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: '🚨 ShieldNet — Sitio Peligroso',
        message: `"${result.domain}" fue detectado como peligroso. ¡No ingreses datos!`,
        priority: 2
      });
      stats.blocked++;
    } else if (result.risk === 'WARNING') {
      stats.suspicious++;
    } else {
      stats.safe++;
    }
    await chrome.storage.local.set({ stats });
  } catch (err) {
    console.error('[ShieldNet]', err);
  }
});

// ============================================================
//  ANÁLISIS PRINCIPAL
// ============================================================
async function analyzeDomain(url) {
  const domain = extractDomain(url);
  const isHTTPS = url.startsWith('https://');

  if (siteCache.has(domain)) return siteCache.get(domain);

  const checks = {
    isHTTPS,
    inBlacklist: BLACKLIST.has(domain),
    isTyposquatting: detectTyposquatting(domain),
    domainAge: await checkDomainAge(domain),
    safeBrowsing: await checkGoogleSafeBrowsing(url),
    hasSuspiciousKeywords: hasSuspiciousKeywords(domain),
    hasDangerousTLD: checkDangerousTLD(domain),
    hasScamStructure: detectScamStructure(domain)
  };

  const score = calculateScore(checks);
  const risk = score >= 70 ? 'SAFE' : score >= 40 ? 'WARNING' : 'DANGER';

  return { domain, url, score, risk, checks, timestamp: Date.now() };
}

// ============================================================
//  NUEVO: Detectar estructura de dominio scam
//  ej: "defenseoptimizedcyberlightweight.autos" → muchas palabras concatenadas
// ============================================================
function detectScamStructure(domain) {
  const base = domain.split('.')[0].toLowerCase();

  // Dominio muy largo (más de 25 chars antes del TLD) = sospechoso
  const tooLong = base.length > 25;

  // Muchas palabras concatenadas sin sentido (palabras de seguridad juntas)
  const securityWords = ['secure', 'defense', 'protect', 'guard', 'safe',
    'cyber', 'shield', 'alert', 'warning', 'critical', 'fast', 'lightweight',
    'optimized', 'cloud', 'storage', 'account', 'login', 'verify', 'update'];
  const wordMatches = securityWords.filter(w => base.includes(w));
  const tooManySecurityWords = wordMatches.length >= 2;

  // Muchos guiones = generado automáticamente
  const hyphens = (base.match(/-/g) || []).length;
  const tooManyHyphens = hyphens >= 3;

  // Números aleatorios en el dominio
  const randomNumbers = /\d{4,}/.test(base);

  const detected = tooLong || tooManySecurityWords || tooManyHyphens || randomNumbers;

  return {
    detected,
    reasons: [
      tooLong && 'Dominio sospechosamente largo',
      tooManySecurityWords && `Palabras de seguridad concatenadas: ${wordMatches.join(', ')}`,
      tooManyHyphens && 'Demasiados guiones (generado automáticamente)',
      randomNumbers && 'Números aleatorios en el dominio'
    ].filter(Boolean)
  };
}

// ============================================================
//  NUEVO: Verificar TLD peligroso
// ============================================================
function checkDangerousTLD(domain) {
  for (const tld of DANGEROUS_TLDS) {
    if (domain.endsWith(tld)) {
      return { detected: true, tld };
    }
  }
  // TLD muy inusual (no .com .net .org .mx .gob.mx etc.)
  const safeTLDs = ['.com', '.net', '.org', '.mx', '.com.mx', '.gob.mx',
    '.edu.mx', '.edu', '.gov', '.io', '.co', '.app', '.dev'];
  const isSafe = safeTLDs.some(t => domain.endsWith(t));
  if (!isSafe) {
    const tld = '.' + domain.split('.').slice(-1)[0];
    return { detected: true, tld, reason: 'TLD poco común' };
  }
  return { detected: false };
}

// ============================================================
//  TYPOSQUATTING
// ============================================================
function detectTyposquatting(domain) {
  const domainBase = domain.replace(/^www\./, '').split('.')[0].toLowerCase();
  for (const legit of LEGIT_DOMAINS) {
    const legitBase = legit.split('.')[0].toLowerCase();
    const dist = levenshtein(domainBase, legitBase);
    if (dist > 0 && dist <= 2 && domainBase !== legitBase) {
      return { detected: true, imitates: legit, distance: dist };
    }
    const normalized = domainBase
      .replace(/1/g, 'l').replace(/0/g, 'o')
      .replace(/rn/g, 'm').replace(/vv/g, 'w');
    if (normalized === legitBase && domainBase !== legitBase) {
      return { detected: true, imitates: legit, method: 'char_substitution' };
    }
  }
  return { detected: false };
}

function levenshtein(a, b) {
  const dp = Array.from({ length: a.length + 1 }, (_, i) =>
    Array.from({ length: b.length + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0))
  );
  for (let i = 1; i <= a.length; i++)
    for (let j = 1; j <= b.length; j++)
      dp[i][j] = a[i-1] === b[j-1]
        ? dp[i-1][j-1]
        : 1 + Math.min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]);
  return dp[a.length][b.length];
}

function hasSuspiciousKeywords(domain) {
  const suspicious = [
    'secure', 'login', 'verify', 'account', 'update', 'confirm',
    'banking', 'soporte', 'seguro', 'verificar', 'actualizar',
    'premio', 'ganaste', 'urgente', 'alerta', 'suspended', 'locked',
    'recovery', 'restore', 'support', 'helpdesk', 'free', 'gratis',
    'defense', 'optimized', 'lightweight', 'guard', 'protect'
  ];
  const lower = domain.toLowerCase();
  const found = suspicious.filter(k => lower.includes(k));
  return { detected: found.length > 0, keywords: found };
}

// ============================================================
//  GOOGLE SAFE BROWSING
// ============================================================
async function checkGoogleSafeBrowsing(url) {
  const API_KEY = 'AIzaSyBAkd6xucAZyQdyy0R6YbxJFQyzLzFH6yg';
  if (API_KEY === 'TU_API_KEY_AQUI') return { checked: false, safe: true };
  try {
    const response = await fetch(
      `https://safebrowsing.googleapis.com/v4/threatMatches:find?key=${API_KEY}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client: { clientId: 'shieldnet', clientVersion: '1.1.0' },
          threatInfo: {
            threatTypes: ['MALWARE', 'SOCIAL_ENGINEERING', 'UNWANTED_SOFTWARE'],
            platformTypes: ['ANY_PLATFORM'],
            threatEntryTypes: ['URL'],
            threatEntries: [{ url }]
          }
        })
      }
    );
    const data = await response.json();
    return { checked: true, safe: !data.matches?.length, threats: data.matches || [] };
  } catch {
    return { checked: false, safe: true };
  }
}

// ============================================================
//  WHOIS — EDAD DEL DOMINIO
// ============================================================
async function checkDomainAge(domain) {
  try {
    const response = await fetch(
      `https://www.whoisxmlapi.com/whoisserver/WhoisService?apiKey=at_aLE7rm4HSpTjsxcmZkCJVbwyojzTZ&domainName=${domain}&outputFormat=JSON`
    );
    const data = await response.json();
    const createdDate = data?.WhoisRecord?.createdDate;
    if (createdDate) {
      const ageDays = Math.floor((Date.now() - new Date(createdDate).getTime()) / 86400000);
      return { known: true, ageDays, ageCategory: ageDays < 30 ? 'NEW' : ageDays < 365 ? 'RECENT' : 'OLD' };
    }
  } catch {}
  return { known: false, ageDays: null, ageCategory: 'UNKNOWN' };
}

// ============================================================
//  SCORE FINAL — ahora con más penalizaciones
// ============================================================
function calculateScore(checks) {
  let score = 100;

  if (!checks.isHTTPS)                        score -= 35;
  if (checks.inBlacklist)                     score -= 60; // subimos de 50 a 60
  if (checks.isTyposquatting.detected)        score -= 40;
  if (!checks.safeBrowsing.safe)              score -= 40;
  if (checks.hasSuspiciousKeywords.detected)  score -= 15;
  if (checks.hasDangerousTLD?.detected)       score -= 30; // NUEVO: TLD peligroso
  if (checks.hasScamStructure?.detected)      score -= 35; // NUEVO: estructura scam

  if (checks.domainAge.ageCategory === 'NEW')    score -= 20;
  if (checks.domainAge.ageCategory === 'RECENT') score -= 10;

  return Math.max(0, Math.min(100, score));
}

function extractDomain(url) {
  try { return new URL(url).hostname.replace(/^www\./, ''); }
  catch { return url; }
}

// ── Mensajes desde popup ──
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === 'GET_CURRENT_RESULT') {
    chrome.storage.local.get(['lastResult', 'stats'], (data) => sendResponse(data));
    return true;
  }
  if (msg.type === 'ANALYZE_URL') {
    analyzeDomain(msg.url).then(sendResponse);
    return true;
  }
  if (msg.type === 'GET_STATS') {
    chrome.storage.local.get('stats', (data) => sendResponse(data.stats || stats));
    return true;
  }
});
