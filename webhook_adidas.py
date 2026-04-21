"""
webhook_adidas.py  v3
Usa el motor de búsqueda + catálogo en lugar del cache viejo
"""

import os, json, logging, threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

# ── Motor de búsqueda nuevo ───────────────────────────────────────
from buscador import buscar_por_texto, formatear_respuesta

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
app = Flask(__name__)

CATALOGO_FILE = "catalogo_adidas.json"

# ── Health check ─────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return "Adi 🤍 activo", 200

# ── Webhook principal ─────────────────────────────────────────────
# =====================================================================
# HELPERS PARA RESPUESTAS RICAS (TELEGRAM)
# =====================================================================

def es_telegram(body: dict) -> bool:
    """Detecta si la solicitud viene de Telegram."""
    fuente = body.get("originalDetectIntentRequest", {})
    return fuente.get("source", "") == "telegram"


def respuesta_telegram(resultado: dict, respuesta_texto: str,
                        session: str, contextos_extra: list) -> dict:
    """
    Construye una respuesta con imágenes para Telegram.
    Devuelve el dict completo para jsonify().
    """
    from buscador import formatear_respuesta as fmt
    productos  = resultado.get("resultados", [])
    filtros    = resultado.get("filtros", {})
    fallback   = resultado.get("fallback", False)

    messages = []

    # ── Texto introductorio ──────────────────────────────────────────
    if fallback and filtros:
        col = filtros.get("coleccion","")
        intro = (f"No encontré exactamente lo que buscas, "
                 f"pero mira estas opciones de {col.title() if col else 'adidas'}: 👟")
    else:
        partes = []
        if filtros.get("coleccion"): partes.append(filtros["coleccion"].title())
        if filtros.get("color"):
            cv = filtros["color"]
            partes.append(", ".join(cv) if isinstance(cv, list) else cv)
        if filtros.get("talla"):     partes.append(f"talla {filtros['talla']}")
        desc = " · ".join(partes) if partes else "tu búsqueda"
        intro = f"Encontré estas opciones de {desc} 👟"

    messages.append({
        "platform": "TELEGRAM",
        "text": {"text": [intro]}
    })

    # ── Card por producto (con imagen) ──────────────────────────────
    for p in productos:
        nombre  = p.get("nombre", "")
        precio  = p.get("precio", "")
        orig    = p.get("precio_original", "")
        desc_p  = p.get("descuento", "")
        tallas  = p.get("tallas_disponibles", [])
        url     = p.get("url", "")
        imagen  = p.get("imagen", "")

        precio_str = precio
        if desc_p and orig and orig != precio:
            precio_str = f"{precio} (antes {orig}) {desc_p}"

        if tallas:
            tallas_str = (f"Tallas: {', '.join(tallas)}"
                          if len(tallas) <= 6
                          else f"Tallas disponibles: {len(tallas)}")
        else:
            tallas_str = ""

        subtitulo = f"💰 {precio_str}"
        if tallas_str:
            subtitulo += f"\n📏 {tallas_str}"

        card = {
            "platform": "TELEGRAM",
            "card": {
                "title":    nombre,
                "subtitle": subtitulo,
                "buttons":  [{"text": "Ver en adidas.mx 🔗", "postback": url}]
            }
        }
        # Agregar imagen si existe
        if imagen:
            card["card"]["imageUri"] = imagen

        messages.append(card)

    # ── Cierre ───────────────────────────────────────────────────────
    messages.append({
        "platform": "TELEGRAM",
        "text": {"text": ["¿Te interesa alguno o quieres ver más opciones? 😊"]}
    })

    return {
        "fulfillmentText":     respuesta_texto,   # fallback para otras plataformas
        "fulfillmentMessages": messages,
        "outputContexts":      contextos_extra,
    }


