// ============================================================
//  ShieldNet — phishing.js
//  Detector de correos/emails de phishing
//  Analiza texto de correos buscando patrones de fraude
// ============================================================

// ── Patrones de urgencia típicos en phishing ──
const URGENCY_PATTERNS = [
  // Español
  /tu cuenta (será|va a ser) (eliminada|cerrada|suspendida|bloqueada)/i,
  /verifica(r)? (tu|su) cuenta/i,
  /actualiza(r)? (tu|su) (contraseña|información|datos)/i,
  /haz clic (aquí|en el enlace)/i,
  /en las próximas (\d+) horas/i,
  /acceso (limitado|suspendido|bloqueado)/i,
  /confirma(r)? (tu|su) identidad/i,
  /ingresa (tu|su) contraseña/i,
  /ganaste un premio/i,
  /eres el (ganador|afortunado)/i,
  /tu paquete (está detenido|no pudo entregarse)/i,
  /debes pagar (una multa|el importe)/i,
  /SAT: (tienes una multa|debes)/i,
  /IMSS: (verifica|actualiza)/i,
  /si no (actúas|respondes|verificas)/i,
  /de lo contrario (tu|su) cuenta/i,
  
  // Inglés
  /your account (will be|has been) (suspended|terminated|closed)/i,
  /verify your (account|identity|email)/i,
  /click here (immediately|now|urgently)/i,
  /within (\d+) hours/i,
  /unusual (activity|sign-in)/i,
  /confirm your (password|credentials)/i,
  /you have won/i,
  /act (now|immediately)/i
];

// ── Palabras clave de phishing con peso ──
const PHISHING_KEYWORDS = {
  high: [
    'contraseña', 'password', 'banco', 'banco', 'tarjeta', 'crédito',
    'NIP', 'PIN', 'CVV', 'número de cuenta', 'clabe', 'token',
    'suspended', 'suspended account', 'verify now', 'login now'
  ],
  medium: [
    'urgente', 'urgent', 'inmediatamente', 'immediately',
    'premio', 'prize', 'winner', 'ganador', 'gratis', 'free',
    'limitado', 'expira', 'expires', 'vence', 'deadline'
  ],
  low: [
    'haz clic', 'click here', 'enlace', 'link', 'descarga', 'download',
    'adjunto', 'attachment', 'formulario', 'form'
  ]
};

// ── Dominios de remitentes sospechosos ──
const SUSPICIOUS_SENDER_PATTERNS = [
  // Dominio no coincide con la marca que dice ser
  { brand: 'paypal', legitimateDomain: 'paypal.com' },
  { brand: 'amazon', legitimateDomain: 'amazon.com.mx' },
  { brand: 'apple', legitimateDomain: 'apple.com' },
  { brand: 'microsoft', legitimateDomain: 'microsoft.com' },
  { brand: 'google', legitimateDomain: 'google.com' },
  { brand: 'netflix', legitimateDomain: 'netflix.com' },
  { brand: 'bbva', legitimateDomain: 'bbva.mx' },
  { brand: 'banorte', legitimateDomain: 'banorte.com' },
  { brand: 'banamex', legitimateDomain: 'banamex.com' },
  { brand: 'santander', legitimateDomain: 'santander.com.mx' },
  { brand: 'sat', legitimateDomain: 'sat.gob.mx' },
  { brand: 'imss', legitimateDomain: 'imss.gob.mx' },
  { brand: 'bancomer', legitimateDomain: 'bancomer.com' }
];

// ============================================================
//  FUNCIÓN PRINCIPAL: analizar un email completo
// ============================================================
function analyzeEmail(emailData) {
  const { sender, subject, body } = emailData;
  
  const results = {
    isPhishing: false,
    isSuspicious: false,
    score: 0,        // 0 = limpio, 100 = claramente phishing
    reasons: [],
    senderAnalysis: null,
    urgencyDetected: false,
    keywordsFound: [],
    suspiciousLinks: []
  };

  // 1. Analizar remitente
  results.senderAnalysis = analyzeSender(sender);
  if (results.senderAnalysis.suspicious) {
    results.score += 40;
    results.reasons.push(results.senderAnalysis.reason);
  }

  // 2. Buscar patrones de urgencia en subject + body
  const fullText = `${subject} ${body}`;
  const urgencyFound = URGENCY_PATTERNS.filter(p => p.test(fullText));
  if (urgencyFound.length > 0) {
    results.urgencyDetected = true;
    results.score += Math.min(urgencyFound.length * 15, 35);
    results.reasons.push(`Lenguaje de urgencia detectado (${urgencyFound.length} patrón/es)`);
  }

  // 3. Contar keywords de phishing
  for (const [weight, keywords] of Object.entries(PHISHING_KEYWORDS)) {
    const found = keywords.filter(k => 
      fullText.toLowerCase().includes(k.toLowerCase())
    );
    if (found.length > 0) {
      results.keywordsFound.push(...found);
      const points = weight === 'high' ? 10 : weight === 'medium' ? 5 : 2;
      results.score += found.length * points;
    }
  }

  // 4. Extraer y analizar links del body
  results.suspiciousLinks = extractSuspiciousLinks(body);
  if (results.suspiciousLinks.length > 0) {
    results.score += results.suspiciousLinks.length * 20;
    results.reasons.push(`${results.suspiciousLinks.length} enlace(s) sospechoso(s) encontrado(s)`);
  }

  // 5. Detectar mismatch entre texto del link y URL real
  const mismatchedLinks = detectLinkMismatch(body);
  if (mismatchedLinks.length > 0) {
    results.score += 30;
    results.reasons.push('Links con texto engañoso (texto ≠ destino real)');
  }

  // Normalizar score
  results.score = Math.min(100, results.score);

  // Clasificación final
  results.isPhishing = results.score >= 70;
  results.isSuspicious = results.score >= 40 && results.score < 70;

  return results;
}

