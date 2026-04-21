"""
actualizador_ligero.py
======================
Actualiza precio + tallas del catálogo SIN Selenium, SIN Chrome.
Solo usa requests + BeautifulSoup → corre en GitHub Actions gratis.

Solo modifica: precio, precio_original, descuento,
               tallas_disponibles, tallas_agotadas, actualizado

NO modifica: nombre, sku, color, género, categoría, colección, imagen, url

Uso local:
    pip install requests beautifulsoup4
    python actualizador_ligero.py
    python actualizador_ligero.py --limite 100
    python actualizador_ligero.py --desde 200 --limite 100
    python actualizador_ligero.py --solo-agotados
"""

import json
import re
import time
import random
import logging
import argparse
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ═══════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════
CATALOGO_FILE  = "catalogo_adidas.json"
BACKUP_FILE    = "catalogo_adidas_backup.json"
LOG_CAMBIOS    = "cambios_catalogo.json"
GUARDAR_CADA   = 50        # guardar cada N productos
PAUSA_MIN      = 2.0       # igual que el crawler original
PAUSA_MAX      = 5.0
PAUSA_LARGA_CADA = 50      # pausa larga cada N productos
PAUSA_LARGA_MIN  = 15.0    # segundos de pausa larga
PAUSA_LARGA_MAX  = 30.0
MAX_REINTENTOS = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler("actualizador.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# Rotar User-Agents como el crawler original
import random as _random_ua
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]

def get_headers():
    """Genera headers rotando User-Agent para parecer humano."""
    return {
        "User-Agent": _random_ua.choice(USER_AGENTS),
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.adidas.mx/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }

HEADERS = get_headers()  # compatibilidad

# ═══════════════════════════════════════════════════════
# EXTRAER DATOS DE LA PÁGINA
# ═══════════════════════════════════════════════════════

def _limpiar_precio(texto: str) -> str:
    """'1999' → '$1,999'  |  '1999.0' → '$1,999'"""
    try:
        n = float(str(texto).replace(",", "").replace("$", "").strip())
        return f"${int(n):,}" if n == int(n) else f"${n:,.1f}"
    except Exception:
        return str(texto).strip()


def extraer_datos_json_embebido(html: str) -> dict | None:
    """
    adidas mete el estado del producto en un JSON dentro de un <script>.
    Buscamos el bloque que contiene 'currentArticle' o 'product' con
    precio y tallas.
    """
    # Patrón 1: window.__INITIAL_STATE__ = {...}
    m = re.search(
        r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});?\s*</script>",
        html, re.DOTALL
    )
    if m:
        try:
            data = json.loads(m.group(1))
            return data
        except Exception:
            pass

    # Patrón 2: __NEXT_DATA__ (Next.js)
    m = re.search(
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.+?)</script>',
        html, re.DOTALL
    )
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # Patrón 3: JSON-LD con precio
    m = re.search(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.+?)</script>',
        html, re.DOTALL
    )
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    return None


