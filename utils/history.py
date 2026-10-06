import json
import os
from datetime import datetime
from typing import Any, Dict, List
from utils.paths import get_app_dir

HISTORY_FILE_NAME = "history.json"
MAX_HISTORY_ITEMS = 200


def get_history_path() -> str:
    """Zwraca ścieżkę do pliku history.json obok pliku wykonywalnego/skryptu."""
    return os.path.join(get_app_dir(), HISTORY_FILE_NAME)


def load_history() -> List[Dict[str, Any]]:
    """Wczytuje listę wpisów historii pobrań."""
    path = get_history_path()
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []


def save_history(history: List[Dict[str, Any]]) -> None:
    """Zapisuje zaktualizowaną listę historii do pliku JSON."""
    path = get_history_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except Exception:
        pass


def add_history_entry( title: str, url: str, mode: str, output_dir: str, is_playlist: bool = False, thumbnail_url: str = "",) -> None:
    """Dodaje nowy wpis na początek historii pobrań z zachowaniem limitu wpisów."""
    history = load_history()

    new_entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "title": title,
        "url": url,
        "mode": mode,
        "output_dir": output_dir,
        "is_playlist": is_playlist,
        "thumbnail_url": thumbnail_url,
    }

    # Nowe wpisy trafiają na początek listy (najnowsze u góry)
    history.insert(0, new_entry)

    # Obcięcie listy do ustalonego limitu (FIFO)
    if len(history) > MAX_HISTORY_ITEMS:
        history = history[:MAX_HISTORY_ITEMS]

    save_history(history)

def clear_history() -> None:
    """Czyści całą historię pobrań."""
    save_history([])