import json
import re
import random

# =========================
# MAPEO COLORES ES → EN
# Adidas usa nombres en inglés
# =========================
COLORES_ES_EN = {
    # ── Básicos ────────────────────────────────────────────────────
    "negro":      ["black", "negro", "core black", "dark grey", "dgh solid grey", "carbon", "utility black"],
    "blanco":     ["white", "cloud white", "off white", "cream", "blanco", "ivory", "crystal white", "zero metallic", "chalk pearl", "chalk", "wonder white", "core white"],
    "gris":       ["grey", "gray", "gris", "orbit grey", "grey two", "dark grey", "grey six", "grey four", "solid grey", "Onix "],
    "azul":       ["blue", "azul", "navy", "collegiate blue", "indigo", "blue bird", "crystal sky", "glow blue", "dark blue", "night indigo", "team navy", "Mint Ton"],
    "rojo":       ["red", "rojo", "scarlet", "power red", "lucid red", "team power red", "vivid red"],
    "verde":      ["green", "verde", "aurora green", "olive", "collegiate green", "pulse lime", "semi lucid lime", "preloved green"],
    "cafe":       ["brown", "coffee", "cafe", "gum", "preloved brown", "blanch brown", "earth strata", "sand strata", "aurora coffee"],
    "morado":     ["purple", "morado", "violet", "shadow violet", "pulse lilac", "pulse magenta", "wonder orchid"],
    "naranja":    ["orange", "naranja", "coral", "semi coral", "bright orange", "impact orange", "screaming orange"],
    "rosa":       ["pink", "rosa", "clear pink", "pulse pink", "semi pink", "bliss pink", "true pink", "semi lucid pink"],
    "amarillo":   ["yellow", "amarillo", "pulse yellow", "semi spark", "bold gold", "spark"],
    "beige":      ["beige", "sand", "linen", "alumina", "wonder white", "magic beige", "halo ivory", "halo silver", "crystal linen"],
    "dorado":     ["gold", "gold metallic", "dorado", "bright gold"],
    "plateado":   ["silver", "plateado", "silver metallic", "iron metallic", "halo silver"],

    # ── Fosforescentes / neón ─────────────────────────────────────
    "fosforescente": ["pulse", "lucid", "solar", "flash", "neon", "screaming", "vivid", "bright", "semi lucid", "hi-res"],
    "neon":          ["pulse", "lucid", "solar", "flash", "neon", "screaming", "hi-res"],
    "verde neon":    ["pulse lime", "solar green", "flash lime", "hi-res green", "lucid lime", "semi lucid lime"],
    "amarillo neon": ["pulse yellow", "solar yellow", "flash yellow", "bright yellow", "spark", "semi spark"],
    "rosa neon":     ["pulse pink", "solar pink", "semi lucid pink", "lucid red", "screaming pink"],
    "naranja neon":  ["screaming orange", "impact orange", "solar orange", "flash orange"],
    "azul neon":     ["pulse blue", "solar blue", "hi-res blue", "lucid blue"],

    # ── Colores especiales / guacamaya ────────────────────────────
    "multicolor":    ["multicolor", "multi", "rainbow", "aop", "estampado", "tie dye"],
    "guacamaya":     ["multicolor", "multi", "rainbow", "bright", "pulse", "vivid"],
    "tie dye":       ["tie dye", "aop", "spray dye"],

    # ── Vino / borgoña ────────────────────────────────────────────
    "vino":          ["maroon", "burgundy", "vino", "wine", "bordeaux", "dark red", "collegiate burgundy", "shadow red", "power berry"],
    "borgoña":       ["maroon", "burgundy", "bordeaux", "collegiate burgundy", "power berry"],

    # ── Otros tonos populares ─────────────────────────────────────
    "turquesa":      ["turquoise", "turquesa", "aqua", "mint", "semi mint"],
    "celeste":       ["sky", "celeste", "light blue", "clear sky", "crystal sky", "blue burst"],
    "arena":         ["sand", "arena", "tan", "sand strata", "earth strata"],
    "crema":         ["cream", "off white", "ivory", "crema", "halo ivory"],
    "salmon":        ["salmon", "coral", "semi coral", "wonder mauve"],
    "lavanda":       ["lavender", "lavanda", "lilac", "pulse lilac", "wonder orchid"],
    "terracota":     ["terracotta", "terracota", "clay", "earth", "preloved brown"],
    "militar":       ["olive", "khaki", "military", "cargo", "field"],
    "marino":        ["navy", "marino", "dark navy", "collegiate navy", "night indigo", "night navy", "dark blue", "team navy", "collegiate navy"],
}

