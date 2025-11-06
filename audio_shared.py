# audio_shared.py
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

def start_menu_music(assets_dir: Path) -> None:
    """Inicia música de menú en loop respetando volumen maestro."""
    try:
        _ensure_mixer()
        vol = load_master_volume(assets_dir)
        pygame.mixer.music.set_volume(vol)

        # =====================================================================
        # === ¡¡AQUÍ ESTÁ LA CORRECCIÓN!! ===
        # Añadí "musica inicio" (con espacio) a la lista.
        # =====================================================================
        cand = _find_audio(assets_dir, [
            "musica inicio", # <--- ¡AÑADIDO!
            "musica_menu", "menu_music", "bg_menu", "fondo_menu", "musica_inicio"
        ])
        
        if cand is None:
            # Si sigue sin encontrarla, imprime un aviso
            print(f"ADVERTENCIA: No se encontró el archivo de música de menú (ej. 'musica inicio.mp3') en {assets_dir / 'msuiquita'}")
            return
            
        global _menu_loaded_src
        if _menu_loaded_src != str(cand):
            pygame.mixer.music.load(str(cand))
            _menu_loaded_src = str(cand)
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(-1)
    except Exception:
        pass

def ensure_menu_music_running(assets_dir: Path) -> None:
    """Si la música no suena, volver a iniciarla."""
    try:
        if not pygame.mixer.get_init():
            start_menu_music(assets_dir); return
        if not pygame.mixer.music.get_busy():
            start_menu_music(assets_dir)
    except Exception:
        pass

def set_music_volume_now(assets_dir: Path, v: float) -> None:
    """Ajusta en caliente el volumen de la música y lo mantiene en la sesión."""
    try:
        _ensure_mixer()
        v = max(0.0, min(1.0, float(v)))
        pygame.mixer.music.set_volume(v)
    except Exception:
        pass

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