def extraer_precio_del_html(html: str) -> tuple[str, str, str]:
    """
    Extrae (precio_actual, precio_original, descuento) del HTML.
    Maneja tanto precio normal como precio con descuento.
    """
    soup = BeautifulSoup(html, "html.parser")
    precio_actual   = ""
    precio_original = ""
    descuento_txt   = ""

    # ── Buscar en JSON embebido primero ──────────────────────────
    json_data = extraer_datos_json_embebido(html)
    if json_data:
        # Intentar sacar precio del JSON — adidas usa distintos esquemas
        # Buscar recursivamente cualquier clave con "price" o "precio"
        def buscar_precio(obj, depth=0):
            if depth > 10 or not isinstance(obj, (dict, list)):
                return None
            if isinstance(obj, list):
                for item in obj:
                    r = buscar_precio(item, depth+1)
                    if r:
                        return r
            if isinstance(obj, dict):
                for k, v in obj.items():
                    kl = k.lower()
                    if kl in ("saleprice", "price", "currentprice", "offerprice"):
                        try:
                            n = float(str(v).replace(",",""))
                            if 100 < n < 50000:  # rango razonable MXN
                                return _limpiar_precio(n)
                        except Exception:
                            pass
                    r = buscar_precio(v, depth+1)
                    if r:
                        return r
            return None

        p = buscar_precio(json_data)
        if p:
            precio_actual = p

    # ── Fallback: parsear el HTML ────────────────────────────────
    if not precio_actual:
        # Buscar patrones de precio en el HTML directo
        # Adidas MX usa "$X,XXX" en varios elementos
        patrones_precio = [
            r'\$\s*(\d{1,2},\d{3}(?:\.\d{2})?)',   # $1,999 o $1,999.00
            r'\$\s*(\d{3,5}(?:\.\d{2})?)',          # $999
        ]
        for pat in patrones_precio:
            precios_encontrados = re.findall(pat, html)
            precios_validos = []
            for p_str in precios_encontrados:
                try:
                    n = float(p_str.replace(",", ""))
                    if 100 < n < 50000:
                        precios_validos.append(n)
                except Exception:
                    pass
            if precios_validos:
                precio_actual = _limpiar_precio(min(precios_validos))
                if len(precios_validos) > 1:
                    precio_original = _limpiar_precio(max(precios_validos))
                break

    # ── Buscar precio tachado (descuento) ────────────────────────
    # Adidas usa <del> o elementos con clase "crossed-out" o "sale"
    for sel in ["del", "s", "[class*='crossed']", "[class*='sale']", "[class*='original']"]:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text(strip=True)
            m = re.search(r'\$?\s*([\d,]+)', txt)
            if m:
                try:
                    n = float(m.group(1).replace(",", ""))
                    if 100 < n < 50000:
                        precio_original = _limpiar_precio(n)
                        break
                except Exception:
                    pass

    # Si no hay precio tachado, original == actual
    if not precio_original:
        precio_original = precio_actual

    # Calcular descuento si hay diferencia
    if precio_actual and precio_original and precio_actual != precio_original:
        try:
            pa = float(precio_actual.replace("$","").replace(",",""))
            po = float(precio_original.replace("$","").replace(",",""))
            if po > 0 and pa < po:
                pct = round((1 - pa/po) * 100)
                descuento_txt = f"-{pct}%"
        except Exception:
            pass

    return precio_actual, precio_original, descuento_txt