# Aliases — si el usuario dice esto, buscar por este color
ALIASES_COLOR = {
    "fosfo": "fosforescente",
    "fluor": "fosforescente", 
    "flúor": "fosforescente",
    "guaca": "guacamaya",
    "colorido": "multicolor",
    "de colores": "multicolor",
    "vinotinto": "vino",
    "burgundy": "borgoña",
    "sky": "celeste",
    "nude": "beige",
    "azul marino": "marino",
    "azul rey": "azul",
    "azul cielo": "celeste",
    "verde limón": "verde neon",
    "verde manzana": "verde neon",
}

# =========================
# COLECCIONES DE EQUIPOS
# Para excluir calcetines de equipo cuando no se pidió uno específico
# =========================
COLECCIONES_EQUIPO = {
    "argentina", "alemania", "españa", "italia", "colombia", "chile",
    "brasil", "peru", "gales", "escocia", "costa rica", "venezuela",
    "belgica", "japon", "seleccion mx", "man united", "real madrid",
    "boca juniors", "river plate", "inter miami", "as roma", "club america",
    "tigres uanl", "arsenal", "juventus", "bayern munich", "liverpool",
    "newcastle",
    "mercedes amg", "audi f1", "copa mundial",
}

# =========================
# CARGAR CATÁLOGO
# =========================
def cargar_productos(ruta="catalogo_adidas.json"):
    with open(ruta, "r", encoding="utf-8") as f:
        return list(json.load(f).values())

# =========================
# EXTRAER COLOR PRINCIPAL
# Deriva color en español a partir del campo "color"
# =========================
def normalizar_color(color_query):
    """Convierte alias o variantes al color estándar del motor."""
    q = color_query.lower().strip()
    if q in ALIASES_COLOR:
        return ALIASES_COLOR[q]
    return q

def color_en_espanol(p):
    """Devuelve el color en español detectado, o '' si no se puede."""
    color_raw = (p.get("color") or p.get("color_principal") or "").lower()
    if not color_raw:
        return ""
    for esp, terminos_en in COLORES_ES_EN.items():
        if any(t in color_raw for t in terminos_en):
            return esp
    return ""

