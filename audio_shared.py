from __future__ import annotations
import pygame, os
from pathlib import Path

# ---------- util rutas ----------
def _find_audio(assets_dir: Path, stems: list[str]) -> Path | None:
    audio_dir = assets_dir / "msuiquita"
    if not audio_dir.exists():
        return None
    for stem in stems:
        for ext in (".ogg", ".wav", ".mp3"):
            # match exact y con sufijos
            for p in list(audio_dir.glob(f"{stem}{ext}")) + list(audio_dir.glob(f"{stem}*{ext}")):
                return p
    return None

# ---------- persistencia volumen maestro (0..1) ----------
def _vol_path(assets_dir: Path) -> Path:
    # ya usabas esto desde opciones.py
    return assets_dir.parent / "volume.txt"

def load_master_volume(assets_dir: Path) -> float:
    try:
        p = _vol_path(assets_dir)
        if p.exists():
            v = float(p.read_text(encoding="utf-8").strip())
            return max(0.0, min(1.0, v))
    except Exception:
        pass
    return 0.7

def save_master_volume(assets_dir: Path, v: float) -> None:
    try:
        _vol_path(assets_dir).write_text(str(max(0.0, min(1.0, float(v)))), encoding="utf-8")
    except Exception:
        pass

# ---------- mixer ----------
def _ensure_mixer():
    if not pygame.mixer.get_init():
        pygame.mixer.pre_init(44100, -16, 2, 256)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(24)

# ---------- Música de menú ----------
_menu_loaded_src: str | None = None
_menu_music_path: Path | None = None # Cache para el path de la música de menú

def start_menu_music(assets_dir: Path) -> None:
    """Inicia música de menú en loop respetando volumen maestro."""
    global _menu_loaded_src, _menu_music_path
    try:
        _ensure_mixer()
        vol = load_master_volume(assets_dir)
        pygame.mixer.music.set_volume(vol)

        # Carga el path de la música de menú si aún no se ha cargado
        if _menu_music_path is None:
            cand = _find_audio(assets_dir, [
                "musica inicio", # <--- ¡AÑADIDO!
                "musica_menu", "menu_music", "bg_menu", "fondo_menu", "musica_inicio"
            ])
            if cand is None:
                print(f"ADVERTENCIA: No se encontró el archivo de música de menú (ej. 'musica inicio.mp3') en {assets_dir / 'msuiquita'}")
                return
            _menu_music_path = cand
        
        # === CAMBIO: Lógica de reproducción forzada ===
        # Si la música cargada no es la de menú, cárgala y reprodúcela
        if _menu_loaded_src != str(_menu_music_path):
            pygame.mixer.music.load(str(_menu_music_path))
            _menu_loaded_src = str(_menu_music_path)
            pygame.mixer.music.play(-1, fade_ms=300) # Forzar reproducción
        
        # Si es la música correcta pero no está sonando, reprodúcela
        elif not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(-1, fade_ms=300)

        # Limpia los 'trackers' de música de nivel
        global _level_music_loaded_src, _suspense_music_loaded_src
        _level_music_loaded_src = None
        _suspense_music_loaded_src = None
    except Exception:
        pass


def ensure_menu_music_running(assets_dir: Path) -> None:
    """Asegura que la música de menú esté sonando (llamado al volver de un nivel)."""
    # === CAMBIO: Esta función ahora llama a start_menu_music ===
    # start_menu_music es lo suficientemente inteligente como para saber si debe
    # forzar la carga (si viene de un nivel) o simplemente reanudar.
    start_menu_music(assets_dir)

def set_music_volume_now(assets_dir: Path, v: float) -> None:
    """Ajusta en caliente el volumen de la música y lo mantiene en la sesión."""
    try:
        _ensure_mixer()
        v = max(0.0, min(1.0, float(v)))
        pygame.mixer.music.set_volume(v)
    except Exception:
        pass

# ================================================================
# === FUNCIONES DE MÚSICA PARA NIVELES (SIN CAMBIOS) ===
# (Buscando 'frantic_gameplay_v001' y 'a2')
# ================================================================

_level_music_loaded_src: str | None = None
_suspense_music_loaded_src: str | None = None

