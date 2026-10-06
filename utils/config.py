import json
import os
from typing import Any, Dict
from utils.paths import get_default_download_dir
from utils.paths import get_app_dir

CONFIG_FILE_NAME = "settings.json"

def get_config_path() -> str:
    """Zwraca ścieżkę do pliku settings.json obok pliku wykonywalnego/skryptu."""
    return os.path.join(get_app_dir(), CONFIG_FILE_NAME)

def get_default_settings() -> Dict[str, Any]:
    """Domyślne ustawienia programu."""
    return {
        "download_dir": get_default_download_dir(),
        "default_mode": "Najlepsza (Automatyczna)",
        "download_type": "single",
    }


def load_settings() -> Dict[str, Any]:
    """Wczytuje ustawienia z pliku settings.json z bezpiecznym fallbackiem."""
    path = get_config_path()
    defaults = get_default_settings()

    if not os.path.exists(path):
        save_settings(defaults)
        return defaults

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Uzupełnienie ewentualnych brakujących kluczy z defaults
            for key, value in defaults.items():
                if key not in data:
                    data[key] = value
            return data
    except Exception:
        return defaults


def save_settings(settings: Dict[str, Any]) -> None:
    """Zapisuje słownik ustawień do settings.json."""
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
    except Exception:
        pass