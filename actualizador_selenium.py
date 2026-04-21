"""
actualizador_selenium.py
========================
Actualiza precio + tallas del catalogo usando Selenium
(igual que el crawler original — bypasea Cloudflare).

Solo modifica: precio, precio_original, descuento,
               tallas_disponibles, tallas_agotadas, actualizado
NO modifica: nombre, sku, color, genero, categoria, coleccion, imagen, url

Uso:
    pip install selenium webdriver-manager
    python actualizador_selenium.py
    python actualizador_selenium.py --limite 100
    python actualizador_selenium.py --desde 200 --limite 100
    python actualizador_selenium.py --solo-agotados
"""

import json, time, re, logging, random, argparse
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

CATALOGO_FILE = "catalogo_adidas.json"
BACKUP_FILE   = "catalogo_adidas_backup.json"
LOG_CAMBIOS   = "cambios_catalogo.json"
GUARDAR_CADA  = 25

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s", datefmt="%H:%M:%S",
    handlers=[logging.FileHandler("actualizador.log", encoding="utf-8"),
              logging.StreamHandler()])
log = logging.getLogger(__name__)


def crear_driver():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def pausa():
    time.sleep(random.uniform(2.0, 4.0))

def cerrar_popups(driver):
    time.sleep(1.5)
    try:
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            t = btn.text.strip().upper()
            if "ACEPTAR" in t and "SEGUIMIENTO" in t:
                driver.execute_script("arguments[0].click();", btn); time.sleep(1); break
    except: pass
    try:
        btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Cerrar']")
        driver.execute_script("arguments[0].click();", btn); time.sleep(1)
    except: pass
    try: driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    except: pass

def leer_tallas(driver):
    driver.execute_script("window.scrollTo(0, 500);")
    time.sleep(2)
    disp, agot = [], []
    vistas = set()

    def es_talla(t):
        import re as _re
        t = t.strip()
        if not t or len(t) > 25: return False
        if t in {"2XS","XS","S","M","L","XL","2XL","3XL","4XL","5XL","6XL","XXL","XXXL"}: return True
        if t in {"S/M","M/L","L/XL","S/L","OSFM","OSFA","OS","ONE SIZE","JUNIOR [XS]","JUNIOR"}: return True
        if _re.match(r"^(\d*X{0,3}[SML]|[SML])\/(T[0-9]?|P|S|L)$", t, _re.IGNORECASE): return True
        if _re.match(r"^\d+X\/(T[0-9]?|P|S|L)$", t, _re.IGNORECASE): return True
        if _re.match(r"^\d*XL\/(T[0-9]?|P|S|L)$", t, _re.IGNORECASE): return True
        if _re.match(r"^[A-Z0-9]+\/[A-Z0-9]+$", t) and len(t) <= 8: return True
        if _re.match(r'^[2-4][0-9]"$', t): return True
        if _re.match(r'^\d+P$', t): return True
        if _re.match(r'^\d{2}-\d{2}$', t): return True
        if _re.match(r"^\d+\.?\d*K$", t): return True
        if _re.search(r"a[ñn]os", t, _re.IGNORECASE): return True
        if _re.match(r"^[1-7]$", t): return True
        if _re.match(r"^\d+[K]?[\d.]*-\d+[\d.]*[K]?\s*\(", t): return True
        if _re.match(r"^\d+[\d.]*-\d+[\d.]*\s*\(", t): return True
        try:
            n = float(t.replace("MX","").replace(" ",""))
            return 1.0 <= n <= 26
        except: pass
        return False

    def limpiar(t):
        import re as _r
        t = t.strip().replace("MX ","").replace("MX","").strip()
        t = _r.sub(r'\s*/\s*', '/', t)
        return t

    botones = []
    for sel in ["div[data-testid='size-selector'] button","div[class*='size-selector'] button","button[data-testid*='size']","button[class*='size']","[class*='SizeSelector'] button"]:
        try:
            b = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(b) >= 1: botones = b; break
        except: pass

    if not botones:
        try:
            for btn in driver.find_elements(By.TAG_NAME, "button"):
                try:
                    t = limpiar(btn.text)
                    if t and es_talla(t): botones.append(btn)
                except: pass
        except: pass

    for btn in botones:
        try:
            raw    = btn.text.strip()
            limpia = limpiar(raw)
            if not limpia or not es_talla(limpia): continue
            if limpia in vistas: continue
            vistas.add(limpia)
            clases  = (btn.get_attribute("class") or "").lower()
            agotada = (any(k in clases for k in ["disabled","unavailable","out-of-stock","sold-out"]) or
                       btn.get_attribute("aria-disabled") == "true" or bool(btn.get_attribute("disabled")))
            if not agotada:
                try:
                    if btn.find_elements(By.TAG_NAME, "svg"): agotada = True
                except: pass
            (agot if agotada else disp).append(limpia)
        except: pass

    if agot == ["1"] and not disp: agot = []
    return disp, agot

