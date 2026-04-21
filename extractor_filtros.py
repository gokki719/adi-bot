import re
"""
extractor_filtros.py
====================
Convierte el texto del usuario en filtros para el motor de búsqueda.
"""


# =========================
# CATEGORÍAS
# =========================
CATEGORIAS = {
    "tenis":      ["tenis", "zapatillas", "zapatos", "calzado", "sneakers", "tennis"],
    "ropa":       ["ropa", "jersey", "playera", "chamarra", "pants", "shorts",
                   "sudadera", "camiseta", "conjunto", "uniforme"],
    "futbol":     ["tacos", "taco", "cleats", "fútbol", "futbol", "cancha"],
    "accesorios": ["gorra", "gorras", "mochila", "bolsa", "maleta",
                   "balon", "balón", "calcetines", "calcetas"],
}

# =========================
# COLECCIONES / MODELOS
# =========================
COLECCIONES = [
    # Tenis icónicos (más largo primero para que no haya conflictos)
    "handball spezial", "campus 00s", "stan smith", "campus 00",
    "samba", "gazelle", "superstar", "campus", "forum", "ultraboost",
    "nmd", "spezial", "hoops", "adizero", "sl72", "sl 72", "ozweego",
    "terrex", "supernova", "predator", "copa",
    # Modelos running/training que la gente pide por nombre
    "duramo sl", "duramo 10", "duramo", "runfalcon 5", "runfalcon 3", "runfalcon",
    "response cl", "response", "galaxy 7", "galaxy",
    "racer tr23", "racer tr", "lite racer",
    # Modelos de lifestyle adicionales
    "vl court", "sl 72 rs", "retropy", "handball",
    "adizero boston", "adizero sl", "adizero prime",
    # Modelos VL Court
    "vl court", "vl",
    # Colaboraciones
    "pharrell", "wales bonner", "bad bunny", "disney", "minecraft", "lego",
    "fear of god", "y-3", "audi",
    "mercedes amg petronas f1", "mercedes amg petronas", "mercedes amg", "mercedes",
    # Selecciones (más específico primero)
    "seleccion mx", "seleccion mexicana", "seleccion mexico",
    "manchester united", "real madrid", "boca juniors", "river plate",
    "inter miami", "as roma", "club america", "club américa",
    "tigres uanl",
    "argentina", "alemania", "españa", "italia", "colombia", "chile",
    "brasil", "peru", "perú", "gales", "escocia", "costa rica", "venezuela",
    "belgica", "bélgica", "japon", "japón",
    # Clubes y aliases
    "america", "américa", "tigres", "arsenal", "juventus", "bayern",
    "liverpool", "newcastle",
    # Aliases que se normalizan después
    "manchester", "man utd", "man u",
    "madrid",
    "tri", "el tri", "seleccion", "selección", "mexico", "méxico",

]

# =========================
# COLORES
# =========================
COLORES = [
    "negro", "negra", "negros", "negras",
    "blanco", "blanca", "blancos", "blancas",
    "gris", "grises",
    "azul marino", "azul", "azules", "marino", "navy",
    "rojo", "roja", "rojos", "rojas",
    "verde neon", "verde limón", "verde limon", "verde", "verdes",
    "cafe", "café", "cafes",
    "morado", "morada", "morados", "moradas",
    "naranja neon", "naranja", "naranjas",
    "rosa neon", "rosa", "rosas",
    "amarillo neon", "amarillo", "amarilla", "amarillos", "amarillas",
    "beige", "arena", "crema",
    "dorado", "dorada", "dorados", "doradas",
    "plateado", "plateada", "plateados",
    "vino", "borgoña", "borgona", "vinotinto",
    "turquesa", "celeste", "lavanda", "salmon", "salmón",
    "terracota", "militar",
    "violeta", "lila", "magenta", "fucsia", "fuchsia",
    "coral", "tinto", "olivo", "oliva",
    "fosforescente", "fosfo", "neon", "neón", "fluor", "flúor",
    "azul neon",
    "multicolor", "de colores", "guacamaya", "tie dye",
]

