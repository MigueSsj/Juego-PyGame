# config.py
# Este archivo controla el idioma de todo el juego
import pygame
from pathlib import Path

# Idioma actual por defecto ('es' = Español, 'us' = Inglés)
IDIOMA_ACTUAL = "es"

# Diccionario de traducciones
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
        "btn_instrucciones": "btn_instrucciones",
        "btn_inst": "btn_instrucciones",
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
        "titulo_volume": "titulo_volumen",
        "win_level1": "win_level1",
        "win_level3": "win_level3",
        "titulo_juego": "titulo_juego",
        "Tutorial": "Tutorial",
        "contador_basura": "contador_basura",
        "basurita_entregada": "basurita_entregada",
        "flecha_indicador": "flecha_indicador", 

        # === TEXTOS (Español) ===
        "txt_reparar": "[R] Reparar",
        "txt_recoger": "Recoger (E)",
        "txt_plantar": "Plantar (E)",
        "txt_depositar": "Depositar: E",
        "txt_mover_accion_pausa": "Mover: WASD/Flechas | Acción: E / Enter | Pausa: Espacio",
        "txt_herramienta": "Herramienta en mano",
        "txt_zona_reparada": "¡ZONA REPARADA!",
        "txt_tiempo_agotado": "¡TIEMPO AGOTADO!",
        "txt_tutorial_title": "TUTORIAL DE ENTRENAMIENTO",
        "txt_movimiento": "MOVERSE:",
        "txt_misiones": "Misiones: ",
        "txt_pausa_menu": "PAUSA",
        "txt_semilla_mano": "Semilla en las manos",
        "txt_herramienta_obt": "¡Herramienta obtenida!",
        "txt_necesitas_herra": "¡Necesitas la herramienta!",
        "txt_arbol_plantado": "¡Árbol plantado!",
        "txt_semilla_recogida": "Semilla recogida",
        "txt_reparadas": "Reparadas: ",
        "txt_e_key": "E",
        "txt_basura_recolectada": "Basura recolectada",
        "txt_basura_entregada": "¡Basura entregada!",
        "txt_basura_mano": "Basura en las manos",
        "txt_recoger_e": "Recoger: E",
        "txt_depositar_e": "Depositar: E",
        "txt_entregadas": "Entregadas:",
        "txt_parque_limpio": "¡Parque limpio!",
        "txt_park_hud_title": "Nivel 1 – El Parque",
        "txt_calle_hud_title": "Nivel 2 – La Calle",
        "txt_plaza_hud_title": "Nivel 3 – La Plaza",
        "txt_dificil_tiempo": "(Difícil, con tiempo)",
        "txt_facil_tiempo": "(Fácil, con tiempo)",
        
        # Textos específicos del Tutorial
        "txt_tutorial_msg1": "¡Basura recogida! Llévala al bote.",
        "txt_tutorial_msg2": "¡FELICIDADES! Siguiente: Plantación.",
        "txt_tutorial_msg3": "Semilla recogida. ¡Plántala en el hueco!",
        "txt_tutorial_msg4": "¡Plantación iniciada! Espera a que crezca el árbol.",
        "txt_tutorial_msg5": "¡Árbol plantado! REPARA LA PLAZA. Tienes 50 s.",
        "txt_tutorial_msg6": "¡VICTORIA! Con esfuerzo y orden, transformaste la ciudad.",
        "txt_tutorial_msg7": "Ya tienes una herramienta",
        "txt_tutorial_fail": "¡TIEMPO AGOTADO! La ciudad no se transformó.",
        "txt_tutorial_time": "TIEMPO:",
        
        "txt_plantar_semilla": "Plantar semilla (E)",
        "txt_recoger_semilla": "Recoger semilla (E)",
    },
    "us": { # <--- IMPORTANTE: CAMBIADO DE "en" A "us"
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
        "btn_inst": "btn_instruccionesus",
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
        "titulo_volume": "titulo_volumenus",
        "win_level1": "win_level1us",
        "win_level3": "win_level3us",
        "titulo_juego": "titulo_juegous",
        "Tutorial": "Tutorialus",
        "contador_basura": "contador_basuraus",
        "basurita_entregada": "basurita_entregadaus",
        "flecha_indicador": "flecha_indicador",

        # === TEXTOS (Inglés) ===
        "txt_reparar": "[R] Repair",
        "txt_recoger": "Pick up (E)",
        "txt_plantar": "Plant (E)",
        "txt_depositar": "Deposit: E",
        "txt_mover_accion_pausa": "Move: WASD/Arrows | Action: E / Enter | Pause: Space",
        "txt_herramienta": "Tool in hand",
        "txt_zona_reparada": "ZONE REPAIRED!",
        "txt_tiempo_agotado": "TIME UP!",
        "txt_tutorial_title": "TRAINING TUTORIAL",
        "txt_movimiento": "MOVE:",
        "txt_misiones": "Missions: ",
        "txt_pausa_menu": "PAUSE",
        "txt_semilla_mano": "Seed in hands",
        "txt_herramienta_obt": "Tool obtained!",
        "txt_necesitas_herra": "You need the tool!",
        "txt_arbol_plantado": "Tree planted!",
        "txt_semilla_recogida": "Seed picked up",
        "txt_reparadas": "Repaired: ",
        "txt_e_key": "E",
        "txt_basura_recolectada": "Trash collected",
        "txt_basura_entregada": "Trash delivered!",
        "txt_basura_mano": "Trash in hands",
        "txt_recoger_e": "Pick up: E",
        "txt_depositar_e": "Deposit: E",
        "txt_entregadas": "Delivered:",
        "txt_parque_limpio": "Park cleaned!",
        "txt_park_hud_title": "Level 1 – The Park",
        "txt_calle_hud_title": "Level 2 – The Street",
        "txt_plaza_hud_title": "Level 3 – The Plaza",
        "txt_dificil_tiempo": "(Hard, timed)",
        "txt_facil_tiempo": "(Easy, timed)",
        
        # Textos específicos del Tutorial
        "txt_tutorial_msg1": "Trash collected! Take it to the bin.",
        "txt_tutorial_msg2": "SUCCESS! Next: Planting.",
        "txt_tutorial_msg3": "Seed collected. Plant it in the hole!",
        "txt_tutorial_msg4": "Planting started! Wait for the tree to grow.",
        "txt_tutorial_msg5": "Tree planted! REPAIR THE PLAZA. You have 50 s.",
        "txt_tutorial_msg6": "VICTORY! With effort and order, you transformed the city.",
        "txt_tutorial_msg7": "You already have a tool",
        "txt_tutorial_fail": "TIME'S UP! The city was not transformed.",
        "txt_tutorial_time": "TIME:",
        
        "txt_plantar_semilla": "Plant seed (E)",
        "txt_recoger_semilla": "Pick up seed (E)",
    }
}

