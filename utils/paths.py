import os
import sys
from pathlib import Path


def get_app_dir() -> str:
    """Zwraca folder, w którym znajduje się plik .exe lub skrypt (dla settings.json i history.json)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(sys.argv[0]))


def get_ffmpeg_dir() -> str:
    """Zwraca ścieżkę do katalogu zawierającego ffmpeg.exe i ffprobe.exe."""
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    sub_ffmpeg = os.path.join(base_path, "ffmpeg")
    if os.path.isfile(os.path.join(sub_ffmpeg, "ffmpeg.exe")):
        return sub_ffmpeg
    if os.path.isfile(os.path.join(base_path, "ffmpeg.exe")):
        return base_path
    return "ffmpeg"


def get_default_download_dir() -> str:
    default_path = Path.home() / "Downloads" / "YouTube Downloader"
    default_path.mkdir(parents=True, exist_ok=True)
    return str(default_path)