def extraer_tallas_del_html(html: str) -> tuple[list, list]:
    """
    Extrae (tallas_disponibles, tallas_agotadas) del HTML sin Selenium.

    Estrategia:
    1. Buscar en el JSON embebido (más confiable)
    2. Buscar en el HTML con BeautifulSoup
    """
    disp: list[str] = []
    agot: list[str] = []

    # ── Estrategia 1: JSON embebido ─────────────────────────────
    json_data = extraer_datos_json_embebido(html)
    if json_data:
        def buscar_tallas(obj, depth=0):
            """Busca listas de tallas en el JSON recursivamente."""
            if depth > 12 or not isinstance(obj, (dict, list)):
                return None
            if isinstance(obj, list):
                # Si todos los elementos son dicts con "size" o "value" → lista de tallas
                if len(obj) > 0 and isinstance(obj[0], dict):
                    if any(k in obj[0] for k in ("size", "value", "localSize", "displaySize")):
                        return obj
                for item in obj:
                    r = buscar_tallas(item, depth+1)
                    if r:
                        return r
            if isinstance(obj, dict):
                # Claves que suelen contener la lista de tallas
                for k in ("sizes", "sizeList", "availableSizes", "variants", "skus"):
                    if k in obj and isinstance(obj[k], list):
                        r = buscar_tallas(obj[k], depth+1)
                        if r:
                            return r
                for v in obj.values():
                    r = buscar_tallas(v, depth+1)
                    if r:
                        return r
            return None

        tallas_json = buscar_tallas(json_data)
        if tallas_json:
            for item in tallas_json:
                if not isinstance(item, dict):
                    continue
                # Extraer el valor de la talla
                talla_val = (
                    item.get("localSize") or
                    item.get("displaySize") or
                    item.get("size") or
                    item.get("value") or ""
                )
                talla_val = str(talla_val).replace("MX ","").strip()
                if not talla_val or len(talla_val) > 10:
                    continue

                # Determinar si está disponible
                disponible = (
                    item.get("available", True) and
                    not item.get("soldOut", False) and
                    not item.get("isOutOfStock", False) and
                    item.get("availability", "IN_STOCK") != "OUT_OF_STOCK"
                )

                (disp if disponible else agot).append(talla_val)

    # ── Estrategia 2: HTML directo ───────────────────────────────
    if not disp and not agot:
        soup = BeautifulSoup(html, "html.parser")

        # Buscar botones de talla
        PATRONES_TALLA = re.compile(
            r'^(2XS|XS|S|M|L|XL|2XL|3XL|4XL|XXL|XXXL|\d{1,2}\.?\d?'
            r'|\d{1,2}-\d{1,2}\.?\d?\s*\(.*?\)'
            r'|\d{1,2}/\d{1,2})$',
            re.IGNORECASE
        )

        for btn in soup.find_all("button"):
            texto = btn.get_text(strip=True).replace("MX ", "")
            if not PATRONES_TALLA.match(texto):
                continue

            clases = " ".join(btn.get("class", [])).lower()
            aria   = btn.get("aria-disabled", "false").lower()
            dis    = btn.get("disabled")

            agotada = (
                "disabled" in clases or
                "unavailable" in clases or
                "out-of-stock" in clases or
                "sold-out" in clases or
                aria == "true" or
                dis is not None
            )
            (agot if agotada else disp).append(texto)

        # Deduplicar
        disp = list(dict.fromkeys(disp))
        agot = list(dict.fromkeys(agot))

    # ── Estrategia 3: buscar en texto plano del HTML ─────────────
    if not disp and not agot:
        # Buscar patrones numéricos de talla en el contexto de un selector
        m_all = re.findall(
            r'"(?:size|talla)":\s*"([^"]{1,8})"[^}]*"(?:available|disponible)":\s*(true|false)',
            html, re.IGNORECASE
        )
        for talla, disponible in m_all:
            t = talla.replace("MX ","").strip()
            if t:
                (disp if disponible == "true" else agot).append(t)

    return disp, agot


def pagina_valida(html: str, url: str) -> bool:
    """Verifica que la página sea un producto válido y no un 404."""
    if not html or len(html) < 1000:
        return False
    # Detectar páginas de error de adidas
    errores = ["404", "page not found", "página no encontrada",
               "producto no disponible", "no encontramos"]
    html_lower = html.lower()
    if any(e in html_lower[:3000] for e in errores):
        return False
    return True


# Código especial para indicar bloqueo (403) vs eliminado (404)
BLOQUEADO = "__BLOQUEADO__"

def obtener_pagina(url: str, session: requests.Session) -> str | None:
    """Descarga la página con reintentos."""
    bloqueos = 0
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            resp = session.get(url, headers=get_headers(), timeout=20)
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code == 404:
                return None  # Producto eliminado
            elif resp.status_code == 403:
                bloqueos += 1
                espera = 20 * intento
                log.warning(f"  HTTP 403 (bloqueo, intento {intento}) — esperando {espera}s...")
                time.sleep(espera)
            elif resp.status_code == 429:
                espera = 30 * intento
                log.warning(f"  Rate limit (429) — esperando {espera}s...")
                time.sleep(espera)
            else:
                log.warning(f"  HTTP {resp.status_code} (intento {intento})")
                time.sleep(5 * intento)
        except requests.exceptions.Timeout:
            log.warning(f"  Timeout (intento {intento})")
            time.sleep(5 * intento)
        except requests.exceptions.ConnectionError:
            log.warning(f"  Error de conexión (intento {intento})")
            time.sleep(10 * intento)
        except Exception as e:
            log.error(f"  Error inesperado: {e}")
            time.sleep(5)
    # Si todos los intentos fallaron por 403 → bloqueado, NO marcar inactivo
    if bloqueos >= MAX_REINTENTOS:
        return BLOQUEADO
    return None