COLOR_CANONICO = {
    "negra": "negro", "negros": "negro", "negras": "negro",
    "blanca": "blanco", "blancos": "blanco", "blancas": "blanco",
    "grises": "gris",
    "azul marino": "marino", "marino": "marino", "navy": "marino",
    "azules": "azul",
    "roja": "rojo", "rojos": "rojo", "rojas": "rojo",
    "verde limón": "verde neon", "verde limon": "verde neon", "verdes": "verde",
    "café": "cafe", "cafes": "cafe",
    "morada": "morado", "morados": "morado", "moradas": "morado",
    "naranjas": "naranja",
    "rosas": "rosa",
    "amarilla": "amarillo", "amarillos": "amarillo", "amarillas": "amarillo",
    "dorada": "dorado", "dorados": "dorado", "doradas": "dorado",
    "plateada": "plateado", "plateados": "plateado",
    "fosfo": "fosforescente", "neon": "fosforescente",
    "neón": "fosforescente", "fluor": "fosforescente", "flúor": "fosforescente",
    "borgoña": "vino", "borgona": "vino", "vinotinto": "vino",
    "salmón": "salmon",
    "violeta": "morado", "lila": "morado", "magenta": "morado",
    "fucsia": "rosa", "fuchsia": "rosa", "coral": "rosa",
    "tinto": "vino", "olivo": "verde", "oliva": "verde",
    "de colores": "multicolor", "guacamaya": "multicolor",
}

# =========================
# GÉNERO
# =========================
GENERO_MAP = {
    "hombre": ["hombre", "caballero", "caballeros", "masculino", "para hombre"],
    "mujer":  ["mujer", "dama", "damas", "femenino", "para mujer", "para dama"],
    "ninos":  ["niño", "niña", "niños", "niñas", "kids", "infantil", "para niño"],
}

GENERO_MAP_EXTRA = {
    "ninos": ["para mi hijo", "para mi hija", "para mi chamaco",
              "para el niño", "para la niña", "de niño", "de niña"],
    "mujer": ["para mi esposa", "para mi novia", "para mi mamá",
              "para mi mama", "para mi hermana", "de mujer", "para ella"],
    "hombre": ["para mi esposo", "para mi novio", "para mi papá",
               "para mi papa", "para mi hermano", "de hombre", "para él"],
}

# =========================
# PRECIO
# =========================
PRECIO_BAJO = ["barato", "baratos", "económico", "economico", "precio bajo",
               "lo más barato", "lo mas barato", "económicos", "bajo presupuesto"]
PRECIO_ALTO = ["caro", "caros", "premium", "lujoso", "exclusivo",
               "lo mejor", "lo más caro", "lo mas caro", "de calidad"]

# =========================
# TALLAS
# =========================
PATRON_TALLA_ROPA    = re.compile(r'\b(talla\s*)?(2XS|XS|S|M|L|XL|2XL|3XL|4XL|XXL)\b', re.IGNORECASE)
PATRON_TALLA_GORRA   = re.compile(r'\b(S/M|M/L|L/XL)\b', re.IGNORECASE)
PATRON_TALLA_NUMERICA = re.compile(r'\b(talla\s*)?(\d{1,2}(?:\.\d)?)\b', re.IGNORECASE)

TALLA_PALABRAS = {
    "extra grande": "XL", "muy grande": "XL",
    "doble extra": "2XL", "doble xl": "2XL",
    "grande": "L", "gran ": "L",
    "mediano": "M", "mediana": "M", "medio": "M",
    "chico": "S", "chica": "S", "pequeño": "S", "pequeña": "S", "chiquito": "S",
}

# Aliases de colección para normalizar
COLECCION_ALIASES = {
    "manchester":     "manchester united",
    "man u":          "manchester united",
    "man utd":        "manchester united",
    "madrid":         "real madrid",
    "real":         "real madrid",
    "tri":            "seleccion mx",
    "el tri":         "seleccion mx",
    "seleccion":      "seleccion mx",
    "selección":      "seleccion mx",
    "mexico":         "seleccion mx",
    "méxico":         "seleccion mx",
    "seleccion mexico": "seleccion mx",
    "seleccion mexicana": "seleccion mx",
    "america":        "club america",
    "américa":        "club america",
    "ame":        "club america",
    "tigres":         "tigres uanl",
    "mercedes":       "mercedes amg petronas",
    "audi":             "Audi F1",
    "manu":             "manchester united",
    "spiderman":        "spider-man",
    "spider man":       "spider-man",
    "spider-man":       "spider-man",
    "hombre araña":     "spider-man",
    "marvel":           "spider-man",
    "star wars":        "star wars",
    "starwars":         "star wars",

    # Modelos running por alias común
    "duramo 10":      "duramo 10",
    "runfalcon 5":    "runfalcon 5",
    "runfalcon 3":    "runfalcon 3",
    # Modelo VL Court de Mercedes
    "vl":             "vl court",
}