def start_level_music(assets_dir: Path) -> None:
    """Carga y reproduce la música de gameplay 'frantic'."""
    try:
        _ensure_mixer()
        vol = load_master_volume(assets_dir)
        pygame.mixer.music.set_volume(vol)
        
        global _level_music_loaded_src
        # Busca 'frantic_gameplay_v001.ogg' o similares
        cand = _find_audio(assets_dir, ["frantic_gameplay_v001", "frantic", "level_music"])
        if cand is None:
            print(f"ADVERTENCIA: No se encontró 'frantic_gameplay_v001.ogg' en {assets_dir / 'msuiquita'}")
            return
        
        # Solo carga si es una canción diferente a la actual
        global _menu_loaded_src
        if _level_music_loaded_src != str(cand):
            pygame.mixer.music.load(str(cand))
            _level_music_loaded_src = str(cand)
            _menu_loaded_src = str(cand) # Marcar como cargada
        
        # Resetea la música de suspenso
        global _suspense_music_loaded_src
        _suspense_music_loaded_src = None 
        
        pygame.mixer.music.play(-1, fade_ms=500)
    except Exception as e:
        print(f"Error al iniciar música de nivel: {e}")

def start_suspense_music(assets_dir: Path) -> None:
    """Carga y reproduce la música de suspenso 'a2'."""
    try:
        _ensure_mixer()
        vol = load_master_volume(assets_dir)
        pygame.mixer.music.set_volume(vol)
        
        global _suspense_music_loaded_src
        # Busca 'a2.mp3' o similares
        cand = _find_audio(assets_dir, ["a2", "suspense", "timer_low"])
        if cand is None:
            print(f"ADVERTENCIA: No se encontró 'a2.mp3' en {assets_dir / 'msuiquita'}")
            return
        
        # Solo carga si es una canción diferente
        global _menu_loaded_src
        if _suspense_music_loaded_src != str(cand):
            pygame.mixer.music.load(str(cand))
            _suspense_music_loaded_src = str(cand)
            _menu_loaded_src = str(cand) # Marcar como cargada
        
        # Resetea la música de nivel
        global _level_music_loaded_src
        _level_music_loaded_src = None 

        pygame.mixer.music.play(-1, fade_ms=500)
    except Exception as e:
        print(f"Error al iniciar música de suspenso: {e}")

def stop_level_music() -> None:
    """Detiene la música del nivel (usado al salir al menú)."""
    try:
        if pygame.mixer.get_init():
            # Mantenemos el fadeout, la nueva lógica de start_menu_music lo anulará
            pygame.mixer.music.fadeout(500)
        global _level_music_loaded_src, _suspense_music_loaded_src
        _level_music_loaded_src = None
        _suspense_music_loaded_src = None
    except Exception:
        pass

# ================================================================
# === FIN DE LAS FUNCIONES AÑADIDAS ===
# ================================================================


# ---------- Banco SFX ----------
_sfx_cache: dict[str, pygame.mixer.Sound] = {}
_sfx_volume: float = -1.0  # -1.0 significa que debe leerse desde load_master_volume

# keys → posibles nombres de archivo
_SFX_STEMS = {
    "back":   ["btn_back", "back", "regresar"],
    "select": ["musica_botoncitos", "click", "boton", "btn_select", "select"],
    "easy":   ["modo_facil", "btn_facil", "facil"],
    "hard":   ["modo_dificil", "btn_dificil", "dificil"],
}

def _get_sfx_volume(assets_dir: Path) -> float:
    """Obtiene el volumen SFX, inicializándolo desde el master si es necesario."""
    global _sfx_volume
    if _sfx_volume == -1.0:
        # Si es la primera vez que se usa, cárgalo desde el archivo
        _sfx_volume = load_master_volume(assets_dir)
    return _sfx_volume

def _load_sfx_key(key: str, assets_dir: Path) -> pygame.mixer.Sound | None:
    if key in _sfx_cache:
        return _sfx_cache[key]
    stems = _SFX_STEMS.get(key, [])
    p = _find_audio(assets_dir, stems)
    if p is None:
        return None
    try:
        _ensure_mixer()
        snd = pygame.mixer.Sound(str(p))
        snd.set_volume(_get_sfx_volume(assets_dir))
        _sfx_cache[key] = snd
        return snd
    except Exception:
        return None

def set_sfx_volume_now(assets_dir: Path, v: float) -> None:
    """Ajusta el volumen de todos los SFX cacheados y sincroniza con maestro."""
    try:
        global _sfx_volume
        _sfx_volume = max(0.0, min(1.0, float(v)))
        # aplica a los ya cargados
        for snd in _sfx_cache.values():
            try: snd.set_volume(_sfx_volume)
            except Exception: pass
    except Exception:
        pass

def play_sfx(key: str, assets_dir: Path) -> None:
    """Reproduce un SFX mapeado ('back'|'select'|'easy'|'hard')."""
    try:
        snd = _load_sfx_key(key, assets_dir)
        if snd:
            snd.set_volume(_get_sfx_volume(assets_dir))  # Asegura el volumen actual
            snd.play()
    except Exception:
        pass

# Compat con tu código existente
def play_click(assets_dir: Path) -> None:
    """Alias legacy: usar el SFX 'select'."""
    play_sfx("select", assets_dir)