# ═══════════════════════════════════════════════════════
# ACTUALIZAR UN PRODUCTO
# ═══════════════════════════════════════════════════════

def actualizar_producto(url: str, datos_actuales: dict,
                         session: requests.Session) -> tuple[dict | None, dict]:
    """
    Descarga la página del producto y compara con los datos actuales.
    Retorna (datos_nuevos, cambios_dict).
    """
    html = obtener_pagina(url, session)

    if html is None:
        return None, {"tipo": "INACTIVO", "url": url}  # 404 real

    if html == BLOQUEADO:
        log.warning(f"  ⏭️  Saltando (bloqueado por adidas) — se reintentará después")
        return None, {"tipo": "BLOQUEADO"}  # no marcar inactivo

    if not pagina_valida(html, url):
        return None, {"tipo": "INACTIVO", "url": url}

    precio_nuevo, precio_orig_nuevo, desc_nuevo = extraer_precio_del_html(html)
    tallas_disp_nuevo, tallas_agot_nuevo        = extraer_tallas_del_html(html)

    # Detectar cambios
    cambios: dict = {}

    precio_viejo = datos_actuales.get("precio", "")
    if precio_nuevo and precio_nuevo != precio_viejo:
        cambios["precio"] = {"antes": precio_viejo, "ahora": precio_nuevo}

    tallas_antes = set(datos_actuales.get("tallas_disponibles", []))
    tallas_ahora = set(tallas_disp_nuevo)
    if tallas_disp_nuevo and tallas_antes != tallas_ahora:
        agotadas_nuevas  = list(tallas_antes - tallas_ahora)
        volvieron_nuevas = list(tallas_ahora - tallas_antes)
        if agotadas_nuevas or volvieron_nuevas:
            cambios["tallas"] = {
                "se_agotaron":       agotadas_nuevas,
                "volvieron":         volvieron_nuevas,
                "disponibles_ahora": tallas_disp_nuevo,
            }

    # Construir datos actualizados (solo los campos que pueden cambiar)
    datos_nuevos = dict(datos_actuales)
    if precio_nuevo:
        datos_nuevos["precio"]          = precio_nuevo
        datos_nuevos["precio_original"] = precio_orig_nuevo
        datos_nuevos["descuento"]       = desc_nuevo
    if tallas_disp_nuevo or tallas_agot_nuevo:
        datos_nuevos["tallas_disponibles"] = tallas_disp_nuevo
        datos_nuevos["tallas_agotadas"]    = tallas_agot_nuevo
    datos_nuevos["actualizado"] = datetime.now().isoformat()

    return datos_nuevos, cambios


# ═══════════════════════════════════════════════════════
# GUARDAR
# ═══════════════════════════════════════════════════════

def guardar_catalogo(catalogo: dict) -> None:
    with open(CATALOGO_FILE, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)
    log.info(f"  💾 Catálogo guardado ({len(catalogo)} productos)")


