// ============================================================
//  ShieldNet — adblock-dom.js  (DOM layer)
//  Elimina ads del DOM en cualquier página
//  Incluye: genéricos, caliente.mx, push notifications, pop-ups
// ============================================================

(function () {
  'use strict';
  if (window.__sn_adblock_dom) return;
  // No correr en Outlook ni Gmail — tienen su propio detector
  if (/outlook\.(live|office)|mail\.google\.com/.test(location.hostname)) return;
  window.__sn_adblock_dom = true;

  // ── Selectores universales ──
  const AD_SELECTORS = [
    'ins.adsbygoogle', '[data-ad-slot]', '[data-ad-client]', '[data-ad-unit]',
    '[id*="google_ads"]', '[id*="div-gpt-ad"]', '[class*="adsbygoogle"]',
    '[class*="ad-slot"]', '[class*="ad-unit"]', '[class*="ad-banner"]',
    '[class*="ad-container"]', '[class*="ad-wrapper"]', '[class*="advertisement"]',
    '[class*="AdSlot"]', '[class*="AdUnit"]', '[class*="AdBanner"]',
    '[aria-label="Ads"]', '[aria-label="Advertisement"]',
    // iframes de redes de ads
    'iframe[src*="doubleclick.net"]', 'iframe[src*="googlesyndication"]',
    'iframe[src*="adnxs.com"]', 'iframe[src*="advertising.com"]',
    'iframe[src*="adserver"]', 'iframe[src*="adform"]',
    'iframe[src*="taboola"]', 'iframe[src*="outbrain"]',
    'iframe[src*="moatads"]', 'iframe[src*="amazon-adsystem"]',
    // Elementos nativos de ads
    'ytd-ad-slot-renderer', '#masthead-ad', '#player-ads',
    '[data-testid="ad-slot"]', '[data-testid="sponsored-card"]',
    // Caliente.mx específico
    '[class*="betting-banner"]', '[class*="casino-promo"]',
    '[id*="caliente"]', '[class*="caliente-ad"]',
  ];

  // ── Bloquear pop-ups ──
  const _open = window.open;
  window.open = function(url, ...args) {
    if (!url) return null;
    const u = String(url).toLowerCase();
    if (/ad|click|track|redir|pop|banner|promo/.test(u)) return null;
    return _open.call(this, url, ...args);
  };

  // ── Bloquear push notifications ──
  if ('Notification' in window) {
    const _req = Notification.requestPermission;
    Notification.requestPermission = () => Promise.resolve('denied');
  }

  // ── Eliminar elementos ──
  function removeAds() {
    AD_SELECTORS.forEach(sel => {
      try {
        document.querySelectorAll(sel).forEach(el => {
          if (isSafe(el)) el.remove();
        });
      } catch(e) {}
    });

    // Buscar iframes de dominios de ads conocidos
    document.querySelectorAll('iframe').forEach(iframe => {
      const src = iframe.src || iframe.getAttribute('src') || '';
      if (/doubleclick|googlesyndication|adnxs|advertising|adform|moatads|amazon-adsystem|taboola|outbrain|caliente.*ad/i.test(src)) {
        if (isSafe(iframe)) iframe.remove();
      }
    });
  }

  // ── Eliminar overlays/intersticiales ──
  function removeInterstitials() {
    document.querySelectorAll('div, section').forEach(el => {
      try {
        const s = window.getComputedStyle(el);
        if (s.position !== 'fixed' && s.position !== 'absolute') return;
        if (parseInt(s.zIndex) < 1000) return;
        const w = parseInt(s.width), h = parseInt(s.height);
        if (w < window.innerWidth * 0.5 || h < window.innerHeight * 0.5) return;
        const text = (el.innerText || '').toLowerCase();
        if (/anuncio|publicidad|advertisement|sponsored|patrocinado|ad by/i.test(text) ||
            el.querySelector('[id*="ad"],[class*="ad"],[data-ad-slot],iframe[src*="ad"]')) {
          if (isSafe(el)) el.remove();
        }
      } catch(e) {}
    });
  }

  function isSafe(el) {
    if (!el?.parentNode) return false;
    const tag = el.tagName?.toLowerCase();
    if (['body','html','head','main','header','footer','nav','article','aside'].includes(tag)) return false;
    return true;
  }

  // ── Bloqueo específico caliente.mx ──
  function blockCaliente() {
    if (!location.hostname.includes('caliente')) return;
    const sels = [
      '[class*="banner"]', '[class*="Banner"]', '[class*="promo"]',
      '[class*="Promo"]', '[class*="popup"]', '[class*="Popup"]',
      '[class*="modal"]:not([role="dialog"])', '[id*="banner"]',
      '[id*="promo"]', '[id*="popup"]', '[class*="sponsor"]',
      '[class*="publicidad"]', '[class*="oferta"]',
    ];
    sels.forEach(sel => {
      document.querySelectorAll(sel).forEach(el => {
        if (el.offsetHeight > 0 && el.offsetHeight < 500 && isSafe(el)) {
          el.style.setProperty('display','none','important');
        }
      });
    });
  }

  // ── Arrancar ──
  function run() {
    removeAds();
    removeInterstitials();
    blockCaliente();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }

  // Observer
  let t;
  new MutationObserver(() => {
    clearTimeout(t);
    t = setTimeout(run, 200);
  }).observe(document.documentElement, { childList: true, subtree: true });

})();
