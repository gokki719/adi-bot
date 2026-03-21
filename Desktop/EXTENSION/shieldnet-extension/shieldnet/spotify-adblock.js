// ShieldNet — spotify-adblock.js v12
// Solo mutear + ocultar banners. Sin tocar currentTime.

(function () {
  'use strict';
  if (!location.hostname.includes('spotify.com')) return;
  if (window.__sn_spotify) return;
  window.__sn_spotify = true;

  let adActive = false;
  let userVol = 1;

  function isAd() {
    if (/Publicidad|Spotify.*Publicidad/i.test(document.title)) return true;
    if (!document.body) return false;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = walker.nextNode())) {
      if (/^Anuncio\s*[·•]\s*\d/i.test(n.textContent?.trim())) return true;
    }
    return false;
  }

  function tick() {
    const audio = document.querySelector('audio');
    if (!audio) return;

    if (isAd()) {
      if (!adActive) {
        userVol = (!audio.muted && audio.volume > 0) ? audio.volume : 1;
        adActive = true;
      }
      // Solo mutear, nunca pausar ni tocar currentTime
      audio.muted = true;
      audio.volume = 0;

    } else if (adActive) {
      adActive = false;
      audio.muted = false;
      audio.volume = userVol;
    }
  }

  function hideBanners() {
    if (!document.body) return;
    document.querySelectorAll('*').forEach(el => {
      if (el.dataset.snDone) return;
      const t = el.innerText || '';
      if (
        el.offsetHeight > 50 && el.offsetHeight < 500 &&
        /pasate a premium|volver a premium|prueba premium|buena forma|dale una vuelta|vuelve a la música|sin anuncios|que el ritmo|conoce la playlist/i.test(t) &&
        el.querySelector('button, a[href*="premium"], a[href*="saber"]')
      ) {
        el.style.setProperty('display', 'none', 'important');
        el.dataset.snDone = '1';
      }
    });
  }

  setInterval(tick, 300);
  setInterval(hideBanners, 800);
  console.log('[ShieldNet] Spotify v12 - mute only ✓');
})();
