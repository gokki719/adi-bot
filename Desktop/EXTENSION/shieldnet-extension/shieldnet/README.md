# 🛡️ ShieldNet — Extensión de Seguridad Web

## ¿Qué hace?
- ✅ Detecta dominios falsos y typosquatting (banc0mer.com ≠ bancomer.com)
- ✅ Detecta sitios HTTP sin cifrado
- ✅ Revisa listas negras offline y Google Safe Browsing
- ✅ Detecta correos de phishing (patrones de urgencia, remitentes falsos)
- ✅ Bloquea anuncios (20+ redes de publicidad)
- ✅ Bloquea trackers (Google Analytics, Facebook Pixel, Hotjar, etc.)
- ✅ Score de confianza 0-100 por dominio
- ✅ Historial de sitios visitados
- ✅ Compatible con Chrome, Edge, Brave y Opera

---

## 📦 Instalación en Chrome/Edge/Brave/Opera

1. Abre tu navegador y ve a:
   - Chrome: `chrome://extensions`
   - Edge: `edge://extensions`
   - Brave: `brave://extensions`
   - Opera: `opera://extensions`

2. Activa **"Modo desarrollador"** (switch arriba a la derecha)

3. Haz clic en **"Cargar extensión sin empaquetar"** (o "Load unpacked")

4. Selecciona la carpeta `shieldnet-extension/`

5. ¡Listo! El ícono 🛡️ aparece en la barra del navegador

---

## 🔑 APIs (Opcionales pero recomendadas)

### Google Safe Browsing (GRATIS)
1. Ve a https://console.cloud.google.com/
2. Crea un proyecto → Activa "Safe Browsing API"
3. Crea una API Key
4. En `background.js` línea 8, reemplaza `'TU_API_KEY_AQUI'` con tu key

### WhoisXML API (GRATIS — 500 consultas/mes)
1. Regístrate en https://www.whoisxmlapi.com/
2. Copia tu API Key
3. En `background.js` función `checkDomainAge()`, reemplaza `'TU_WHOIS_API_KEY'`

> Sin las API keys la extensión sigue funcionando, solo usa las listas offline.

---

## 📁 Estructura del proyecto

```
shieldnet-extension/
├── manifest.json        ← Config principal (MV3)
├── background.js        ← Motor de análisis (Service Worker)
├── content.js           ← Se inyecta en cada página
├── domainScorer.js      ← Helpers de scoring
├── phishing.js          ← Detector de emails falsos
├── popup.html           ← UI de la extensión
├── popup.js             ← Lógica de la UI
├── rules/
│   ├── adblock_rules.json   ← Reglas de bloqueo de ads
│   └── tracker_rules.json   ← Reglas de bloqueo de trackers
└── icons/
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

---

## 🔧 Cómo agregar más dominios a la lista negra

En `background.js`, busca `const BLACKLIST` y agrega dominios:
```javascript
const BLACKLIST = new Set([
  "dominio-falso.xyz",
  "otro-sitio-chafa.tk",
  // ... agregar más aquí
]);
```

---

## 🎯 Para la presentación del proyecto

### Tecnologías usadas
- **Manifest V3** — estándar actual de extensiones web
- **Chrome Extension APIs**: webNavigation, declarativeNetRequest, storage, notifications
- **Algoritmo de Levenshtein** — para detectar typosquatting
- **Google Safe Browsing API** — base de datos de phishing de Google
- **declarativeNetRequest** — mismo motor que usa Brave Shields para bloquear ads

### Casos de demo (para mostrar en la presentación)
1. Visitar `http://` cualquier sitio → alerta de HTTP
2. La lista negra incluye: `secure-login-banorte.xyz`, `bancomer-seguro.net`
3. Mostrar el score 0-100 en diferentes sitios
4. Mostrar el historial de sitios analizados
5. Los trackers bloqueados (Google Analytics, Facebook Pixel)

---

## ⚠️ Íconos

Necesitan crear 3 archivos PNG simples en `/icons/`:
- `icon16.png` (16×16 px)
- `icon48.png` (48×48 px)  
- `icon128.png` (128×128 px)

Pueden usar cualquier imagen de escudo/candado. O generarla con Canva/Figma.

---

Proyecto escolar — Extensión de Seguridad Web