# =========================
# FILTRAR
# =========================
def filtrar(productos, filtros):
    resultados = []

    # Pre-construir keywords de exclusión una sola vez (performance)
    _excluir_usos  = filtros.get("excluir_uso", [])
    _excluir_tipos = filtros.get("excluir_tipo", [])

    # Keywords por uso para exclusión (espejo de los de inclusión)
    _USO_KW_EXCL = {
        "futbol":     ["predator", "copa", "f50", "tacos", "futbol", "americano",
                       "cleats", "firm ground", "terreno firme", "cesped"],
        "running":    ["running", "run", "ultraboost", "supernova", "adizero",
                       "response", "duramo", "galaxy", "runfalcon"],
        "training":   ["training", "gym", "dropset", "trainer"],
        "basket":     ["basket", "hoops", "jabbar", "dame"],
        "padel":      ["padel", "ubersonic", "courtquick", "barricade", "defiant"],
        "senderismo": ["terrex", "hiking", "senderismo", "skychaser"],
        "golf":       ["golf"],
    }

    for p in productos:

        # ─── Precio maximo (presupuesto) ────────────────────────────
        if filtros.get("precio_maximo"):
            p_str = p.get("precio","").replace("$","").replace(",","").strip()
            try:
                if float(p_str) > filtros["precio_maximo"]:
                    continue
            except:
                pass

        # ─── Exclusiones activas (usuario dijo "no de X") ─────────
        if _excluir_usos:
            texto_p = (p.get("nombre","") + " " + p.get("coleccion","")).lower()
            excluido = False
            for uso_excl in _excluir_usos:
                kws = _USO_KW_EXCL.get(uso_excl, [uso_excl])
                if any(k in texto_p for k in kws):
                    excluido = True
                    break
            if excluido:
                continue

        if _excluir_tipos:
            nombre_p = p.get("nombre","").lower()
            excluido = False
            for tipo_excl in _excluir_tipos:
                if tipo_excl in nombre_p:
                    excluido = True
                    break
            if excluido:
                continue

        # ─── Categoría ────────────────────────────────────────────
        cat_filtro = filtros.get("categoria","")
        if cat_filtro:
            if cat_filtro == "accesorios_nombre":
                pass  # tipo_prenda filtra por nombre más abajo
            elif cat_filtro == "tenis":
                cat_r = p.get("categoria","").lower()
                nom_r = p.get("nombre","").lower()
                # Excluir accesorios siempre
                if cat_r == "accesorios":
                    continue
                # Excluir productos de ropa aunque tengan cat=Tenis (bug del scraper)
                _ROPA_PALABRAS = {"playera","jersey","chamarra","sudadera","pants","shorts","conjunto","falda","vestido","polo","camiseta"}
                if any(x in nom_r for x in _ROPA_PALABRAS):
                    # Solo excluir si el nombre sugiere claramente ropa (no "playera de tenis")
                    _es_ropa = any(nom_r.startswith(x) or nom_r.startswith("playera ") for x in _ROPA_PALABRAS)
                    if _es_ropa and "tenis" not in nom_r:
                        continue
                # cat=Ropa: aceptar solo si "tenis" está en el nombre
                if cat_r == "ropa":
                    if "tenis" not in nom_r:
                        continue
                # cat=Varios: aceptar si hay colección específica y "tenis" en nombre
                if cat_r == "varios":
                    if filtros.get("coleccion") and "tenis" in nom_r:
                        pass
                    else:
                        continue
                # Verificar que "tenis" esté en cat+nombre
                if "tenis" not in (cat_r + " " + nom_r):
                    continue
            elif cat_filtro == "ropa":
                cat_r2 = p.get("categoria","").lower()
                if filtros.get("coleccion"):
                    if cat_r2 not in ("ropa","varios"): continue
                elif cat_r2 != "ropa": continue
            elif cat_filtro == "ropa":
                cat_r2 = p.get("categoria","").lower()
                if filtros.get("coleccion"):
                    if cat_r2 not in ("ropa","varios"): continue
                elif cat_r2 != "ropa": continue
            elif cat_filtro.lower() not in (p.get("categoria","") + " " + p.get("nombre","")).lower():
                continue

        # ─── Tipo de prenda (gorra/calcetines/chamarra/etc) ───────
        if filtros.get("tipo_prenda"):
            nombre_p = p.get("nombre","").lower()
            tp = filtros["tipo_prenda"]
            if tp == "gorra" and "gorra" not in nombre_p:
                continue
            elif tp == "calcetines" and not any(x in nombre_p for x in ["calcet","calceta"]):
                continue
            elif tp == "calcetines" and not filtros.get("coleccion"):
                col_prod = p.get("coleccion","").lower()
                if filtros.get("uso") == "futbol":
                    nom_c = p.get("nombre","").lower()
                    if col_prod not in COLECCIONES_EQUIPO and not any(x in nom_c for x in ["futbol","fútbol","soccer"]):
                        continue
                elif col_prod in COLECCIONES_EQUIPO:
                    continue
            elif tp == "mochila" and "mochila" not in nombre_p:
                continue
            elif tp == "chamarra" and "chamarra" not in nombre_p:
                continue
            elif tp == "sudadera" and "sudadera" not in nombre_p:
                continue
            elif tp == "shorts" and "short" not in nombre_p:
                continue
            elif tp == "jersey":
                if not any(x in nombre_p for x in ["playera","jersey","camiseta","uniforme","polo"]):
                    continue
                if any(x in nombre_p for x in ["shorts","mochila","gorra","calcet","sudadera","pants","tenis"]):
                    continue
            elif tp == "conjunto":
                if "conjunto" not in nombre_p and "set " not in nombre_p:
                    continue
                # Excluir conjuntos de niños cuando no se pidió específicamente niños
                if filtros.get("genero","") != "ninos":
                    if any(x in nombre_p for x in ["niño","niños","nino","ninos",
                                                     "infantil","kids"," mini"]):
                        continue
            elif tp == "balon":
                # "ball" se quita porque "football" también lo contiene
                if not any(x in nombre_p for x in ["balón","balon","pelota","minibal"]):
                    continue
            elif tp == "botella":
                if not any(x in nombre_p for x in ["botella","termo","cantimplora","water","squeeze"]):
                    continue
            elif tp == "munequera":
                if not any(x in nombre_p for x in ["muñequera","munequera","wristband","banda "]):
                    continue
            elif tp == "falda":
                if not any(x in nombre_p for x in ["falda","skirt"]):
                    continue
            elif tp == "vestido":
                if not any(x in nombre_p for x in ["vestido","dress"]):
                    continue

        # ─── Manga larga / manga corta ──────────────────────────────────────
        if filtros.get("manga"):
            _nom_manga = p.get("nombre","").lower()
            if filtros["manga"] == "larga":
                if "manga larga" not in _nom_manga and "long sleeve" not in _nom_manga:
                    continue
            elif filtros["manga"] == "corta":
                if "manga larga" in _nom_manga or "long sleeve" in _nom_manga:
                    continue

        # ─── Capacidad de botella ─────────────────────────────────────────────
        if filtros.get("capacidad") and filtros.get("tipo_prenda") == "botella":
            _nom_bot = p.get("nombre","").lower()
            cap = filtros["capacidad"].lower()
            # Extraer número de la capacidad pedida
            _num_cap = re.search(r'[0-9.,]+', cap)
            if _num_cap:
                num = float(_num_cap.group().replace(',','.'))
                # Convertir todo a ml para comparar
                ml_pedido = int(num * 1000) if ("litro" in cap or cap.strip().endswith(" l")) else int(num)
                # Calcular siempre en litros para generar variantes correctas
                # 500ml → num_l=0.5 → "0.5", "0,5" que matchean "0,5 litros"
                num_l = num / 1000 if num >= 100 else num
                dec_l = f"{num_l:.3f}".rstrip("0").rstrip(".")
                dec_l_c = dec_l.replace(".", ",")
                variantes = [
                    f"{ml_pedido} ml", f"{ml_pedido}ml",
                    dec_l, dec_l_c,
                    dec_l + " litro", dec_l_c + " litro",
                    dec_l + " l",   dec_l_c + " l",
                    str(ml_pedido),
                ]
                if num_l >= 1:
                    variantes += [f"{int(num_l)} litro", f"{int(num_l)} l"]
                variantes = [v for v in set(variantes) if v and len(v) > 1]
                if not any(v in _nom_bot for v in variantes):
                    continue

        # ─── Balon de basketball — buscar en campo color también ─────────────
        if filtros.get("tipo_prenda") == "balon" and filtros.get("uso") == "basket":
            _nom_b = p.get("nombre","").lower()
            _col_b = p.get("color","").lower()
            if not any(x in _nom_b or x in _col_b
                       for x in ["basket","basketball","all court","pro 3","nba"]):
                continue

        # ─── Excluir tacos cuando buscan tenis por color sin especificar futbol ─
        # "tenis morados para hombre" no debe mostrar tacos de fútbol
        if (filtros.get("categoria") in ("tenis", "calzado") and
                not filtros.get("uso") and
                not filtros.get("coleccion")):
            _nom = p.get("nombre","").lower()
            if any(x in _nom for x in ["tacos ", "taco ", "taco de",
                                        "cesped","césped","terreno firme",
                                        "multiterreno","sala ",
                                        "calzado de fútbol","calzado de futbol",
                                        "f50 ", "f50 "]):
                continue

        # ─── Manga larga / manga corta ──────────────────────────────────────
        if filtros.get("manga"):
            _mn = p.get("nombre","").lower()
            if filtros["manga"] == "larga":
                if "manga larga" not in _mn and "long sleeve" not in _mn: continue
            elif filtros["manga"] == "corta":
                if "manga larga" in _mn or "long sleeve" in _mn: continue

        # ─── Portero / arquero ───────────────────────────────────────────
        if filtros.get("portero"):
            _nom_p = p.get("nombre","").lower()
            if not any(x in _nom_p for x in ["portero","arquero","arquera","goalkeeper"]):
                continue

        # ─── Nombre clave de modelo (barreda, jabbar, etc.) ─────────
        if filtros.get("nombre_kw"):
            nombre_p = p.get("nombre","").lower()
            if not any(kw in nombre_p for kw in filtros["nombre_kw"]):
                continue

        # ─── Colección (marca/modelo) FLEXIBLE
        if filtros.get("coleccion"):
            col = filtros["coleccion"].lower()
            texto_p = (p.get("coleccion","") + " " + p.get("nombre","")).lower()

            if filtros.get("modo_modelo"):
                # modo estricto: buscar en coleccion+nombre
                # Algunos productos (gorras de Audi) tienen coleccion='Originals'
                # pero sí tienen el nombre de la marca en el NOMBRE del producto
                if col not in texto_p:
                    # segunda oportunidad: buscar todas las palabras en el nombre
                    nombre_p = p.get("nombre","").lower()
                    palabras = col.split()
                    if not all(palabra in nombre_p for palabra in palabras):
                        continue
            else:
                palabras = col.split()
                if not all(palabra in texto_p for palabra in palabras):
                    continue
                # Spider-Man: acepta col=Disney si "spider" está en el nombre
                col_p_e = p.get("coleccion","").lower()
                nom_p_e = p.get("nombre","").lower()
                if col == "spider-man" and col_p_e != "spider-man":
                    if "spider" not in nom_p_e:
                        continue
                # Colecciones contaminadas: filtrar por nombre si la colección no coincide exactamente
                elif filtros.get("nombre_kw") and col_p_e != col:
                    if not any(kw in nom_p_e for kw in filtros["nombre_kw"]):
                        continue

                # ─── Tipo jersey (local/visitante/tercero) ────────────────
        if filtros.get("tipo_jersey"):
            nombre_p = p.get("nombre","").lower()
            tj = filtros["tipo_jersey"]
            if tj == "local" and "local" not in nombre_p:
                continue
            elif tj == "visitante" and "visitante" not in nombre_p:
                continue
            elif tj == "tercero" and "tercer" not in nombre_p:
                continue

        # ─── Color ────────────────────────────────────────────────
        color_campo = p.get("color","").lower()  # ej: "core black / cloud white / gum"
        color_raw   = (color_campo + " " + p.get("color_principal","").lower())

        if filtros.get("color") and color_raw:
            cv    = filtros["color"]
            lista = cv if isinstance(cv, list) else [cv]

            # Primer color → debe estar en el color PRINCIPAL (antes del primer /)
            color_principal_producto = color_campo.split("/")[0].strip() if color_campo else ""
            primer_color_query = normalizar_color(str(lista[0]))
            terminos_principal = COLORES_ES_EN.get(primer_color_query, [primer_color_query])
            if color_principal_producto:
                if not any(t in color_principal_producto for t in terminos_principal):
                    continue  # Color principal no coincide → descartar

            # Segundo color → debe estar en alguna parte del color completo
            if len(lista) > 1:
                segundo_color_query = normalizar_color(str(lista[1]))
                terminos_segundo = COLORES_ES_EN.get(segundo_color_query, [segundo_color_query])
                if color_raw and not any(t in color_raw for t in terminos_segundo):
                    continue  # No tiene el segundo color → descartar

        # ─── Talla ────────────────────────────────────────────────
        if filtros.get("talla"):
            talla = str(filtros["talla"])
            if talla not in p.get("tallas_disponibles", []):
                continue

        # ─── Género ───────────────────────────────────────────────
        if filtros.get("genero"):
            g = filtros["genero"].lower()
            pg = p.get("genero", "").lower()
            if g == "ninos":
                # Para niños solo aceptar productos específicamente de niños
                if "nino" not in pg and "niño" not in pg:
                    continue
            else:
                # Para hombre/mujer, Unisex también aplica
                if pg != "unisex" and g not in pg:
                    continue

        # ─── Precio máximo ────────────────────────────────────────
        if filtros.get("precio_max"):
            precio_str = p.get("precio", "").replace("$","").replace(",","")
            try:
                if float(precio_str) > filtros["precio_max"]:
                    continue
            except: pass

        # ─── Variante (local/visitante/tercero) ──────────────────
        if filtros.get("variante"):
            variante = filtros["variante"].lower()
            nombre_p = p.get("nombre","").lower()
            VARIANTE_KW = {
                "local":     ["local"],
                "visitante": ["visitante", "visita"],
                "tercero":   ["tercero", "tercer", "third", "3er"],
                "portero":   ["portero", "arquero"],
            }
            kws = VARIANTE_KW.get(variante, [variante])
            if not any(k in nombre_p for k in kws):
                continue

        # ─── Uso / deporte ────────────────────────────────────────
        if filtros.get("uso"):
            texto = (p.get("nombre","") + " " + p.get("coleccion","")).lower()
            uso = filtros["uso"].lower()
            nombre_p = p.get("nombre","").lower()

            # ── Padel: PRIMERO excluir todo lo que no sea calzado de padel ──
            if uso == "padel":
                if any(x in nombre_p for x in ["playera", "polo", "camisa", "jersey",
                                                "short", "sudadera", "pants", "calcet",
                                                "mochila", "gorra", "muñequera",
                                                "munequera", "banda", "bolsa"]):
                    continue
                if not any(x in nombre_p for x in ["tenis", "calzado"]):
                    continue

            keywords = {
                "gym":        ["training","gym","dropset","ultraboost"],
                "basket":     ["basket", "hoops", "forum", "jabbar", "anthony edwards", "dame"],
                "futbol":     ["predator", "copa", "f50", "tacos", "futbol"],
                "running":    ["running", "run", "ultraboost", "supernova", "adizero",
                               "response", "duramo", "galaxy", "runfalcon"],
                "training":   ["training", "gym", "dropset", "trainer"],
                "padel":      ["padel", "ubersonic", "courtquick", "barricade", "defiant"],
                "casual":     ["samba", "gazelle", "campus", "forum", "superstar",
                               "stan smith", "spezial", "hoops"],
                "senderismo": ["terrex","hiking","senderismo"],
            }

            # Definir si el tipo de prenda es un accesorio/ropa (no calzado)
            TIPO_NO_CALZADO = {"calcetines","gorra","mochila","balon","botella",
                               "munequera","falda","vestido","conjunto"}
            tipo_es_no_calzado = filtros.get("tipo_prenda") in TIPO_NO_CALZADO

            # Solo filtrar por keywords de uso si es calzado
            if uso in keywords and not tipo_es_no_calzado:
                if not any(k in texto for k in keywords[uso]):
                    continue

            # FIX: running/gym/training/basket/futbol/senderismo = solo calzado.
            # Palabras como "adizero" aparecen en ropa (ADIZERO F SGL = camiseta)
            # y también en tenis. La categoría del catálogo es la fuente de verdad.
            USOS_SOLO_CALZADO = ("running", "gym", "training",
                                  "basket", "futbol", "senderismo")
            if uso in USOS_SOLO_CALZADO and not tipo_es_no_calzado:
                cat_p = p.get("categoria", "").lower()
                nom_p = p.get("nombre", "").lower()
                # Tenis, Calzado, y Varios con tacos/calzado en nombre = OK
                es_calzado_valido = (
                    cat_p in ("tenis", "calzado") or
                    (cat_p == "varios" and any(x in nom_p for x in ["taco", "calzado", "tenis"]))
                )
                if not es_calzado_valido:
                    continue

        resultados.append(p)

    return resultados