def cambiar_idioma(nuevo_idioma):
    """Cambia el idioma global ('es' o 'us')."""
    global IDIOMA_ACTUAL
    # Parche de seguridad: si recibe 'en', lo tratamos como 'us'
    if nuevo_idioma == "en":
        nuevo_idioma = "us"
        
    if nuevo_idioma in TRADUCCIONES:
        IDIOMA_ACTUAL = nuevo_idioma
    else:
        print(f"[CONFIG] Intento de cambiar a idioma desconocido: {nuevo_idioma}")

def obtener_nombre(clave):
    """
    Devuelve el valor traducido desde config.py.
    """
    idioma = IDIOMA_ACTUAL
    
    # 1. Intentar obtener el texto del diccionario usando el idioma actual
    diccionario_idioma = TRADUCCIONES.get(idioma, TRADUCCIONES["es"])
    valor = diccionario_idioma.get(clave)
    
    # 2. Si encontramos el valor, lo devolvemos
    if valor is not None:
        return valor
        
    # 3. Si no existe la clave en el diccionario (quizás es un nombre de archivo dinámico)
    # y estamos en 'us', agregamos el sufijo.
    if idioma == "us" and not clave.endswith("us"):
        return clave + "us"
    
    # 4. Fallback: devolvemos la clave original
    return clave