def guardar_log_cambios(cambios_log: list) -> None:
    with open(LOG_CAMBIOS, "w", encoding="utf-8") as f:
        json.dump(cambios_log, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Actualiza precios y tallas del catálogo adidas.mx (sin Selenium)"
    )
    parser.add_argument("--catalogo",      type=str, default=CATALOGO_FILE)
    parser.add_argument("--limite",        type=int, default=0,
                        help="Cuántos productos revisar (0 = todos)")
    parser.add_argument("--desde",         type=int, default=0,
                        help="Índice desde el que empezar")
    parser.add_argument("--solo-agotados", action="store_true",
                        help="Solo revisar productos con 0 tallas disponibles")
    args = parser.parse_args()

    # Cargar catálogo
    cat_path = Path(args.catalogo)
    if not cat_path.exists():
        log.error(f"❌ No encontré el catálogo: {cat_path}")
        return

    with open(cat_path, "r", encoding="utf-8") as f:
        catalogo = json.load(f)

    total = len(catalogo)

    # Backup automático
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)
    log.info(f"✅ Backup guardado ({total} productos)")

    # Seleccionar qué actualizar
    urls_todas = list(catalogo.keys())

    if args.solo_agotados:
        urls = [u for u in urls_todas
                if len(catalogo[u].get("tallas_disponibles", [])) == 0]
        log.info(f"🔍 Modo solo-agotados: {len(urls)} productos sin tallas")
    else:
        inicio = args.desde
        fin    = (inicio + args.limite) if args.limite > 0 else total
        urls   = urls_todas[inicio:fin]

    log.info(f"📦 Total catálogo: {total}  |  A revisar: {len(urls)}")
    log.info("─" * 55)

    session      = requests.Session()
    cambios_log  = []
    actualizados = 0
    sin_cambios  = 0
    errores      = 0
    inactivos    = 0

    try:
        for i, url in enumerate(urls, start=1):
            datos = catalogo[url]
            nombre = datos.get("nombre", url)[:50]
            idx_global = (args.desde + i) if not args.solo_agotados else i

            log.info(f"[{idx_global}/{total}] {nombre}")

            datos_nuevos, cambios = actualizar_producto(url, datos, session)

            if datos_nuevos is None:
                if cambios.get("tipo") == "INACTIVO":
                    # NO borrar ni modificar el producto — solo registrar
                    log.warning(f"  ⚠️  No encontrado (puede ser temporal) — se conserva en catálogo")
                    inactivos += 1
                    cambios_log.append({
                        "nombre": datos.get("nombre",""),
                        "sku":    datos.get("sku",""),
                        "url":    url,
                        "tipo":   "POSIBLE_INACTIVO",
                        "timestamp": datetime.now().isoformat()
                    })
                    # El producto SIGUE en el catálogo sin cambios
                elif cambios.get("tipo") == "BLOQUEADO":
                    log.info(f"  ⏭️  Bloqueado — se conserva y reintenta después")
                else:
                    errores += 1
            else:
                catalogo[url] = datos_nuevos
                actualizados  += 1

                if cambios:
                    if "precio" in cambios:
                        log.info(f"  💰 Precio: {cambios['precio']['antes']} → {cambios['precio']['ahora']}")
                    if "tallas" in cambios:
                        if cambios["tallas"]["se_agotaron"]:
                            log.info(f"  📉 Se agotaron: {cambios['tallas']['se_agotaron']}")
                        if cambios["tallas"]["volvieron"]:
                            log.info(f"  📈 Volvieron:   {cambios['tallas']['volvieron']}")
                    cambios_log.append({
                        "nombre":    datos.get("nombre",""),
                        "sku":       datos.get("sku",""),
                        "url":       url,
                        "cambios":   cambios,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    log.info(f"  ✅ Sin cambios")
                    sin_cambios += 1

            # Guardar periódicamente
            if actualizados > 0 and actualizados % GUARDAR_CADA == 0:
                guardar_catalogo(catalogo)
                if cambios_log:
                    guardar_log_cambios(cambios_log)

            # Pausa aleatoria entre requests (igual que crawler original)
            time.sleep(random.uniform(PAUSA_MIN, PAUSA_MAX))

            # Pausa larga cada N productos para no levantar sospechas
            if i % PAUSA_LARGA_CADA == 0 and i > 0:
                descanso = random.uniform(PAUSA_LARGA_MIN, PAUSA_LARGA_MAX)
                log.info(f"  ☕ Pausa larga ({descanso:.0f}s) para evitar detección...")
                time.sleep(descanso)

    except KeyboardInterrupt:
        log.info("\n⏹️  Detenido manualmente (Ctrl+C)")

    finally:
        guardar_catalogo(catalogo)
        if cambios_log:
            guardar_log_cambios(cambios_log)
            log.info(f"📋 Log de cambios: {LOG_CAMBIOS}")

        log.info(f"\n{'═'*55}")
        log.info(f"  ✅ Procesados:   {actualizados}")
        log.info(f"  🟰 Sin cambios:  {sin_cambios}")
        log.info(f"  ⚠️  Inactivos:   {inactivos}")
        log.info(f"  ❌ Errores:      {errores}")
        log.info(f"  🔔 Con cambios:  {len(cambios_log)}")
        log.info(f"{'═'*55}")


if __name__ == "__main__":
    main()