// ── Analizar el remitente del correo ──
function analyzeSender(sender) {
  if (!sender) return { suspicious: false };
  
  const emailMatch = sender.match(/@([^>]+)/);
  if (!emailMatch) return { suspicious: false };
  
  const senderDomain = emailMatch[1].toLowerCase().trim();

  // Verificar si el nombre de la marca aparece pero el dominio no coincide
  for (const { brand, legitimateDomain } of SUSPICIOUS_SENDER_PATTERNS) {
    const senderLower = sender.toLowerCase();
    
    if (senderLower.includes(brand) && !senderDomain.endsWith(legitimateDomain)) {
      return {
        suspicious: true,
        brand,
        expectedDomain: legitimateDomain,
        actualDomain: senderDomain,
        reason: `Se hace pasar por ${brand} pero el dominio es "${senderDomain}" (debería ser "${legitimateDomain}")`
      };
    }
  }

  // Verificar TLDs sospechosos
  const suspiciousTLDs = ['.tk', '.ml', '.ga', '.cf', '.xyz', '.top'];
  if (suspiciousTLDs.some(tld => senderDomain.endsWith(tld))) {
    return {
      suspicious: true,
      actualDomain: senderDomain,
      reason: `Dominio del remitente usa TLD sospechoso: "${senderDomain}"`
    };
  }

  return { suspicious: false, domain: senderDomain };
}

// ── Extraer links sospechosos del cuerpo del correo ──
function extractSuspiciousLinks(text) {
  if (!text) return [];
  
  const urlRegex = /https?:\/\/[^\s<>"]+/gi;
  const urls = text.match(urlRegex) || [];
  
  return urls.filter(url => {
    try {
      const u = new URL(url);
      return (
        u.protocol === 'http:' ||
        /\.(tk|ml|ga|cf|gq|xyz|top|click|link)$/.test(u.hostname) ||
        u.hostname.split('.').length > 4 ||
        /login|secure|verify|account|confirm/.test(u.hostname)
      );
    } catch { return false; }
  });
}

// ── Detectar cuando el texto visible del link no coincide con la URL ──
function detectLinkMismatch(htmlBody) {
  if (!htmlBody) return [];
  
  const linkRegex = /<a[^>]+href=["']([^"']+)["'][^>]*>(.*?)<\/a>/gi;
  const mismatches = [];
  let match;

  while ((match = linkRegex.exec(htmlBody)) !== null) {
    const href = match[1];
    const visibleText = match[2].replace(/<[^>]+>/g, '').trim();
    
    // Si el texto visible parece una URL diferente a la real
    if (visibleText.includes('.') && visibleText.includes('/')) {
      try {
        const visibleHost = new URL('https://' + visibleText.replace(/^https?:\/\//, '')).hostname;
        const actualHost = new URL(href).hostname;
        
        if (visibleHost !== actualHost && !actualHost.endsWith(visibleHost)) {
          mismatches.push({ visible: visibleText, actual: href });
        }
      } catch {}
    }
  }

  return mismatches;
}

// ── Analizar Gmail/Outlook en el DOM ──
function analyzeEmailsInDOM() {
  const results = [];
  
  // Gmail: buscar contenido de emails abiertos
  const gmailBody = document.querySelector('.a3s.aiL, [data-message-id]');
  if (gmailBody) {
    const emailText = gmailBody.innerText || '';
    const senderEl = document.querySelector('.gD'); // elemento del remitente en Gmail
    const sender = senderEl?.getAttribute('email') || '';
    
    const analysis = analyzeEmail({
      sender,
      subject: document.title,
      body: emailText
    });

    if (analysis.isPhishing || analysis.isSuspicious) {
      results.push({ source: 'gmail', analysis });
      showEmailWarning(gmailBody, analysis);
    }
  }

  return results;
}

// ── Mostrar advertencia dentro del email en el DOM ──
function showEmailWarning(container, analysis) {
  if (document.getElementById('sn-email-warning')) return;
  
  const isPhishing = analysis.isPhishing;
  const color = isPhishing ? '#ff3b6b' : '#ffd060';
  const textColor = isPhishing ? 'white' : '#1a1a1a';

  const warning = document.createElement('div');
  warning.id = 'sn-email-warning';
  warning.style.cssText = `
    background: ${color}; color: ${textColor};
    padding: 12px 16px; border-radius: 8px; margin-bottom: 12px;
    font-family: sans-serif; font-size: 13px;
    border-left: 4px solid ${isPhishing ? '#cc0033' : '#cc9900'};
  `;

  warning.innerHTML = `
    <strong>${isPhishing ? '🚨 PHISHING DETECTADO' : '⚠️ Email Sospechoso'}</strong>
    <div style="margin-top:6px; font-size:12px">
      Score de riesgo: <strong>${analysis.score}/100</strong><br>
      ${analysis.reasons.map(r => `• ${r}`).join('<br>')}
    </div>
  `;

  container.parentNode?.insertBefore(warning, container);
}

// Exportar para uso en content.js
if (typeof window !== 'undefined') {
  window.ShieldNetPhishing = {
    analyzeEmail,
    analyzeSender,
    analyzeEmailsInDOM,
    extractSuspiciousLinks
  };
}
