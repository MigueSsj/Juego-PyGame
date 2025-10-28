# audio_shared.py
from __future__ import annotations
import pygame
from pathlib import Path

# ===== Config =====
_DEFAULT_VOL = 0.6
_CLICK_STEMS = ["musica_botoncitos", "click", "boton"]
_MUSIC_STEMS = ["musica inicio", "musica_inicio", "inicio"]

_click_snd: pygame.mixer.Sound | None = None

# ---------- utils volumen (archivo de texto) ----------
def _vol_path(assets_dir: Path) -> Path:
    # Guarda en la raíz del proyecto, al lado de assets/
    return assets_dir.parent / "volume.txt"

def load_master_volume(assets_dir: Path) -> float:
    try:
        p = _vol_path(assets_dir)
        if p.exists():
            v = float(p.read_text(encoding="utf-8").strip())
            return max(0.0, min(1.0, v))
    except Exception:
        pass
    return _DEFAULT_VOL

def save_master_volume(assets_dir: Path, v: float) -> None:
    v = max(0.0, min(1.0, float(v)))
    try:
        _vol_path(assets_dir).write_text(f"{v:.3f}", encoding="utf-8")
    except Exception:
        pass

# ---------- helpers audio ----------
def _find_audio(assets_dir: Path, stems: list[str], exts=(".ogg",".wav",".mp3")) -> Path | None:
    audio_dir = assets_dir / "msuiquita"
    if not audio_dir.exists(): return None
    # exacto
    for st in stems:
        for ext in exts:
            p = audio_dir / f"{st}{ext}"
            if p.exists(): return p
    # prefijo
    for st in stems:
        for ext in exts:
            cands = sorted(audio_dir.glob(f"{st}*{ext}"), key=lambda p: len(p.name))
            if cands: return cands[0]
    return None

def _ensure_mixer():
    if not pygame.mixer.get_init():
        pygame.mixer.init()

# ---------- música ----------
def start_menu_music(assets_dir: Path) -> None:
    """Arranca la música de menú al volumen maestro actual."""
    try:
        p = _find_audio(assets_dir, _MUSIC_STEMS)
        if not p:
            return
        _ensure_mixer()
        pygame.mixer.music.load(str(p))
        pygame.mixer.music.set_volume(load_master_volume(assets_dir))
        pygame.mixer.music.play(-1)
    except Exception:
        pass

def ensure_menu_music_running(assets_dir: Path) -> None:
    try:
        if not pygame.mixer.get_init() or not pygame.mixer.music.get_busy():
            start_menu_music(assets_dir)
        else:
            pygame.mixer.music.set_volume(load_master_volume(assets_dir))
    except Exception:
        pass

def set_music_volume_now(assets_dir: Path, v: float) -> None:
    """Ajusta y guarda el volumen maestro; aplica a la música si está sonando."""
    save_master_volume(assets_dir, v)
    try:
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(v)
    except Exception:
        pass

# ---------- click ----------
def _ensure_click_loaded(assets_dir: Path):
    global _click_snd
    if _click_snd is not None:
        return
    try:
        p = _find_audio(assets_dir, _CLICK_STEMS)
        if not p:
            return
        _ensure_mixer()
        _click_snd = pygame.mixer.Sound(str(p))
    except Exception:
        _click_snd = None

def play_click(assets_dir: Path):
    """Reproduce el click usando SIEMPRE el volumen maestro actual."""
    try:
        _ensure_click_loaded(assets_dir)
        if _click_snd:
            _click_snd.set_volume(load_master_volume(assets_dir))
            _click_snd.play()
    except Exception:
        pass
