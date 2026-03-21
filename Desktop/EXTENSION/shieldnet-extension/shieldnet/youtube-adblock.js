// ============================================================
//  ShieldNet — youtube-adblock.js
//  Bloquea anuncios en YouTube sin romper la reproducción
// ============================================================

(function () {
  'use strict';
  if (!location.hostname.includes('youtube.com')) return;
  if (window.__sn_yt_loaded) return;
  window.__sn_yt_loaded = true;

  // Selectores de elementos de anuncio en el DOM
  const AD_SELECTORS = [
    '.ytp-ad-overlay-container',
    '.ytp-ad-text-overlay',
    '#masthead-ad',
    '#player-ads',
    'ytd-ad-slot-renderer',
    'ytd-in-feed-ad-layout-renderer',
    'ytd-banner-promo-renderer',
    'ytd-statement-banner-renderer',
    'ytd-promoted-sparkles-web-renderer',
    'ytd-promoted-video-renderer',
    'ytd-carousel-ad-renderer',
    'ytd-search-pyv-renderer',
    '.ytd-display-ad-renderer',
    'ytd-display-ad-renderer',
    '.ytp-featured-product',
    '.ytp-ad-action-interstitial',
    '.ytp-ad-timed-pie-countdown-container'
  ];

  // ── Eliminar banners y overlays del DOM ──
  function removeAdElements() {
    AD_SELECTORS.forEach(selector => {
      document.querySelectorAll(selector).forEach(el => el.remove());
    });
  }

  // ── Saltar anuncios de video ──
  // SOLO hace clic en "Saltar" — NO adelanta el video
  function skipVideoAd() {
    // Intentar clic en botón de saltar
    const skipBtn = document.querySelector(
      '.ytp-ad-skip-button, .ytp-ad-skip-button-modern, .ytp-skip-ad-button'
    );
    if (skipBtn) {
      skipBtn.click();
      return;
    }

    // Si hay anuncio reproduciéndose y NO hay botón de saltar:
    // Mutear el audio del anuncio para que no moleste
    const video = document.querySelector('video');
    const adOverlay = document.querySelector('.ytp-ad-player-overlay-instream-info');
    if (video && adOverlay) {
      video.muted = true;
    } else if (video) {
      // Sin anuncio: asegurarse de que el audio esté activo
      video.muted = false;
    }
  }

  // ── Interceptar fetch para bloquear tracking de ads ──
  const originalFetch = window.fetch;
  window.fetch = function (...args) {
    const url = typeof args[0] === 'string' ? args[0] : (args[0]?.url || '');
    if (
      url.includes('/pagead/') ||
      url.includes('/pcs/activeview') ||
      url.includes('doubleclick.net') ||
      url.includes('/api/stats/ads')
    ) {
      return Promise.resolve(new Response('{}', {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      }));
    }
    return originalFetch.apply(this, args);
  };

  // ── Observar cambios en el DOM ──
  let lastUrl = location.href;
  const observer = new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      setTimeout(removeAdElements, 800);
    }
    removeAdElements();
    skipVideoAd();
  });

  // Esperar al body antes de observar
  const startObserver = () => {
    if (!document.body) return;
    observer.observe(document.body, { childList: true, subtree: true });
  };

  if (document.body) startObserver();
  else document.addEventListener('DOMContentLoaded', startObserver);

  // Revisar cada 500ms (más lento = menos lag)
  setInterval(() => {
    skipVideoAd();
    removeAdElements();
  }, 500);

  removeAdElements();
  console.log('[ShieldNet] YouTube AdBlock activo ✓');
})();