def obtener_precio(driver):
    precio_venta = "N/D"
    precio_original = None
    descuento = ""
    try:
        h1  = driver.find_element(By.TAG_NAME, "h1")
        cnt = driver.execute_script("""
            var el=arguments[0];
            for(var i=0;i<6;i++){el=el.parentElement;if(!el)break;
            var t=el.innerText||'';var p=t.match(/[$][\d,]+/g)||[];
            if(p.length>=1&&p.length<=5&&t.length<3000)return t;}return null;""", h1)
        if cnt:
            pct_match = re.search(r'-(\d+)%', cnt)
            if pct_match: descuento = f"-{pct_match.group(1)}%"
            precios = []
            for p in re.findall(r'\$[\d,]+(?:\.\d{2})?', cnt):
                try:
                    n = float(p.replace("$","").replace(",",""))
                    if 100 < n < 30000: precios.append((n,p))
                except: pass
            if precios:
                precios.sort()
                precio_venta    = precios[0][1]
                precio_original = precios[-1][1] if len(precios) > 1 else None
    except: pass
    return precio_venta, precio_original, descuento


def actualizar_producto(url, datos_actuales, driver):
    try:
        driver.get(url)
        cerrar_popups(driver)
        time.sleep(2)

        precio_nuevo, precio_orig_nuevo, desc_nuevo = obtener_precio(driver)
        tallas_disp, tallas_agot = leer_tallas(driver)

        cambios = {}
        if precio_nuevo and precio_nuevo != "N/D" and precio_nuevo != datos_actuales.get("precio",""):
            cambios["precio"] = {"antes": datos_actuales.get("precio",""), "ahora": precio_nuevo}

        tallas_antes = set(datos_actuales.get("tallas_disponibles", []))
        tallas_ahora = set(tallas_disp)
        if tallas_disp and tallas_antes != tallas_ahora:
            agotadas = list(tallas_antes - tallas_ahora)
            volvieron = list(tallas_ahora - tallas_antes)
            if agotadas or volvieron:
                cambios["tallas"] = {"se_agotaron": agotadas, "volvieron": volvieron,
                                      "disponibles_ahora": tallas_disp}

        datos_nuevos = dict(datos_actuales)
        if precio_nuevo and precio_nuevo != "N/D":
            datos_nuevos["precio"]          = precio_nuevo
            datos_nuevos["precio_original"] = precio_orig_nuevo
            datos_nuevos["descuento"]       = desc_nuevo
        if tallas_disp or tallas_agot:
            datos_nuevos["tallas_disponibles"] = tallas_disp
            datos_nuevos["tallas_agotadas"]    = tallas_agot
        datos_nuevos["actualizado"] = datetime.now().isoformat()

        return datos_nuevos, cambios
    except Exception as e:
        log.error(f"  Error: {e}")
        return None, {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalogo",      default=CATALOGO_FILE)
    parser.add_argument("--limite",        type=int, default=0)
    parser.add_argument("--desde",         type=int, default=0)
    parser.add_argument("--solo-agotados", action="store_true")
    args = parser.parse_args()

    with open(args.catalogo, encoding="utf-8") as f:
        catalogo = json.load(f)
    total = len(catalogo)

    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)
    log.info(f"Backup guardado ({total} productos)")

    urls_todas = list(catalogo.keys())
    if args.solo_agotados:
        urls = [u for u in urls_todas if len(catalogo[u].get("tallas_disponibles",[])) == 0]
        log.info(f"Modo solo-agotados: {len(urls)} productos")
    else:
        inicio = args.desde
        fin = (inicio + args.limite) if args.limite > 0 else total
        urls = urls_todas[inicio:fin]

    log.info(f"Total: {total} | A revisar: {len(urls)}")
    log.info("-" * 50)

    driver = crear_driver()
    cambios_log = []
    actualizados = sin_cambios = errores = 0

    try:
        for i, url in enumerate(urls, 1):
            datos = catalogo[url]
            nombre = datos.get("nombre", url)[:50]
            log.info(f"[{i}/{len(urls)}] {nombre}")

            datos_nuevos, cambios = actualizar_producto(url, datos, driver)

            if datos_nuevos is None:
                errores += 1
            else:
                catalogo[url] = datos_nuevos
                actualizados += 1
                if cambios:
                    if "precio" in cambios:
                        log.info(f"  Precio: {cambios['precio']['antes']} -> {cambios['precio']['ahora']}")
                    if "tallas" in cambios:
                        if cambios["tallas"]["se_agotaron"]:
                            log.info(f"  Agotadas: {cambios['tallas']['se_agotaron']}")
                        if cambios["tallas"]["volvieron"]:
                            log.info(f"  Volvieron: {cambios['tallas']['volvieron']}")
                    cambios_log.append({"nombre": datos.get("nombre",""), "url": url,
                                         "cambios": cambios, "timestamp": datetime.now().isoformat()})
                else:
                    log.info(f"  Sin cambios")
                    sin_cambios += 1

            if actualizados > 0 and actualizados % GUARDAR_CADA == 0:
                with open(CATALOGO_FILE, "w", encoding="utf-8") as f:
                    json.dump(catalogo, f, ensure_ascii=False, indent=2)
                log.info(f"  Guardado parcial")

            pausa()

    except KeyboardInterrupt:
        log.info("Detenido (Ctrl+C)")
    finally:
        driver.quit()
        with open(CATALOGO_FILE, "w", encoding="utf-8") as f:
            json.dump(catalogo, f, ensure_ascii=False, indent=2)
        if cambios_log:
            with open(LOG_CAMBIOS, "w", encoding="utf-8") as f:
                json.dump(cambios_log, f, ensure_ascii=False, indent=2)
        log.info(f"\nProcessados: {actualizados} | Sin cambios: {sin_cambios} | Errores: {errores} | Con cambios: {len(cambios_log)}")


if __name__ == "__main__":
    main()