# =========================
# ORDENAR
# Mayor número de tallas disponibles primero
# Si hay descuento, sube posición
# =========================
def ordenar(resultados, precio="bajo"):
    def score(p):
        tallas = len(p.get("tallas_disponibles", []))
        desc = 1 if p.get("descuento") else 0
        precio_num = 0
        try:
            precio_num = float(p.get("precio","0").replace("$","").replace(",",""))
        except: pass
        if precio == "bajo":
            # Priorizar: 1) tiene descuento, 2) más tallas, 3) precio más bajo
            return (desc, tallas, -precio_num)
        else:
            return (tallas, desc, precio_num)
    return sorted(resultados, key=score, reverse=True)

# =========================
# MOTOR PRINCIPAL
# =========================
def buscar(productos, filtros, top=3):
    resultados = filtrar(productos, filtros)


    # SI ES MODELO → NO MEZCLAR
    if filtros.get("modo_modelo"):
        precio_orden = filtros.get("precio", "bajo")
        resultados = ordenar(resultados, precio_orden)
        return resultados[:top]

    # CASO ESPECIAL: PADEL → NO FALLBACK
    if filtros.get("uso") == "padel":
        precio_orden = filtros.get("precio", "bajo")
        resultados = ordenar(resultados, precio_orden)
        return resultados[:top]

    # fallback normal
    if len(resultados) < 3:
        filtros_relajados = {}

        if filtros.get("uso"):
            filtros_relajados["uso"] = filtros["uso"]

        if filtros.get("categoria"):
            filtros_relajados["categoria"] = filtros["categoria"]

        nuevos = filtrar(productos, filtros_relajados)

        for p in nuevos:
            if p not in resultados:
                resultados.append(p)

    precio_orden = filtros.get("precio", "bajo")
    resultados = ordenar(resultados, precio_orden)

    # Deduplicar
    vistos = set()
    dedup = []
    for p in resultados:
        sku = p.get("sku") or p.get("url","").split("/")[-1]
        if sku not in vistos:
            vistos.add(sku)
            dedup.append(p)

    return dedup[:top]

# =========================
# QUICK TEST
# =========================
if __name__ == "__main__":
    productos = cargar_productos()
    print(f"Cargados: {len(productos)} productos\n")

    tests = [
        ("Tenis negros", {"categoria": "tenis", "color": "negro"}),
        ("Tenis blancos talla 7", {"categoria": "tenis", "color": "blanco", "talla": "7"}),
        ("Ropa talla M para hombre", {"categoria": "ropa", "talla": "M", "genero": "hombre"}),
        ("Samba talla 8", {"coleccion": "samba", "talla": "8"}),
        ("Tenis casual baratos", {"uso": "casual"}),
        ("Tenis de futbol", {"uso": "futbol"}),
        ("America talla L", {"coleccion": "club america", "talla": "L"}),
    ]

    for nombre, filtros in tests:
        print(f"=== {nombre} ===")
        r = buscar(productos, filtros)
        for p in r:
            color_es = color_en_espanol(p)
            print(f"  {p['nombre'][:45]:45} | {p['precio']:8} | {color_es or p['color_principal']:15} | {len(p['tallas_disponibles'])} tallas")
        print()