@app.route("/webhook", methods=["POST"])
def webhook():
    body   = request.get_json(force=True)
    qr     = body.get("queryResult", {})
    intent = qr.get("intent", {}).get("displayName", "")
    params = qr.get("parameters", {})
    query  = qr.get("queryText", "")

    log.info(f"Intent: {intent} | Query: {query}")

    # ── modo.regalo ─────────────────────────────────────────────
    if intent == "modo.regalo":
        q_lo = query.lower()
        dest = ""
        for k, n in [("novia","tu novia"),("novio","tu novio"),("esposa","tu esposa"),
                     ("esposo","tu esposo"),("mama","tu mama"),("papa","tu papa"),
                     ("hijo","tu hijo"),("hija","tu hija"),("amigo","tu amigo"),
                     ("amiga","tu amiga"),("hermano","tu hermano"),("hermana","tu hermana"),
                     ("abuelo","tu abuelo"),("abuela","tu abuela")]:
            if k in q_lo:
                dest = n; break
        sep = chr(10)
        if dest:
            msg_r = ("Que gran detalle para " + dest + "!" + sep +
                     "Para ayudarte mejor dime:" + sep +
                     "- Que tipo de producto? (tenis, ropa, gorra...)" + sep +
                     "- Cual es su talla?" + sep +
                     "- Tienes presupuesto en mente?")
        else:
            msg_r = ("Que gran detalle! Para quien es el regalo?" + sep +
                     "Dime:" + sep +
                     "- Que tipo de producto? (tenis, ropa, gorra...)" + sep +
                     "- Cual es su talla?" + sep +
                     "- Tienes presupuesto en mente?")
        return jsonify({"fulfillmentText": msg_r})

    # ── buscar.producto / recomendar / buscar.coleccion ───────────
    if intent in ("buscar.producto", "buscar.presupuesto", "recomendar.por.deporte", "buscar.coleccion", "ver.catalogo.buscar"):

        # Construir texto de búsqueda combinando params + query original
        def limpiar(v):
            v = str(v or "").strip()
            return "" if v in ("?", "$", "", "None") else v

        nombre    = limpiar(params.get("nombre_producto") or params.get("coleccion"))
        disciplin = limpiar(params.get("disciplina"))
        categ     = limpiar(params.get("categoria"))
        talla     = limpiar(params.get("talla"))

        # Armar texto completo para el extractor
        # Preferimos el query original porque ya tiene todo en lenguaje natural
        texto_busqueda = query.strip()

        # Si Dialogflow extrajo params útiles, los agregamos al texto
        if nombre and nombre.lower() not in texto_busqueda.lower():
            texto_busqueda = nombre + " " + texto_busqueda
        if talla and talla not in texto_busqueda:
            texto_busqueda += f" talla {talla}"

        # Aliases antes de buscar
        ALIASES = {
            "manchester": "manchester united", "man u": "manchester united",
            "man utd": "manchester united", "united": "manchester united",
            "el tri": "mexico", "tri": "mexico", "seleccion": "mexico",
            "madrid": "real madrid", "barça": "barcelona", "barca": "barcelona",
            "america": "club america", "aguilas": "club america",
            "bay": "bayern", "juve": "juventus",
        }
        for alias, real in ALIASES.items():
            if alias in texto_busqueda.lower() and real not in texto_busqueda.lower():
                texto_busqueda = texto_busqueda.replace(alias, real)
                break

        # Si el query no tiene colección pero hay una activa del ver.catalogo → usarla
        ctxs_all = qr.get("outputContexts", [])
        ctx_bus = next((c for c in ctxs_all if "busqueda-activa" in c.get("name","")), None)
        if ctx_bus:
            col_activa = ctx_bus.get("parameters",{}).get("coleccion_activa","")
            if col_activa and col_activa.lower() not in texto_busqueda.lower():
                # Solo añadir coleccion_activa si el query NO tiene tema propio
                # (evita que "botella de 500ml" o "gorras de audi" hereden la coleccion anterior)
                from extractor_filtros import extraer_filtros as _ef_check
                _f_chk = _ef_check(texto_busqueda)
                # Tipos de prenda que nunca son refinamiento de una colección
                _TIPOS_INDEPENDIENTES = {"botella","balon","muñequera","termo",
                                          "calcetines","mochila","gorra"}
                _tiene_tema_propio = (
                    bool(_f_chk.get("coleccion")) or   # tiene su propia colección
                    bool(_f_chk.get("color")) or        # tiene color específico
                    bool(_f_chk.get("talla")) or        # tiene talla específica
                    bool(_f_chk.get("capacidad")) or    # botella con cantidad
                    bool(_f_chk.get("uso")) or          # calcetines de FUTBOL, tenis para CORRER
                    (_f_chk.get("tipo_prenda") in _TIPOS_INDEPENDIENTES)  # botella, balon, etc.
                )
                _PRENDA_KW = {"tenis","playera","playeras","jersey","chamarra","gorra","gorras",
                               "calcetines","mochila","shorts","short","balon","botella","termo",
                               "muestrame","muéstrame","conjuntos","faldas","vestidos"}
                _kw = _f_chk.get("nombre_kw") or []
                _kw_externos = [w for w in _kw if w not in _PRENDA_KW]
                if _kw_externos:
                    _tiene_tema_propio = True  # tiene palabras propias (barreda, campus, etc.)
                if not _tiene_tema_propio:
                    texto_busqueda = col_activa + " " + texto_busqueda

        log.info(f"Buscando: '{texto_busqueda}'")

        try:
            resultado   = buscar_por_texto(texto_busqueda, top=3, ruta=CATALOGO_FILE)
            # Si no encontró nada y el query es muy vago, preguntar más
            if resultado["total"] == 0 and resultado["fallback"] and len(texto_busqueda.split()) <= 3:
                respuesta = (
                    "¡Claro! Para encontrarte lo mejor, ¿me puedes dar más detalles? 😊\n"
                    "Por ejemplo: ¿para qué lo quieres? (fútbol, gym, diario), ¿qué talla?, ¿algún color?"
                )
                return jsonify({"fulfillmentText": respuesta})

            respuesta = formatear_respuesta(resultado)

            # Guardar query, filtros y página en contexto para que ver.mas funcione
            session = body.get("session", "")
            filtros_para_guardar = {
                k: v for k, v in resultado["filtros"].items()
                if k not in ("es_refinamiento", "modo_modelo", "_skip_talla_numero", "_skip_talla")
            }
            filtros_json_str = json.dumps(filtros_para_guardar, ensure_ascii=False)

            contextos = [
                {
                    "name": f"{session}/contexts/producto-encontrado",
                    "lifespanCount": 5,
                    "parameters": {
                        "ultimo_query":  texto_busqueda,
                        "filtros_json":  filtros_json_str,
                        "pagina":        1
                    }
                },
                {
                    "name": f"{session}/contexts/busqueda-activa",
                    "lifespanCount": 3,
                    "parameters": {"ultimo_query": texto_busqueda}
                }
            ]

            # ── Respuesta rica con imágenes para Telegram ─────────────
            if es_telegram(body) and resultado.get("resultados"):
                return jsonify(respuesta_telegram(resultado, respuesta, session, contextos))

            # ── Respuesta de texto para otras plataformas ─────────────
            return jsonify({
                "fulfillmentText": respuesta,
                "outputContexts":  contextos,
            })

        except Exception as e:
            log.error(f"Error en buscador: {e}")
            respuesta = "Tuve un problema buscando ese producto. ¿Puedes intentar de nuevo? 🤍"

        return jsonify({"fulfillmentText": respuesta})

    # ── ver.mas — "muéstrame más / sí / otros modelos / algo más casual" ──
    elif intent == "ver.mas":
        from extractor_filtros import extraer_filtros as _extraer
        from motor_busqueda import cargar_productos, filtrar, ordenar
        from buscador import get_productos

        contextos = qr.get("outputContexts", [])
        ctx = next((c for c in contextos if "producto-encontrado" in c.get("name","")), None)

        if not ctx:
            return jsonify({"fulfillmentText": "¿Qué producto andas buscando? 😊"})

        params_ctx   = ctx.get("parameters", {})
        ultimo_query = params_ctx.get("ultimo_query", "")
        pagina       = int(params_ctx.get("pagina", 1))
        pagina_nueva = pagina + 1
        skip         = pagina * 3

        # Recuperar filtros guardados del contexto anterior
        filtros_json_raw = params_ctx.get("filtros_json", "")
        try:
            filtros_guardados = json.loads(filtros_json_raw) if filtros_json_raw else {}
        except Exception:
            filtros_guardados = {}

        # ── ¿El usuario está refinando o solo pidiendo más? ───────
        query_actual = query.strip()
        filtros_nuevos = _extraer(query_actual) if query_actual else {}
        es_refinamiento = filtros_nuevos.get("es_refinamiento", False)

        # Frases puras de "ver más sin cambiar nada"
        FRASES_SOLO_MAS = {
            "si", "sí", "mas", "más", "otra", "otros", "otras",
            "siguiente", "siguiente por favor", "ver mas", "ver más",
            "muestra mas", "muéstrame más", "muéstrame más opciones",
            "algo mas", "algo más", "show more", "more",
        }
        es_solo_mas = query_actual.lower().strip() in FRASES_SOLO_MAS

        # Detectar cambio de color → marcar para nueva búsqueda
        _nueva_busqueda_color = None
        if not es_solo_mas and filtros_guardados:
            from extractor_filtros import extraer_filtros as _ef_c
            _f_c = _ef_c(query_actual)
            _color_nuevo = _f_c.get("color")
            _color_guard = filtros_guardados.get("color")
            if _color_nuevo and _color_nuevo != _color_guard:
                _nueva_busqueda_color = query_actual
                filtros_guardados = {}

        if not ultimo_query and not filtros_guardados and not _nueva_busqueda_color:
            return jsonify({"fulfillmentText": "Dime qué producto buscas 😊"})

        try:
            productos = get_productos(CATALOGO_FILE)

            # ── Caso A: refinamiento con filtros nuevos ───────────
            # Ej: "algo más casual", "pero en negro", "para running"
            if es_refinamiento and filtros_guardados and not es_solo_mas:
                filtros_fusionados = dict(filtros_guardados)
                for k, v in filtros_nuevos.items():
                    if k in ("es_refinamiento", "modo_modelo", "nombre_kw"):
                        continue
                    filtros_fusionados[k] = v
                # Acumular exclusiones
                if filtros_guardados.get("excluir_uso") and filtros_nuevos.get("excluir_uso"):
                    filtros_fusionados["excluir_uso"] = list(set(
                        filtros_guardados["excluir_uso"] + filtros_nuevos["excluir_uso"]
                    ))
                # Limpiar uso si fue excluido
                if filtros_fusionados.get("excluir_uso") and filtros_fusionados.get("uso"):
                    if filtros_fusionados["uso"] in filtros_fusionados["excluir_uso"]:
                        del filtros_fusionados["uso"]

                log.info(f"🔀 ver.mas refinamiento → filtros: {filtros_fusionados}")
                encontrados = filtrar(productos, filtros_fusionados)
                if not encontrados:
                    # Relajar: quitar talla, mantener color+coleccion+exclusiones
                    f_relax = {k: v for k, v in filtros_fusionados.items()
                               if k in ("color","coleccion","uso","categoria",
                                        "excluir_uso","excluir_tipo","genero")}
                    encontrados = filtrar(productos, f_relax)
                encontrados = ordenar(encontrados, filtros_fusionados.get("precio","bajo"))

                # Deduplicar
                vistos, dedup = set(), []
                for p in encontrados:
                    sku = p.get("sku") or p.get("url","").split("/")[-1].split("?")[0]
                    if sku not in vistos:
                        vistos.add(sku)
                        dedup.append(p)

                # Empezar desde 0 porque los filtros cambiaron
                siguientes = dedup[:3]
                filtros_para_ctx = {k: v for k, v in filtros_fusionados.items()
                                    if k not in ("es_refinamiento","modo_modelo","nombre_kw")}
                pagina_nueva = 1

            # ── Caso B: paginación — mismo query, siguientes resultados ──
            else:
                # Usar el query original con top=skip+3 para garantizar mismo orden
                _q_pag = _nueva_busqueda_color if _nueva_busqueda_color else ultimo_query
                resultado_raw = buscar_por_texto(_q_pag, top=skip + 3, ruta=CATALOGO_FILE)
                todos_raw = resultado_raw["resultados"]
                siguientes = todos_raw[skip:skip + 3] if len(todos_raw) > skip else []
                # Si fue cambio de color, actualizar filtros y query para el contexto
                if _nueva_busqueda_color:
                    filtros_guardados = {k:v for k,v in resultado_raw["filtros"].items()
                                         if k not in ("es_refinamiento","modo_modelo",
                                                       "_skip_talla_numero","_skip_talla")}
                    ultimo_query = _nueva_busqueda_color

                filtros_para_ctx = filtros_guardados

            if not siguientes:
                respuesta = (
                    "Ya te mostré todo lo que tenemos de eso 😊 "
                    "¿Quieres cambiar algo como el color, talla o tipo de producto?"
                )
                return jsonify({"fulfillmentText": respuesta})

            resultado_pag = {
                "filtros":    filtros_para_ctx,
                "resultados": siguientes,
                "total":      len(siguientes),
                "fallback":   False,
            }
            respuesta = formatear_respuesta(resultado_pag)

            session = body.get("session", "")
            # Guardar filtros actualizados en contexto
            filtros_json_new = json.dumps(
                {k: v for k, v in filtros_para_ctx.items()
                 if k not in ("nombre_kw","es_refinamiento","modo_modelo")},
                ensure_ascii=False
            )
            filtros_json_new = json.dumps(
                {k: v for k, v in filtros_para_ctx.items()
                 if k not in ("nombre_kw","es_refinamiento","modo_modelo")},
                ensure_ascii=False
            )
            ctx_ver_mas = [
                {
                    "name": f"{session}/contexts/producto-encontrado",
                    "lifespanCount": 5,
                    "parameters": {
                        "ultimo_query": ultimo_query,
                        "filtros_json": filtros_json_new,
                        "pagina": pagina_nueva
                    }
                },
                {
                    "name": f"{session}/contexts/busqueda-activa",
                    "lifespanCount": 3,
                    "parameters": {
                        "ultimo_query": ultimo_query,
                        "filtros_json": filtros_json_new,
                    }
                }
            ]

            # Telegram: respuesta con imágenes
            if es_telegram(body) and resultado_pag.get("resultados"):
                return jsonify(respuesta_telegram(resultado_pag, respuesta, session, ctx_ver_mas))

            return jsonify({
                "fulfillmentText": respuesta,
                "outputContexts":  ctx_ver_mas,
            })

        except Exception as e:
            log.error(f"Error en ver.mas: {e}")
            return jsonify({"fulfillmentText": "Tuve un problema buscando más opciones. ¿Intentamos de nuevo? 🤍"})

    # ── talla.similar ─────────────────────────────────────────────
    elif intent == "talla.similar":
        contextos = qr.get("outputContexts", [])
        prod_ctx  = next((c for c in contextos if "busqueda-activa" in c.get("name","")), None)
        talla_b   = str(params.get("talla","")).strip()

        if prod_ctx:
            prod_q = prod_ctx.get("parameters",{}).get("nombre_producto") or "tenis"
            texto  = f"{prod_q} talla {talla_b}"
            try:
                resultado = buscar_por_texto(texto, ruta=CATALOGO_FILE)
                respuesta = formatear_respuesta(resultado)
            except:
                respuesta = "Dime qué producto buscas y en qué talla 👟"
        else:
            respuesta = "Dime qué producto buscas y en qué talla 👟"

        return jsonify({"fulfillmentText": respuesta})

    # ── Políticas ─────────────────────────────────────────────────
    elif intent in ("politica.envios", "politica.devoluciones"):
        if any(x in query.lower() for x in ["devoluc", "cambio", "regresar", "devolver"]):
            return jsonify({"fulfillmentText": "🔄 En adidas México tienes 30 días para devolver sin costo. El artículo debe estar sin usar y con etiquetas. Inicia en adidas.mx → Mis Pedidos → Devolver 🤍"})
        return jsonify({"fulfillmentText": "📦 Envío gratis en pedidos de $999 o más. Tiempo de entrega: 3-5 días hábiles. Rastrea tu pedido en adidas.mx → Mis Pedidos 🤍"})

    # ── adiClub ───────────────────────────────────────────────────
    elif intent in ("adiclub", "info.adiclub"):
        return jsonify({"fulfillmentText": "⭐ adiClub es gratis — acumulas puntos con cada compra y los cambias por descuentos. También tienes acceso anticipado a drops exclusivos. Únete en adidas.mx 🤍"})

    # ── Guía de tallas ────────────────────────────────────────────
    elif intent == "guia.tallas":
        return jsonify({"fulfillmentText": "📏 Mide tu pie del talón al dedo más largo en cm. Ejemplo: 25.5cm = MX 7, 26cm = MX 7.5, 26.5cm = MX 8. Guía completa en adidas.mx/guia-de-tallas 🤍"})

    # ── Qué tienes de X (consulta de categorías) ─────────────────
    elif intent == "ver.catalogo":
        from extractor_filtros import extraer_filtros, COLECCION_ALIASES
        from motor_busqueda import cargar_productos, filtrar
        filtros_cat = extraer_filtros(query)
        col = filtros_cat.get("coleccion","")
        if col:
            try:
                prods = cargar_productos(CATALOGO_FILE)
                todos = filtrar(prods, {"coleccion": col})
                # Agrupar por tipo de prenda
                cats = {}
                for p in todos:
                    nom = p.get("nombre","").lower()
                    if "jersey" in nom or "playera" in nom:
                        cats["jerseys/playeras"] = cats.get("jerseys/playeras",0) + 1
                    elif "chamarra" in nom:
                        cats["chamarras"] = cats.get("chamarras",0) + 1
                    elif "shorts" in nom:
                        cats["shorts"] = cats.get("shorts",0) + 1
                    elif "tenis" in nom or "calzado" in nom or "zapatilla" in nom:
                        cats["tenis"] = cats.get("tenis",0) + 1
                    elif "gorra" in nom:
                        cats["gorras"] = cats.get("gorras",0) + 1
                    elif "mochila" in nom:
                        cats["mochilas"] = cats.get("mochilas",0) + 1
                    elif "calcet" in nom:
                        cats["calcetines"] = cats.get("calcetines",0) + 1
                    else:
                        cats["otros"] = cats.get("otros",0) + 1

                if cats:
                    # Formato natural sin paréntesis
                    partes = []
                    for k, v in sorted(cats.items()):
                        if k == "otros" or v == 0:
                            continue
                        partes.append(f"{v} {k}")
                    if "otros" in cats and cats["otros"] > 0:
                        partes.append("y más artículos")
                    lista = ", ".join(partes)
                    nombre_col = col.replace("seleccion mx","Selección Mexicana").title()
                    respuesta = (
                        f"Del {nombre_col} tengo: {lista} 🤍\n"
                        f"¿Qué te interesa? Dime el tipo de producto y tu talla."
                    )
                else:
                    respuesta = f"Hmm, no encontré productos de {col.title()} en el catálogo 😕"
            except:
                respuesta = "¿Qué producto de adidas andas buscando? 🤍"
        else:
            respuesta = "¿De qué equipo o colección quieres ver el catálogo? 🤍"

        # Guardar colección activa en contexto para que el siguiente mensaje
        # ("muestrame los tenis") sepa a qué colección se refiere
        if col:
            session = body.get("session", "")
            return jsonify({
                "fulfillmentText": respuesta,
                "outputContexts": [
                    {
                        "name": f"{session}/contexts/busqueda-activa",
                        "lifespanCount": 5,
                        "parameters": {
                            "ultimo_query":     query,
                            "coleccion_activa": col,
                        }
                    },
                    {
                        "name": f"{session}/contexts/producto-encontrado",
                        "lifespanCount": 0,
                        "parameters": {}
                    }
                ]
            })
        return jsonify({"fulfillmentText": respuesta})

    # ── Default ───────────────────────────────────────────────────
    return jsonify({"fulfillmentText": "¡Hola! Soy Adi 🤍 ¿En qué te puedo ayudar? Busco tenis, ropa y más de adidas México."})


if __name__ == "__main__":
    app.run(port=5000, debug=True)