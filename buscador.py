"""
buscador.py
===========
Punto de entrada principal del buscador de Adi 🤍

Uso:
    from buscador import buscar_por_texto
    resultados = buscar_por_texto("quiero samba negros talla 8")
"""

from extractor_filtros import extraer_filtros
from motor_busqueda import cargar_productos, buscar

# Cargar catálogo una sola vez al importar
_productos = None

def get_productos(ruta="catalogo_adidas.json"):
    global _productos
    if _productos is None:
        _productos = cargar_productos(ruta)
    return _productos

def buscar_por_texto(texto: str, top: int = 3, ruta: str = "catalogo_adidas.json") -> dict:
    """
    Recibe texto libre del usuario y devuelve resultados + filtros detectados.

    Retorna:
    {
        "filtros":    {...},          # lo que se detectó
        "resultados": [...],          # lista de productos
        "total":      int,            # cuántos encontró
        "fallback":   bool,           # True si tuvo que relajar filtros
    }
    """
    productos = get_productos(ruta)
    filtros   = extraer_filtros(texto)

    # Búsqueda normal
    from motor_busqueda import filtrar, ordenar
    encontrados = filtrar(productos, filtros)
    fallback = False

    if not encontrados:
        fallback = True
        # Relajar: quitar talla, color y capacidad PERO mantener tipo_prenda/coleccion/uso
        # Esto hace que "botellas de 0.5L sin stock" muestre otras botellas, no tenis
        filtros_relajados = {k: v for k, v in filtros.items()
                             if k in ("coleccion", "tipo_prenda", "categoria", "uso", "precio_maximo", "color")}
        encontrados = filtrar(productos, filtros_relajados)

    if not encontrados:
        # Último recurso: solo categoría (sin nombre_kw para no quedarse sin nada)
        if filtros.get("categoria"):
            encontrados = filtrar(productos, {"categoria": filtros["categoria"]})

    precio_orden = filtros.get("precio", "bajo")
    encontrados  = ordenar(encontrados, precio_orden)

    # Deduplicar — mismo SKU no aparece dos veces
    vistos = set()
    dedup  = []
    for p in encontrados:
        sku = p.get("sku") or p.get("url","").split("/")[-1].split("?")[0]
        if sku not in vistos:
            vistos.add(sku)
            dedup.append(p)

    return {
        "filtros":    filtros,
        "resultados": dedup[:top],
        "total":      len(encontrados),
        "fallback":   fallback,
    }


def formatear_respuesta(resultado: dict) -> str:
    """
    Convierte el resultado en texto para responder al usuario.
    Esto lo usa el webhook directamente.
    """
    filtros    = resultado["filtros"]
    productos  = resultado["resultados"]
    fallback   = resultado["fallback"]

    if not productos:
        return "Lo siento, no encontré productos que coincidan con lo que buscas. ¿Puedo ayudarte con algo más? 😊"

    # Construir descripción de lo buscado
    partes = []
    if filtros.get("coleccion"): partes.append(filtros["coleccion"].title())
    if filtros.get("color"):
        cv = filtros["color"]
        color_str = ", ".join(cv) if isinstance(cv, list) else cv
        partes.append(color_str)
    if filtros.get("talla"):     partes.append(f"talla {filtros['talla']}")
    if filtros.get("genero"):    partes.append(f"para {filtros['genero']}")
    descripcion = " · ".join(partes) if partes else "tu búsqueda"

    if fallback:
        # Construir descripción del fallback (sin talla específica pues se relajó)
        _fb_partes = []
        if filtros.get("coleccion"): _fb_partes.append(filtros["coleccion"].title())
        if filtros.get("color"):
            _cv = filtros["color"]
            _fb_partes.append(", ".join(_cv) if isinstance(_cv, list) else _cv)
        if filtros.get("precio_maximo"): _fb_partes.append(f"menos de ${filtros['precio_maximo']}")
        _fb_desc = " · ".join(_fb_partes) if _fb_partes else ""
        if _fb_desc:
            intro = f"Encontré estas opciones de {_fb_desc}: 👟"
        else:
            intro = f"Mira estas opciones que tenemos: 👟"
    else:
        intro = f"Encontré estas opciones de {descripcion}: 👟"

    lineas = [intro, ""]
    for i, p in enumerate(productos, 1):
        nombre  = p["nombre"]
        precio  = p["precio"]
        orig    = p.get("precio_original", "")
        desc    = p.get("descuento", "")
        tallas  = p.get("tallas_disponibles", [])
        url     = p.get("url", "")

        precio_str = precio
        if desc:
            precio_str = f"{precio} ~~{orig}~~ {desc}"

        tallas_str = ""
        if tallas:
            if len(tallas) <= 6:
                tallas_str = f"Tallas: {', '.join(tallas)}"
            else:
                tallas_str = f"Tallas disponibles: {len(tallas)}"

        lineas.append(f"*{i}. {nombre}*")
        lineas.append(f"   💰 {precio_str}")
        if tallas_str:
            lineas.append(f"   📏 {tallas_str}")
        lineas.append(f"   🔗 {url}")
        lineas.append("")

    lineas.append("¿Te interesa alguno o quieres ver más opciones? 😊")
    return "\n".join(lineas)


# =========================
# TEST
# =========================
if __name__ == "__main__":
    queries = [
        "quiero unos samba negros talla 8",
        "busco jersey del america talla L",
        "tenis baratos para correr talla 7",
        "algo de argentina talla M para hombre",
        "tenis fosforescentes talla 7",
        "quiero algo casual negro",
    ]

    for q in queries:
        print(f"\n{'='*60}")
        print(f"QUERY: {q}")
        print(f"{'='*60}")
        r = buscar_por_texto(q)
        print(f"Filtros detectados: {r['filtros']}")
        print(f"Fallback: {r['fallback']}")
        print()
        print(formatear_respuesta(r))