# =========================
# EXTRACTOR PRINCIPAL
# =========================
def extraer_filtros(texto: str) -> dict:
    t = texto.lower().strip()
    filtros = {}

    # ─── Tipo jersey (local/visitante/tercero) ────────────────────────────
    # Detectar ANTES de colección para no confundir "local" con nombre
    if any(x in t for x in ["jersey local", "playera local", "uniforme local",
                              "camiseta local", " local", "local "]):
        filtros["tipo_jersey"] = "local"
    elif any(x in t for x in ["visitante", "de visita", "jersey visitante",
                                "playera visitante"]):
        filtros["tipo_jersey"] = "visitante"
    elif any(x in t for x in ["tercer jersey", "tercera", "tercer "]):
        filtros["tipo_jersey"] = "tercero"

    # ─── Colección — aliases primero, luego lista ──────────────────────────
    import re as _re_col
    for alias in sorted(COLECCION_ALIASES.keys(), key=len, reverse=True):
        if len(alias) <= 3:
            if _re_col.search(r'(?<![a-záéíóúüñ])' + _re_col.escape(alias) + r'(?![a-záéíóúüñ])', t):
                filtros["coleccion"] = COLECCION_ALIASES[alias]
                break
        elif alias in t:
            filtros["coleccion"] = COLECCION_ALIASES[alias]
            break
    if not filtros.get("coleccion"):
        for col in sorted(COLECCIONES, key=len, reverse=True):
            if col in t:
                filtros["coleccion"] = COLECCION_ALIASES.get(col, col)
                break

    # ─── Categoría ────────────────────────────────────────────────────────
    # Gorras/calcetines/mochilas → buscar en Ropa y Varios por nombre
    if any(kw in t for kw in ["gorra", "gorras", "calcet", "mochila",
                                   "balon", "balón", "balones", "pelota",
                                   "botella", "botellas", "termo", "termos", "cantimplora",
                                   "muñequera", "munequera", "muñequeras", "banda",
                                   "falda", "faldas", "vestido", "vestidos"]):
        filtros["categoria"] = "accesorios_nombre"  # flag especial
    else:
        for cat, keywords in CATEGORIAS.items():
            if any(kw in t for kw in keywords):
                filtros["categoria"] = "tenis" if cat == "futbol" else cat
                if cat == "futbol":
                    filtros["uso"] = "futbol"
                break

    # ─── Tipo de prenda específica ─────────────────────────────────────────
    if any(x in t for x in ["chamarra", "jacket", "rompevientos"]):
        filtros["tipo_prenda"] = "chamarra"
    elif any(x in t for x in ["sudadera", "hoodie", "sweatshirt"]):
        filtros["tipo_prenda"] = "chamarra"  # adidas usa "chamarra" para ZNE
    elif any(x in t for x in ["gorra", "gorras"]):
        filtros["tipo_prenda"] = "gorra"
    elif any(x in t for x in ["calcet", "calcetas", "caletas", "caleta"]):
        filtros["tipo_prenda"] = "calcetines"
    elif any(x in t for x in ["mochila", "bolsa"]):
        filtros["tipo_prenda"] = "mochila"
    elif any(x in t for x in ["shorts", "short "]) or t.strip() in ("short",) or t.endswith(" short"):
        filtros["tipo_prenda"] = "shorts"
    elif any(x in t for x in ["jersey", "playera", "camiseta", "uniforme"]):
        filtros["tipo_prenda"] = "jersey"
    elif any(x in t for x in ["balon", "balón", "balones", "pelota",
                                    "baloncesto", "basketball", "basket ball"]):
        filtros["tipo_prenda"] = "balon"
    elif any(x in t for x in ["botella", "botellas", "termo", "termos", "cantimplora", "agua"]):
        filtros["tipo_prenda"] = "botella"
    elif any(x in t for x in ["muñequera", "munequera", "muñequeras", "wristband"]):
        filtros["tipo_prenda"] = "munequera"
    elif any(x in t for x in ["falda", "faldas", "skirt"]):
        filtros["tipo_prenda"] = "falda"
    elif any(x in t for x in ["vestido", "vestidos", "dress"]):
        filtros["tipo_prenda"] = "vestido"
    elif any(x in t for x in ["conjunto", "conjuntos", "set ", "outfit"]):
        filtros["tipo_prenda"] = "conjunto"

    # ─── Portero / arquero ────────────────────────────────────────────────
    if any(x in t for x in ["portero", "arquero", "guardameta", "goalkeeper"]):
        filtros["portero"] = True

    # ─── Manga larga / manga corta ─────────────────────────────────────────
    if any(x in t for x in ["manga larga", "manga-larga", "long sleeve", "ml "]):
        filtros["manga"] = "larga"
    elif any(x in t for x in ["manga corta", "manga-corta", "short sleeve"]):
        filtros["manga"] = "corta"

    # ─── Frases de botella → normalizar ANTES del regex de capacidad ────────
    if "botella" in t or "termo" in t or filtros.get("tipo_prenda") == "botella":
        import re as _re_b
        # "500ml" sin espacio → "500 ml"
        t = _re_b.sub(r'(\d)(ml)', r' ', t)
        _tiene_num = bool(_re_b.search(r'[0-9]+\s*(ml|litro)', t))
        if not _tiene_num:
            for _f, _r in [("litro y medio","1.5 litros"),("medio litro","0.5 litros"),
                           ("un litro","1 litro"),("dos litros","2 litros"),("litro","1 litro")]:
                if _f in t:
                    t = t.replace(_f, _r)
                    filtros.pop("talla", None)
                    break
        if " medio" in t and not _tiene_num:
            t = t.replace(" medio", " 0.5 litros")
            filtros.pop("talla", None)
        # "botella de 500" → "botella de 500 ml"
        _solo = _re_b.search(r'(?<![0-9])(500|600|750|1000|250|1500|2000)(?![0-9])', t)
        if _solo and not _re_b.search(r'(ml|litro)', t):
            t = t.replace(_solo.group(), _solo.group() + " ml")

    # ─── Capacidad de botella (litros/ml) — no confundir con talla ──────────
    # "1 litro", "750 ml", "0.5 litros" → filtro separado
    _cap = re.search(r'([0-9][0-9.,]*)\s*(ml|mililitros?|litros?|lts?)\b', t)
    if _cap:
        filtros["capacidad"] = _cap.group(0).strip()
        # Evitar que el número se interprete como talla
        filtros["_skip_talla_numero"] = True

    # ─── Capacidad de botella ──────────────────────────────────────────────────
    _cap_m_rx = __import__('re').search(r'([0-9]+[.,]?[0-9]*)\s*(ml|mililitros?|litros?|lts?)', t)
    if _cap_m_rx:
        filtros["capacidad"] = _cap_m_rx.group(0).strip()
        filtros["_skip_talla_numero"] = True

    # ─── Colores (detectados en ORDEN de aparición en el texto) ─────────
    posiciones_color = []
    t_temp = t
    for color in sorted(COLORES, key=len, reverse=True):
        idx = t_temp.find(color)
        if idx >= 0:
            canonico = COLOR_CANONICO.get(color, color)
            posiciones_color.append((idx, canonico))
            # Borrar para no detectar subcadenas
            t_temp = t_temp[:idx] + " " * len(color) + t_temp[idx+len(color):]

    # Ordenar por posición en el texto original
    posiciones_color.sort(key=lambda x: x[0])
    colores_encontrados = []
    for _, canonico in posiciones_color:
        if canonico not in colores_encontrados:
            colores_encontrados.append(canonico)

    if len(colores_encontrados) == 1:
        filtros["color"] = colores_encontrados[0]
    elif len(colores_encontrados) > 1:
        filtros["color"] = colores_encontrados

    # ─── Talla ────────────────────────────────────────────────────────────
    # Palabras primero
    for palabra, talla_equiv in TALLA_PALABRAS.items():
        if palabra in t and "talla" not in filtros:
            filtros["talla"] = talla_equiv
            break
    # Ropa (XS, S, M, L...)
    m = PATRON_TALLA_ROPA.search(t)
    if m:
        filtros["talla"] = m.group(2).upper()
    else:
        # Gorra
        m = PATRON_TALLA_GORRA.search(t)
        if m:
            filtros["talla"] = m.group(0).upper()
        else:
            # Numérica — solo si no se detectó capacidad de botella
            if not filtros.get("_skip_talla_numero"):
                m = PATRON_TALLA_NUMERICA.search(t)
                if m:
                    try:
                        n = float(m.group(2))
                        if 1 <= n <= 26:
                            filtros["talla"] = m.group(2)
                    except: pass

    # ─── Género ───────────────────────────────────────────────────────────
    for gen, keywords in GENERO_MAP_EXTRA.items():
        if any(kw in t for kw in keywords):
            filtros["genero"] = gen
            break
    if "genero" not in filtros:
        for gen, keywords in GENERO_MAP.items():
            if any(kw in t for kw in keywords):
                filtros["genero"] = gen
                break

    # ─── Presupuesto maximo ─────────────────────────────────────────────
    import re as _re_pm
    _talla_actual = str(filtros.get("talla",""))
    _pm_patrones = [
        (r'(?:menos de|hasta|no mas de)\s+\$?\s*([1-9][0-9]{2,4})', False),
        (r'presupuesto de\s+\$?\s*([1-9][0-9]{2,4})', False),
        (r'de\s+([1-9][0-9]{2,4})\s+pesos', False),
        (r'en\s+([1-9][0-9]{2,4})\s+pesos', False),
        (r'([1-9][0-9]{2,4})\s+pesos', False),
        (r'\$([1-9][0-9]{2,4})', False),
        (r'mil pesos', True),
        (r'un mil', True),
    ]
    _precio_detectado = None
    for _pat, _es_mil in _pm_patrones:
        _m = _re_pm.search(_pat, t)
        if _m:
            try:
                if _es_mil:
                    _precio_detectado = 1000
                else:
                    _v = int(_m.group(1))
                    if str(_v) != _talla_actual and str(float(_v)) != _talla_actual:
                        if 100 <= _v <= 50000:
                            _precio_detectado = _v
                break
            except:
                pass
    if _precio_detectado:
        filtros["precio_maximo"] = _precio_detectado

    # ─── Modo regalo ────────────────────────────────────────────────────
    _FRASES_REGALO = ["para regalar","de regalo","quiero regalar","busco regalo",
                      "como regalo","para cumpleanos","para navidad","para el dia",
                      "para mi novia","para mi novio","para mi esposa","para mi esposo",
                      "para mi mama","para mi papa","para mi hijo","para mi hija",
                      "para mi amigo","para mi amiga","para mi hermano","para mi hermana",
                      "para mi abuelo","para mi abuela"]
    if any(fr in t for fr in _FRASES_REGALO):
        filtros["modo_regalo"] = True
        # Inferir género del destinatario para filtrar mejor
        if any(x in t for x in ["novia","esposa","mama","mamá","hija","hermana","abuela","amiga"]):
            if not filtros.get("genero"):
                filtros["genero"] = "mujer"
        elif any(x in t for x in ["novio","esposo","papa","papá","hijo","hermano","abuelo","amigo"]):
            if not filtros.get("genero"):
                filtros["genero"] = "hombre"

    # ─── Precio bajo/alto (keyword) ──────────────────────────────────────
    if any(p in t for p in PRECIO_BAJO):
        filtros["precio"] = "bajo"
    elif any(p in t for p in PRECIO_ALTO):
        filtros["precio"] = "alto"

        # ─── Uso / deporte MEJORADO ────────────────────────────
    if "uso" not in filtros:

        USOS = {
            "futbol": ["futbol", "fútbol", "tacos", "cancha", "soccer", "fut", "balon pie"],
            "basket": ["basket", "basquet", "basquetbol", "basketball", "nba"],
            "running": ["running", "correr", "run", "maraton"],
            "training": ["gym", "entrenamiento", "training", "ejercicio"],
            "padel": ["padel", "pádel"],
            "golf":  ["golf"],
            "casual": ["casual", "diario", "calle", "salir", "streetwear"]
        }

        for uso, palabras in USOS.items():
            if any(p in t for p in palabras):
                filtros["uso"] = uso
                break

    # Detectar modelo específico
    filtros["modo_modelo"] = False
    if filtros.get("coleccion"):
        palabras = t.split()
        if len(palabras) <= 3:
            filtros["modo_modelo"] = True

    # ─── Palabras clave de modelo (cuando no hay coleccion detectada) ──
    # Permite buscar cualquier modelo por nombre: "barreda", "jabbar",
    # "zx", "sl", "f50", "feroza", etc. sin tener que agregarlos uno a uno.
    if not filtros.get("coleccion"):
        # Palabras que NO son nombres de modelos
        STOPWORDS = {
            # verbos y artículos
            "quiero", "busco", "dame", "tienes", "tiene", "hay",
            "que", "del", "los", "las", "con", "por", "una", "uno",
            "algo", "unos", "unas", "para",
            # categorías de producto
            "tenis", "zapatillas", "calzado", "ropa", "jersey", "chamarra",
            "gorra", "mochila", "calcetines", "short", "shorts", "pants",
            "playera", "sudadera", "conjunto", "uniforme", "camiseta",
            # géneros
            "mujer", "hombre", "nino", "nina", "dama", "caballero",
            "masculino", "femenino", "infantil", "kids",
            # colores frecuentes (se capturan aparte)
            "negro", "negra", "negros", "blanco", "blanca", "blancos",
            "azul", "rojo", "verde", "gris", "rosa", "cafe", "morado",
            # deportes / usos
            "padel", "running", "futbol", "gym", "casual", "training",
            "basket", "senderismo",
            # precio
            "barato", "baratos", "caro", "caros", "economico",
            # tallas (texto)
            "talla", "grande", "mediano", "chico",
            # otras palabras comunes
            "color", "modelo", "tipo", "estilo", "marca",
            # conectores de refinamiento — no son modelos
            "pero", "sino", "tampoco", "aunque", "igual", "mismo", "misma",
            "mas", "más", "otra", "otro", "otras", "otros", "opciones", "opcion",
            "diferente", "distinto",
            # negaciones (capturadas en excluir_uso)
            "no", "sea", "son", "nada", "nunca",
            # verbos de petición
            "correr", "entrenar", "caminar", "jugar", "salir", "usar",
            "necesito", "quiero", "busco", "ocupo",
            # Plurales de tipo_prenda (productos usan singular)
            "botellas", "termos", "munequeras", "muñequeras", "bandas",
            "mediana", "mediano", "grande", "chico", "chica",
            "faldas", "vestidos", "conjuntos", "balones", "pelotas",
            # Sinónimos de baloncesto — ya capturados como uso=basket
            "baloncesto", "basketball", "basquet", "básquet",
            # Litros/ml — ya capturados como capacidad
            "litro", "litros", "litro",
            # Palabras de uso ya detectadas (no son modelos de producto)
            "diario", "cotidiano", "diaria", "uso", "diarios",
        }
        # Mínimo 2 letras (para capturar "zx", "sl", "vl", "f50", etc.)
        # pero excluir palabras de 1 letra y preposiciones cortas
        STOPWORDS_CORTAS = {"a", "e", "o", "y", "u", "de", "en", "el", "la"}
        palabras_query = t.split()
        kws = []
        for w in palabras_query:
            if w in STOPWORDS or w in STOPWORDS_CORTAS:
                continue
            if len(w) < 2:
                continue
            # Aceptar: modelos cortos (2-3 letras) solo si no son palabras comunes
            kws.append(w)
        # Quitar colores ya detectados
        if filtros.get("color"):
            cv = filtros["color"]
            _colores_base = set(cv if isinstance(cv, list) else [cv])
            # Agregar variantes plurales y singulares para limpiar bien
            _colores_extendidos = set(_colores_base)
            _EXTRA_COLOR_KW = {
                "fosfo","neon","neón","fluor","flúor","fosforescente","fosforescentes",
                "negra","negras","negros","blanca","blancas","blancos","grises",
                "rosas","azules","rojas","verdes","cafes","morados","naranjas","amarillos",
                "violeta","lila","magenta","fucsia","fuchsia","coral","tinto","olivo","oliva",
                "turquesa","celeste","lavanda","vino","cafe","bordo","limon",
            }
            _colores_extendidos.update(_EXTRA_COLOR_KW)
            for _c in _colores_base:
                _colores_extendidos.add(_c + "s")   # rosa → rosas
                _colores_extendidos.add(_c + "a")   # negro → negra
                _colores_extendidos.add(_c + "as")  # negro → negras
                if _c.endswith("s"): _colores_extendidos.add(_c[:-1])  # rosas → rosa
                if _c.endswith("a"): _colores_extendidos.add(_c[:-1] + "o")  # negra → negro
            kws = [w for w in kws if w not in _colores_extendidos]
        # Quitar tallas ya detectadas
        if filtros.get("talla"):
            kws = [w for w in kws if w != str(filtros["talla"]).lower()]
        # Quitar de kws palabras que ya están capturadas en tipo_prenda o uso
        tipo = filtros.get("tipo_prenda", "")
        if tipo:
            stems = {tipo, tipo + "s", tipo[:-1]}
            kws = [w for w in kws if w not in stems]
        uso_det = filtros.get("uso", "")
        VERBOS_USO = {
            "running": {"correr","run","corro","corriendo"},
            "gym":     {"entrenar","ejercicio","training","entreno"},
            "futbol":  {"futbol","fut","soccer"},
            "basket":  {"basket","basquet"},
            "padel":   {"padel"},
            "casual":  {"diario","casual","calle","cotidiano"},
        }
        if uso_det in VERBOS_USO:
            kws = [w for w in kws if w not in VERBOS_USO[uso_det]]

        # Quitar números y unidades de medida si ya están en capacidad
        if filtros.get("capacidad"):
            import re as _re_kw
            kws = [w for w in kws
                   if not _re_kw.match(r'^[0-9]+([.,][0-9]+)?(ml)?$', w)
                   and w not in ("ml","l","litro","litros","termo","termos","mililitros")]
        if filtros.get("capacidad"):
            import re as _re_kw
            kws = [w for w in kws
                   if not _re_kw.match(r'^[0-9]+([.,][0-9]+)?(ml)?$', w)
                   and w not in ("ml","l","litro","litros","termo","termos","mililitros")]
        if kws:
            filtros["nombre_kw"] = kws

    # ─── Negaciones / exclusiones ─────────────────────────────────────────
    NEGACION_USO_MAP = {
        "futbol": "futbol", "fútbol": "futbol", "tacos": "futbol",
        "fut": "futbol", "soccer": "futbol",
        "running": "running", "correr": "running", "run": "running",
        "gym": "training", "entrenamiento": "training", "training": "training",
        "basket": "basket", "basquet": "basket", "basketball": "basket",
        "padel": "padel",
        "senderismo": "senderismo", "hiking": "senderismo",
        "golf": "golf",
    }
    NEGACION_TIPO_MAP = {
        "playera": "playera", "jersey": "jersey", "chamarra": "chamarra",
        "gorra": "gorra", "mochila": "mochila", "calcetines": "calcetines",
        "shorts": "shorts",
    }
    NEGACION_STOPWORDS = {
        "hay", "tengo", "quiero", "haber", "nada", "problema",
        "algo", "eso", "esto", "los", "las", "me", "te", "le",
        "lo", "se", "un", "una", "que", "mas", "tienes", "tiene",
        "sea", "tanto", "tan",
    }

    PATRONES_NEG = [
        re.compile(r"que\s+no\s+sea\s+(?:de\s+|para\s+)?(\w+)", re.IGNORECASE),
        re.compile(r"no\s+(?:de\s+|para\s+|sean?\s+de\s+|sean?\s+)?(\w+)", re.IGNORECASE),
        re.compile(r"sin\s+(?:ser\s+de\s+|ser\s+)?(?:de\s+)?(\w+)", re.IGNORECASE),
        re.compile(r"pero\s+no\s+(?:de\s+)?(\w+)", re.IGNORECASE),
        re.compile(r"excepto\s+(?:lo\s+de\s+)?(\w+)", re.IGNORECASE),
        re.compile(r"algo\s+(?:diferente|distinto)\s+(?:al?|del?|a\s+los?)\s+(\w+)", re.IGNORECASE),
    ]

    excluir_usos, excluir_tipos = [], []
    for patron in PATRONES_NEG:
        for m in patron.finditer(t):
            palabra = m.group(1).lower().rstrip("s")
            if palabra in NEGACION_STOPWORDS:
                continue
            if palabra in NEGACION_USO_MAP and NEGACION_USO_MAP[palabra] not in excluir_usos:
                excluir_usos.append(NEGACION_USO_MAP[palabra])
            if palabra in NEGACION_TIPO_MAP and NEGACION_TIPO_MAP[palabra] not in excluir_tipos:
                excluir_tipos.append(NEGACION_TIPO_MAP[palabra])
            # también intentar sin quitar la 's'
            pal2 = m.group(1).lower()
            if pal2 in NEGACION_USO_MAP and NEGACION_USO_MAP[pal2] not in excluir_usos:
                excluir_usos.append(NEGACION_USO_MAP[pal2])

    if excluir_usos:
        filtros["excluir_uso"] = excluir_usos
        if filtros.get("uso") in excluir_usos:
            del filtros["uso"]
    if excluir_tipos:
        filtros["excluir_tipo"] = excluir_tipos

    # ─── Detectar refinamiento ────────────────────────────────────────────
    # "es_refinamiento" le dice al webhook que fusione con el contexto anterior
    FRASES_REFINAMIENTO = [
        # Cambiar uso/deporte
        "para correr", "para el gym", "para gym", "para training",
        "para futbol", "para basket", "para padel", "para senderismo", "para golf",
        "de running", "de training", "de futbol", "de basket",
        # Cambiar estilo
        "algo casual", "algo mas casual", "algo más casual",
        "algo lifestyle", "algo deportivo", "algo de calle",
        "algo mas deportivo", "algo más deportivo",
        # Negaciones
        "no de futbol", "no de running", "no de training",
        "que no sea", "sin ser de", "sin futbol", "sin running",
        # "no tienes"/"no hay" son paginación, no refinamiento — se manejan en ver.mas
        # Pedir más con refinamiento
        "algo diferente", "otro estilo", "otra opcion", "otra opción",
        "algo mas", "algo más", "pero en", "pero de",
        "en ese color", "en esa talla", "del mismo color",
        "pero casual", "pero para correr", "pero lifestyle",
        "mismo color", "misma talla",
    ]
    if any(frase in t for frase in FRASES_REFINAMIENTO):
        filtros["es_refinamiento"] = True
    # También si solo hay exclusiones sin coleccion nueva → es refinamiento
    if excluir_usos and not filtros.get("coleccion") and not filtros.get("nombre_kw"):
        filtros["es_refinamiento"] = True

    # Si hay tipo_prenda y número grande en kw → es el precio
    if not filtros.get("precio_maximo") and filtros.get("tipo_prenda"):
        for _w in list(filtros.get("nombre_kw") or []):
            try:
                _n = int(_w)
                if 100 <= _n <= 50000:
                    filtros["precio_maximo"] = _n
                    _kws2 = [x for x in filtros["nombre_kw"] if x != _w]
                    if _kws2:
                        filtros["nombre_kw"] = _kws2
                    else:
                        filtros.pop("nombre_kw", None)
                    break
            except:
                pass

    # Quitar palabras de precio de nombre_kw
    _PRECIO_WORDS = {"pesos","peso","mxn","menos","hasta","presupuesto","mil","mediana","mediano","grande","chico","chica"}
    if filtros.get("precio_maximo") or True:  # siempre limpiar estas palabras
        _kw_final = filtros.get("nombre_kw") or []
        _kw_final = [w for w in _kw_final if w not in _PRECIO_WORDS]
        import re as _re_kf
        _kw_final = [w for w in _kw_final if not _re_kf.match(r'^[0-9]+$', w)]
        if _kw_final:
            filtros["nombre_kw"] = _kw_final
        else:
            filtros.pop("nombre_kw", None)

    return filtros


# =========================
# TEST
# =========================
if __name__ == "__main__":
    queries = [
        "jersey del manchester local talla M",
        "jersey del manchester visitante talla L",
        "playera del tri talla M",
        "jersey de mexico talla L",
        "tenis blanco con morado talla 8",
        "algo de correr negro con rosa talla 7",
        "tenis para mi hijo talla 13",
        "quiero samba negros talla 8",
        "tenis baratos para gym",
        "chamarra del real madrid talla M para hombre",
        "jersey del america local talla XL",
    ]
    print(f"{'QUERY':<50} {'FILTROS'}")
    print("─" * 100)
    for q in queries:
        f = extraer_filtros(q)
        print(f"{q:<50} {f}")