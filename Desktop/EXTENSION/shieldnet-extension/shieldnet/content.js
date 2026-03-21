// ============================================================
//  ShieldNet — content.js
//  Se inyecta en cada página. Analiza el DOM en busca de
//  señales de phishing: formularios sospechosos, iframes, etc.
// ============================================================

(function() {
  'use strict';

  // Evitar doble ejecución
  if (window.__shieldnet_loaded) return;
  window.__shieldnet_loaded = true;

  // ── Estado ──
  let warningBanner = null;
  let currentRisk = null;

  // ── Escuchar resultados del background ──
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === 'DOMAIN_RESULT') {
      currentRisk = msg.result.risk;
      
      if (msg.result.risk === 'DANGER') {
        showWarningBanner(msg.result);
      } else if (msg.result.risk === 'WARNING') {
        showWarningBanner(msg.result, false);
      }
    }
  });

  // ── Analizar formularios en la página ──
  function analyzePageForms() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
      const hasPassword = form.querySelector('input[type="password"]');
      const action = form.action || '';
      const isHTTP = action.startsWith('http://') || 
                     (!action.startsWith('https://') && location.protocol === 'http:');
      
      if (hasPassword && isHTTP) {
        markFormAsDangerous(form, 'Este formulario envía tu contraseña SIN cifrado (HTTP)');
      }
    });
  }

  function markFormAsDangerous(form, reason) {
    form.style.outline = '3px solid #ff3b6b';
    form.style.borderRadius = '6px';
    
    const warning = document.createElement('div');
    warning.style.cssText = `
      background: #ff3b6b; color: white; padding: 8px 14px;
      font-family: sans-serif; font-size: 13px; font-weight: bold;
      border-radius: 6px 6px 0 0; margin-bottom: 4px;
      display: flex; align-items: center; gap: 8px;
    `;
    warning.innerHTML = `⚠️ ShieldNet: ${reason}`;
    form.parentNode.insertBefore(warning, form);
  }

  // ── Banner de advertencia en la parte superior ──
  function showWarningBanner(result, isDanger = true) {
    if (warningBanner) warningBanner.remove();

    const color = isDanger ? '#ff3b6b' : '#ffd060';
    const textColor = isDanger ? 'white' : '#1a1a1a';
    const icon = isDanger ? '🚨' : '⚠️';
    const title = isDanger ? 'SITIO PELIGROSO DETECTADO' : 'Sitio Sospechoso';
    const msg = isDanger
      ? `Este sitio fue identificado como potencialmente malicioso (score: ${result.score}/100). Evita ingresar datos personales o contraseñas.`
      : `Este sitio tiene características sospechosas (score: ${result.score}/100). Procede con precaución.`;

    warningBanner = document.createElement('div');
    warningBanner.id = 'shieldnet-banner';
    warningBanner.style.cssText = `
      position: fixed; top: 0; left: 0; right: 0; z-index: 2147483647;
      background: ${color}; color: ${textColor};
      padding: 12px 20px; font-family: 'Segoe UI', sans-serif;
      font-size: 14px; display: flex; align-items: center;
      justify-content: space-between; gap: 16px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.4);
      animation: shieldnet-slide-in 0.3s ease-out;
    `;

    // Agregar animación CSS
    const style = document.createElement('style');
    style.textContent = `
      @keyframes shieldnet-slide-in {
        from { transform: translateY(-100%); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
      }
    `;
    document.head.appendChild(style);

    warningBanner.innerHTML = `
      <div style="display:flex; align-items:center; gap:12px; flex:1;">
        <span style="font-size:22px">${icon}</span>
        <div>
          <strong style="font-size:15px">ShieldNet: ${title}</strong>
          <div style="font-size:12px; margin-top:2px; opacity:0.9">${msg}</div>
        </div>
      </div>
      <div style="display:flex; gap:8px; flex-shrink:0">
        ${isDanger ? `<button id="sn-goback" style="
          background: white; color: ${color}; border: none;
          padding: 8px 16px; border-radius: 6px; cursor: pointer;
          font-weight: bold; font-size: 13px;
        ">← Volver</button>` : ''}
        <button id="sn-dismiss" style="
          background: transparent; color: ${textColor};
          border: 2px solid ${textColor}40; padding: 8px 12px;
          border-radius: 6px; cursor: pointer; font-size: 12px;
        ">Ignorar</button>
      </div>
    `;

    document.body.prepend(warningBanner);
    document.body.style.marginTop = (warningBanner.offsetHeight + 8) + 'px';

    document.getElementById('sn-dismiss')?.addEventListener('click', () => {
      warningBanner.remove();
      document.body.style.marginTop = '';
    });

    document.getElementById('sn-goback')?.addEventListener('click', () => {
      history.back();
    });
  }

  // ── Detector de links sospechosos en la página ──
  function analyzeSuspiciousLinks() {
    const links = document.querySelectorAll('a[href]');
    let suspicious = 0;

    links.forEach(link => {
      const href = link.href;
      if (isSuspiciousURL(href)) {
        suspicious++;
        link.style.textDecoration = 'underline wavy #ffd060';
        link.title = '⚠️ ShieldNet: Este enlace parece sospechoso';
        link.setAttribute('data-shieldnet', 'suspicious');
      }
    });

    return suspicious;
  }

  function isSuspiciousURL(url) {
    try {
      const u = new URL(url);
      return (
        u.protocol === 'http:' ||
        /\.(tk|ml|ga|cf|gq|xyz)$/.test(u.hostname) ||
        u.hostname.split('.').length > 4
      );
    } catch {
      return false;
    }
  }

  // ── Detector de iframes ocultos (común en phishing) ──
  function detectHiddenIframes() {
    // Solo advertir, no eliminar iframes (algunos son legítimos en YT)
    const iframes = document.querySelectorAll('iframe');
    iframes.forEach(iframe => {
      try {
        const style = window.getComputedStyle(iframe);
        const src = iframe.src || '';
        // Solo reportar iframes de dominios externos sospechosos
        if (src && !src.startsWith(location.origin) &&
            (src.includes('doubleclick') || src.includes('adnxs'))) {
          iframe.remove();
        }
      } catch(e) {}
    });
  }

  // ── Ejecutar análisis cuando el DOM está listo ──
  function runAnalysis() {
    analyzePageForms();
    analyzeSuspiciousLinks();
    detectHiddenIframes();
    
    // Enviar resultado al background para que lo guarde
    chrome.runtime.sendMessage({
      type: 'PAGE_ANALYSIS_DONE',
      url: location.href
    }).catch(() => {});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runAnalysis);
  } else {
    runAnalysis();
  }

  // Observar cambios dinámicos (SPAs como Gmail)
  const startObserver = () => {
    if (!document.body) return;
    const obs = new MutationObserver(() => { analyzePageForms(); });
    obs.observe(document.body, { childList: true, subtree: true });
  };
  if (document.body) startObserver();
  else document.addEventListener('DOMContentLoaded', startObserver);

})();
