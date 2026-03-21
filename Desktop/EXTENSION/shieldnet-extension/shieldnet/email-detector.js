// ============================================================
//  ShieldNet — email-detector.js v1.2
//  Detecta phishing en Outlook y Gmail
//  Mejorado: analiza remitente, imágenes con links, HTML oculto
// ============================================================

(function () {
  'use strict';
  if (window.__sn_email_loaded) return;
  window.__sn_email_loaded = true;

  const isGmail   = location.hostname.includes('mail.google.com');
  const isOutlook = location.hostname.includes('outlook.live.com') ||
                    location.hostname.includes('outlook.office.com');

  if (!isGmail && !isOutlook) return;

  // ── Patrones de urgencia en texto ──
  const URGENCY_PATTERNS = [
    /cuenta.{0,20}(cancelada|bloqueada|suspendida|eliminada)/i,
    /almacenamiento.{0,20}(lleno|limite|critico|agotado)/i,
    /verifica.{0,15}(ahora|inmediatamente|hoy|urgente)/i,
    /contrase[ñn]a.{0,20}(expir|venc|cambi)/i,
    /actua(liza|lice).{0,20}(datos|informaci|pago|tarjeta)/i,
    /suscripci[oó]n.{0,20}(vencid|expir|cancelad)/i,
    /archivos.{0,20}(elimin|borra|perder[aá]s)/i,
    /oferta.{0,15}(tiempo limitado|expira|[0-9]+%)/i,
    /aviso final/i, /alerta cr[ií]tica/i,
    /act[uú]a (ahora|inmediatamente)/i,
    /renueva.{0,20}(hoy|ahora|inmediatamente)/i,
    /your account.{0,20}(suspend|terminat|cancel)/i,
    /verify.{0,15}(now|immediately|today)/i,
    /storage.{0,20}(full|limit|critical)/i,
    /action required/i, /immediate action/i,
    // Multas, gobierno, tráfico
    /multa.{0,30}(pendiente|pago|venc|plazo)/i,
    /sanción.{0,30}(pendiente|pago|regulariz)/i,
    /expediente.{0,30}(pendiente|admin|regulariz)/i,
    /acción requerida.{0,20}(horas|días|plazo)/i,
    /pago.{0,20}(próximas|horas|plazo|evitar)/i,
    /importe.{0,20}(increment|adicional|recarg)/i,
    /regulariz.{0,20}(pago|expediente|situaci)/i,
    /infracción.{0,20}(puntos|permiso|conducir)/i,
    /puntos.{0,20}(permiso|conducir|detracción)/i,
    /plazo.{0,20}(24 horas|48 horas|venc)/i,
    /si no.{0,30}(pago|regulariz|cargo adicional)/i,
    /notificación.{0,20}(administrativa|oficial)/i,
    /dirección general.{0,20}(tráfico|hacienda|seguridad)/i
  ];

  // ── Dominios oficiales de gobierno (nunca vienen de dominios comerciales) ──
  const GOV_NAMES = [
    'dirección general de tráfico', 'dgt', 'hacienda', 'agencia tributaria',
    'seguridad social', 'ministerio', 'gobierno', 'sat', 'imss', 'infonavit',
    'servicio de administración tributaria', 'secretaría'
  ];

  // ── Marcas legítimas y sus dominios reales ──
  const LEGIT_SENDERS = {
    'microsoft': ['microsoft.com', 'outlook.com', 'live.com', 'hotmail.com'],
    'google': ['google.com', 'gmail.com', 'googlemail.com'],
    'apple': ['apple.com', 'icloud.com'],
    'amazon': ['amazon.com', 'amazon.com.mx'],
    'dropbox': ['dropbox.com'],
    'cloud secure': ['microsoft.com', 'google.com', 'apple.com'],
    'cloud': ['microsoft.com', 'google.com', 'apple.com', 'dropbox.com']
  };

  // ── Analizar el remitente ──
  function analyzeSender(senderEmail, senderName) {
    const results = [];
    const domain = senderEmail?.split('@')[1]?.toLowerCase() || '';

    // 1. Dominio con números random = generado automáticamente
    // ej: loretta437096chung.onmicrosoft.com
    if (/[a-z]+\d{4,}[a-z]+/.test(domain)) {
      results.push({
        score: 50,
        reason: `🚨 Remitente generado automáticamente: "${senderEmail}" (patrón nombre+números)`
      });
    }

    // 2. Subdominio raro en onmicrosoft.com (tenants falsos)
    if (domain.endsWith('.onmicrosoft.com')) {
      const tenant = domain.replace('.onmicrosoft.com', '');
      if (/\d{4,}/.test(tenant) || tenant.length > 20) {
        results.push({
          score: 45,
          reason: `🚨 Tenant de Microsoft sospechoso: "${domain}" (no es una empresa real)`
        });
      }
    }

    // 3. Nombre del remitente vs dominio real
    const senderLower = (senderName + ' ' + senderEmail).toLowerCase();
    for (const [brand, legitDomains] of Object.entries(LEGIT_SENDERS)) {
      const mentionsBrand = senderLower.includes(brand);
      const isLegit = legitDomains.some(d => domain.endsWith(d));
      if (mentionsBrand && !isLegit && domain) {
        results.push({
          score: 45,
          reason: `🚨 Se hace pasar por "${brand}" pero viene de "@${domain}"`
        });
      }
    }

    // 4. TLD sospechoso en el remitente
    const badTLDs = ['.tk', '.ml', '.ga', '.cf', '.autos', '.xyz', '.sbs'];
    if (badTLDs.some(t => domain.endsWith(t))) {
      results.push({
        score: 40,
        reason: `⚠️ Dominio del remitente sospechoso: "${domain}"`
      });
    }

    return results;
  }

  // ── Analizar links (incluyendo los dentro de imágenes) ──
  function analyzeLinks(container) {
    const results = [];

    // Links normales
    const links = container.querySelectorAll('a[href]');
    let suspiciousCount = 0;

    links.forEach(link => {
      const href = link.href || '';
      try {
        const host = new URL(href).hostname;
        if (
          /\.(tk|ml|ga|cf|autos|sbs|cyou|cfd|xyz|top)$/.test(host) ||
          /[a-z]\d{4,}[a-z]/.test(host) ||   // números random en dominio
          host.split('.').length > 4 ||          // demasiados subdominios
          /\d{1,3}\.\d{1,3}\.\d{1,3}/.test(host) // IP address directo
        ) {
          suspiciousCount++;
          link.style.outline = '2px solid #ff3b6b';
          link.title = '⚠️ ShieldNet: Link sospechoso';
        }
      } catch {}
    });

    if (suspiciousCount > 0) {
      results.push({
        score: suspiciousCount * 25,
        reason: `🔗 ${suspiciousCount} enlace(s) sospechoso(s) detectado(s)`
      });
    }

    // Imágenes que son links (técnica común de phishing)
    const imgLinks = container.querySelectorAll('a[href] img, a[href] > *');
    if (imgLinks.length > 0) {
      // Si hay imágenes que funcionan como botones/links, verificar sus URLs
      let suspiciousImgLinks = 0;
      imgLinks.forEach(img => {
        const parentLink = img.closest('a');
        if (!parentLink) return;
        const href = parentLink.href || '';
        try {
          const host = new URL(href).hostname;
          if (
            /\.(autos|sbs|cyou|cfd|tk|ml|ga|cf)$/.test(host) ||
            /[a-z]\d{4,}[a-z]/.test(host)
          ) {
            suspiciousImgLinks++;
          }
        } catch {}
      });

      if (suspiciousImgLinks > 0) {
        results.push({
          score: 35,
          reason: `🖼️ Imagen usada como link sospechoso (técnica común de phishing)`
        });
      }
    }

    return results;
  }

  // ── Función principal de análisis ──
  function analyzeEmail(container, senderEmail, senderName) {
    const text = container.innerText || '';
    let totalScore = 0;
    const reasons = [];

    // 0. Detectar si finge ser gobierno desde dominio comercial
    const senderLower = (senderEmail || '').toLowerCase();
    const nameLower = (senderName || '').toLowerCase();
    const bodyLower = (text || '').toLowerCase();
    const isGovImpersonation = GOV_NAMES.some(g => nameLower.includes(g) || bodyLower.includes(g));
    const isGovDomain = senderLower.includes('.gob.') || senderLower.includes('.gov.') ||
                        senderLower.endsWith('.gob') || senderLower.endsWith('.gov');
    if (isGovImpersonation && !isGovDomain) {
      totalScore += 70;
      reasons.push('🏛️ Suplanta a institución de gobierno desde dominio no oficial');
    }

    // 1. Analizar remitente
    const senderIssues = analyzeSender(senderEmail, senderName);
    senderIssues.forEach(({ score, reason }) => {
      totalScore += score;
      reasons.push(reason);
    });

    // 2. Patrones de urgencia en texto visible
    if (text.length > 20) {
      const found = URGENCY_PATTERNS.filter(p => p.test(text));
      if (found.length > 0) {
        totalScore += found.length * 15;
        reasons.push(`⚠️ Lenguaje de urgencia detectado (${found.length} señal/es)`);
      }
    }

    // 3. Analizar links e imágenes
    const linkIssues = analyzeLinks(container);
    linkIssues.forEach(({ score, reason }) => {
      totalScore += score;
      reasons.push(reason);
    });

    // 4. Palabras de pago
    const paymentWords = ['tarjeta', 'crédito', 'débito', 'cvv', 'nip', 'pin',
                          'credit card', 'payment', 'billing',
                          'consultar expediente', 'regularizar', 'importe pendiente'];
    // Moneda extranjera en México o México en Europa = sospechoso
    const foreignCurrency = /€\s*\d|\d\s*€|euros/.test(text) && 
                             (location.hostname.includes('.mx') || /mexico|méxico/i.test(text));
    if (foreignCurrency) {
      totalScore += 25;
      reasons.push('💰 Usa moneda extranjera (€ euros) sospechosamente');
    }
    const paymentFound = paymentWords.filter(w => text.toLowerCase().includes(w));
    if (paymentFound.length >= 2) {
      totalScore += 30;
      reasons.push(`💳 Solicita información de pago`);
    }

    return {
      isPhishing: totalScore >= 60,
      isSuspicious: totalScore >= 30 && totalScore < 60,
      score: Math.min(100, totalScore),
      reasons
    };
  }

  // ── Mostrar banner ──
  function showBanner(container, analysis) {
    if (container.querySelector('.sn-email-banner')) return;

    const isPhishing = analysis.isPhishing;
    const bg = isPhishing ? '#ff3b6b' : '#d29922';
    const textColor = isPhishing ? 'white' : '#1a1a1a';

    const banner = document.createElement('div');
    banner.className = 'sn-email-banner';
    banner.style.cssText = `
      background:${bg}; color:${textColor};
      padding:12px 16px; border-radius:8px; margin:8px 0 12px;
      font-family:'Segoe UI',sans-serif; font-size:13px;
      border-left:5px solid ${isPhishing ? '#cc0033' : '#b8860b'};
      position:relative; z-index:9999;
    `;
    banner.innerHTML = `
      <div style="font-weight:700;font-size:14px;margin-bottom:6px">
        ${isPhishing ? '🚨 ShieldNet: PHISHING DETECTADO' : '⚠️ ShieldNet: Correo Sospechoso'}
        <span style="font-size:11px;margin-left:8px;opacity:0.8">Riesgo: ${analysis.score}/100</span>
      </div>
      <div style="font-size:12px;line-height:1.8">
        ${analysis.reasons.map(r => `• ${r}`).join('<br>')}
      </div>
      ${isPhishing ? `<div style="margin-top:8px;font-size:12px;font-weight:700;background:rgba(0,0,0,0.15);padding:6px 10px;border-radius:6px">
        ⛔ NO hagas clic en ningún enlace. NO ingreses datos personales ni de pago.
      </div>` : ''}
    `;

    container.insertBefore(banner, container.firstChild);
  }

  // ── Obtener remitente en Outlook (busca en todo el doc incluyendo iframes) ──
  function getOutlookSender() {
    // Buscar en todos los spans/divs con título que tengan @
    const allEls = document.querySelectorAll('span[title], div[title], a[title]');
    for (const el of allEls) {
      const t = el.getAttribute('title') || '';
      if (t.includes('@') && t.includes('.') && t.length < 200) return t.trim();
    }
    // Buscar texto visible con formato de email
    const allSpans = document.querySelectorAll('span, a');
    for (const el of allSpans) {
      const t = (el.innerText || '').trim();
      if (/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(t) && t.length < 100) return t;
    }
    return '';
  }

  function getOutlookSenderName() {
    const selectors = [
      '[class*="SenderName"]', '[class*="sender"] strong',
      '[class*="DisplayName"]', '[class*="senderName"]',
      '[aria-label*="De:"]', 'h1[class*="sender"]'
    ];
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el?.innerText?.trim()) return el.innerText.trim();
    }
    return '';
  }

  // ── Escanear Outlook — incluyendo iframes ──
  function scanOutlook() {
    // Obtener remitente del documento principal
    const senderEmail = getOutlookSender();
    const senderName  = getOutlookSenderName();

    // Intentar escanear el documento principal primero
    const mainSelectors = [
      '.allowTextSelection', '[class*="ReadingPaneContent"]',
      '[role="document"]', '[class*="messageBody"]',
      '[class*="ItemBody"]', '[class*="readingPane"]',
      'div[class*="body"]', '[aria-label*="Cuerpo"]'
    ];
    for (const sel of mainSelectors) {
      const body = document.querySelector(sel);
      if (body && !body.dataset.snScanned && body.innerText?.length > 30) {
        body.dataset.snScanned = '1';
        const analysis = analyzeEmail(body, senderEmail, senderName);
        if (analysis.isPhishing || analysis.isSuspicious) {
          showBanner(body.parentElement || body, analysis);
          return;
        }
      }
    }

    // Si no encontró en el doc principal, buscar en iframes
    const iframes = document.querySelectorAll('iframe');
    for (const iframe of iframes) {
      try {
        const iDoc = iframe.contentDocument || iframe.contentWindow?.document;
        if (!iDoc || iframe.dataset.snScanned) continue;

        const iBody = iDoc.body;
        if (!iBody || iBody.innerText?.length < 30) continue;

        iframe.dataset.snScanned = '1';

        // Usar el remitente del doc principal para analizar el cuerpo del iframe
        const analysis = analyzeEmail(iBody, senderEmail, senderName);
        if (analysis.isPhishing || analysis.isSuspicious) {
          // Insertar banner encima del iframe
          const wrapper = iframe.parentElement;
          if (wrapper && !wrapper.querySelector('.sn-email-banner')) {
            showBanner(wrapper, analysis);
          }
          return;
        }
      } catch(e) { /* iframe de otro origen, ignorar */ }
    }
  }

  // ── Escanear Gmail ──
  function scanGmail() {
    const body = document.querySelector('.a3s.aiL, [data-message-id] .ii.gt');
    if (!body || body.dataset.snScanned) return;
    body.dataset.snScanned = '1';

    const senderEl = document.querySelector('.gD');
    const senderEmail = senderEl?.getAttribute('email') || '';
    const senderName  = senderEl?.innerText || '';

    const analysis = analyzeEmail(body, senderEmail, senderName);
    if (analysis.isPhishing || analysis.isSuspicious) {
      showBanner(body, analysis);
    }
  }

  // ── Observer ──
  let scanTimeout;
  const observer = new MutationObserver(() => {
    clearTimeout(scanTimeout);
    scanTimeout = setTimeout(() => {
      if (!shouldScan()) return;
      // Limpiar flags para re-escanear correos nuevos
      document.querySelectorAll('[data-sn-scanned]').forEach(el => {
        delete el.dataset.snScanned;
      });
      // Limpiar banners viejos antes de re-escanear
      document.querySelectorAll('.sn-email-banner').forEach(el => el.remove());
      if (isOutlook) scanOutlook();
      if (isGmail)   scanGmail();
    }, 900);
  });

  function shouldScan() {
    if (isOutlook) {
      // Solo escanear cuando hay un correo abierto (URL tiene ID largo o ruta junkemail/id/)
      const path = location.href;
      return path.includes('/mail/0/') && (
        path.includes('/id/') ||
        path.includes('junkemail') ||
        path.includes('inbox') && path.length > 60
      );
    }
    if (isGmail) {
      // Gmail: solo cuando hay #inbox/ o #all/ con ID
      return /#(inbox|sent|spam|all)\/[a-zA-Z0-9]+/.test(location.hash);
    }
    return false;
  }

  const start = () => {
    if (!document.body) return;
    observer.observe(document.body, { childList: true, subtree: true });
    setTimeout(() => {
      if (shouldScan()) {
        if (isOutlook) scanOutlook();
        if (isGmail)   scanGmail();
      }
    }, 1500);
  };

  if (document.body) start();
  else document.addEventListener('DOMContentLoaded', start);

})();
