# config.py
# Este archivo controla el idioma de todo el juego

# Idioma actual por defecto ('es' = Español, 'en' = Inglés)
IDIOMA_ACTUAL = "es"

# Diccionario de traducciones
# Clave (Izquierda): El nombre que usas en tu código (ej: "btn_play")
# Valor (Derecha): El nombre REAL del archivo o el texto que se mostrará
TRADUCCIONES = {
    "es": {
        # === IMÁGENES (Español) ===
        "btn_confirmar": "btn_confirmar",
        "btn_back": "btn_back",
        "btn_dificil": "btn_dificil",
        "btn_dificil2": "btn_dificil2",
        "btn_dificil3": "btn_dificil3",
        "btn_facil": "btn_facil",
        "btn_facil2": "btn_facil2",
        "btn_facil3": "btn_facil3",
        "btn_instrucciones": "btn_instrucciones", # Ojo: en main usabas "btn_instruccio", verifica el nombre real
        "btn_inst": "btn_instruccio",             # Agrego este por compatibilidad con tu main.py anterior
        "btn_nivel_1": "btn_nivel_1",
        "btn_nivel_2": "btn_nivel_2",
        "btn_nivel_3": "btn_nivel_3",
        "btn_opc": "btn_opc",
        "btn_play": "btn_play",
        "elige_dificultad_nivel1": "elige_dificultad_nivel1",
        "lose_level1": "lose_level1",
        "lose_level2": "lose_level2",
        "lose_level3": "lose_level3",
        "n2_victoria_calle_verde": "n2_victoria_calle_verde",
        "title_dificultad_2": "title_dificultad_2",
        "title_dificultad_3": "title_dificultad_3",
        "title_levels": "title_levels",
        "title_personaje": "title_personaje",
        "titulo_idioma": "titulo_idioma",
        "titulo_opciones": "titulo_opciones",
        "titulo_volume": "titulo_volume",
        "win_level1": "win_level1",
        "win_level3": "win_level3",
        "titulo_juego": "titulo_juego",
        "Tutorial": "Tutorial", # Botón menú principal

        # === TEXTOS (Español) ===
        "txt_reparar": "[R] Reparar",
        "txt_recoger": "Recoger (E)",
        "txt_plantar": "Plantar (E)",
        "txt_herramienta": "Herramienta en mano",
        "txt_zona_reparada": "¡ZONA REPARADA!",
        "txt_tiempo_agotado": "¡TIEMPO AGOTADO!",
        "txt_tutorial": "TUTORIAL DE ENTRENAMIENTO",
        "txt_movimiento": "Mover: WASD/Flechas | Acción: E",
        "txt_misiones": "Misiones: ",
        "txt_pausa": "PAUSA",
        "txt_semilla_mano": "Semilla en las manos",
        "txt_herramienta_obt": "¡Herramienta obtenida!",
        "txt_necesitas_herra": "¡Necesitas la herramienta!",
        "txt_arbol_plantado": "¡Árbol plantado!",
        "txt_semilla_recogida": "Semilla recogida",
        "txt_reparadas": "Reparadas: "
    },
    "en": {
        # === IMÁGENES (Inglés - Terminación 'us') ===
        "btn_confirmar": "btn_confirmarus",
        "btn_back": "btn_backus",
        "btn_dificil": "btn_dificilus",
        "btn_dificil2": "btn_dificil2us",
        "btn_dificil3": "btn_dificil3us",
        "btn_facil": "btn_facilus",
        "btn_facil2": "btn_facil2us",
        "btn_facil3": "btn_facil3us",
        "btn_instrucciones": "btn_instruccionesus",
        "btn_inst": "btn_instruccionesus", # Mapeo para compatibilidad
        "btn_nivel_1": "btn_nivel_1us",
        "btn_nivel_2": "btn_nivel_2us",
        "btn_nivel_3": "btn_nivel_3us",
        "btn_opc": "btn_opcus",
        "btn_play": "btn_playus",
        "elige_dificultad_nivel1": "elige_dificultad_nivel1us",
        "lose_level1": "lose_level1us",
        "lose_level2": "lose_level2us",
        "lose_level3": "lose_level3us",
        "n2_victoria_calle_verde": "n2_victoria_calle_verdeus",
        "title_dificultad_2": "title_dificultad_2us",
        "title_dificultad_3": "title_dificultad_3us",
        "title_levels": "title_levelsus",
        "title_personaje": "title_personajeus",
        "titulo_idioma": "titulo_idiomaus",
        "titulo_opciones": "titulo_opcionesus",
        "titulo_volume": "titulo_volumeus",
        "win_level1": "win_level1us",
        "win_level3": "win_level3us",
        "titulo_juego": "titulo_juegous", # Asumo que tienes este
        "Tutorial": "Tutorialus",         # Asumo que tienes este

        # === TEXTOS (Inglés) ===
        "txt_reparar": "[R] Repair",
        "txt_recoger": "Pick up (E)",
        "txt_plantar": "Plant (E)",
        "txt_herramienta": "Tool in hand",
        "txt_zona_reparada": "ZONE REPAIRED!",
        "txt_tiempo_agotado": "TIME UP!",
        "txt_tutorial": "TRAINING TUTORIAL",
        "txt_movimiento": "Move: WASD/Arrows | Action: E",
        "txt_misiones": "Missions: ",
        "txt_pausa": "PAUSE",
        "txt_semilla_mano": "Seed in hands",
        "txt_herramienta_obt": "Tool obtained!",
        "txt_necesitas_herra": "You need the tool!",
        "txt_arbol_plantado": "Tree planted!",
        "txt_semilla_recogida": "Seed picked up",
        "txt_reparadas": "Repaired: "
    }
}

def obtener_nombre(clave):
    """Devuelve el valor traducido según el idioma actual."""
    idioma = TRADUCCIONES.get(IDIOMA_ACTUAL, TRADUCCIONES["es"])
    # Devuelve la traducción o la clave original si no existe traducción
    return idioma.get(clave, clave)

def cambiar_idioma(nuevo_idioma):
    """Cambia el idioma global ('es' o 'en')."""
    global IDIOMA_ACTUAL
    if nuevo_idioma in TRADUCCIONES:
        IDIOMA_ACTUAL = nuevo_idioma