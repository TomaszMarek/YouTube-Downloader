import os
import shutil
import time
from typing import Callable, Optional
from yt_dlp import YoutubeDL
from core.models import DownloadTask, QualityMode
from utils.paths import get_ffmpeg_dir


class DownloadCancelledException(Exception):
    pass


def _format_download_error(e: Exception) -> Exception:
    err_msg = str(e).lower()
    if "confirm your age" in err_msg or "age-restricted" in err_msg:
        return RuntimeError("Film wymaga ograniczenia wiekowego (+18).")
    if "not a bot" in err_msg or "sign in" in err_msg:
        return RuntimeError("Wymagane logowanie lub blokada YouTube.")
    if "private video" in err_msg:
        return RuntimeError("Film prywatny lub usunięty.")
    return e


def _extract_best_thumbnail(data: dict) -> str:
    if not data:
        return ""
    if data.get("thumbnail"):
        return data["thumbnail"]
    thumbnails = data.get("thumbnails")
    if thumbnails and isinstance(thumbnails, list):
        for thumb in reversed(thumbnails):
            if thumb and isinstance(thumb, dict) and thumb.get("url"):
                return thumb["url"]
    return ""


class DownloadEngine:
    def __init__(self, is_cancelled_check: Callable[[str], bool]):
        self._is_cancelled = is_cancelled_check
        self.ffmpeg_dir = get_ffmpeg_dir()

    def run(self, task: DownloadTask, on_progress: Callable[[dict], None]) -> Optional[dict]:
        if not os.path.exists(task.output_dir):
            try:
                os.makedirs(task.output_dir, exist_ok=True)
            except Exception as e:
                raise RuntimeError(f"Brak uprawnień do utworzenia katalogu: {e}")

        if not os.access(task.output_dir, os.W_OK):
            raise RuntimeError("Brak uprawnień do zapisu w folderze docelowym.")

        def progress_hook(d: dict):
            if self._is_cancelled(task.id):
                raise DownloadCancelledException("Zadanie anulowane.")
            on_progress(d)

        try:
            if task.is_playlist:
                return self._download_playlist(task, progress_hook)
            return self._download_single(task, progress_hook)
        except DownloadCancelledException:
            self._cleanup_temp_files(task)
            raise

    def _download_playlist(self, task: DownloadTask, progress_hook: Callable) -> Optional[dict]:
        flat_opts = {
            "extract_flat": True,
            "quiet": True,
            "no_warnings": True,
        }
        try:
            with YoutubeDL(flat_opts) as ydl:
                if self._is_cancelled(task.id):
                    raise DownloadCancelledException()
                playlist_dict = ydl.extract_info(task.url, download=False)
        except DownloadCancelledException:
            raise
        except Exception as e:
            raise _format_download_error(e)

        if not playlist_dict or "entries" not in playlist_dict:
            raise RuntimeError("Nie udało się pobrać spisu utworów z playlisty.")

        playlist_title = playlist_dict.get("title") or playlist_dict.get("playlist_title") or "Playlista"
        safe_title = "".join(c for c in playlist_title if c not in r'\/:*?"<>|').strip() or "Playlista"

        task.title = playlist_title
        album_dir = os.path.join(task.output_dir, safe_title)
        task.target_subdir = album_dir
        os.makedirs(album_dir, exist_ok=True)

        outtmpl = os.path.join(album_dir, "%(title).150B.%(ext)s")
        single_opts = self._build_single_options(task, progress_hook, outtmpl)

        thumb_url = _extract_best_thumbnail(playlist_dict)
        raw_entries = [e for e in playlist_dict["entries"] if e]

        if not thumb_url and raw_entries:
            thumb_url = _extract_best_thumbnail(raw_entries[0])
            if not thumb_url and raw_entries[0].get("id"):
                thumb_url = f"https://i.ytimg.com/vi/{raw_entries[0]['id']}/hqdefault.jpg"

        task.thumbnail_url = thumb_url

        if task.playlist_items:
            allowed = {int(x.strip()) for x in task.playlist_items.split(",") if x.strip().isdigit()}
            entries = [e for idx, e in enumerate(raw_entries, start=1) if idx in allowed]
        else:
            entries = raw_entries

        task.skipped_items.clear()

        for idx, entry in enumerate(entries, start=1):
            if self._is_cancelled(task.id):
                raise DownloadCancelledException()

            video_url = entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
            entry_title = entry.get("title", f"Pozycja #{idx}")

            try:
                with YoutubeDL(single_opts) as ydl:
                    ydl.extract_info(video_url, download=True)
            except DownloadCancelledException:
                raise
            except Exception:
                task.skipped_items.append(entry_title)

        if task.skipped_items and len(task.skipped_items) == len(entries):
            raise RuntimeError("Wszystkie pozycje z playlisty zostały zablokowane lub wymagają logowania.")

        return playlist_dict

    def _download_single(self, task: DownloadTask, progress_hook: Callable) -> Optional[dict]:
        outtmpl = os.path.join(task.output_dir, "%(title).150B.%(ext)s")
        ydl_opts = self._build_single_options(task, progress_hook, outtmpl)

        try:
            with YoutubeDL(ydl_opts) as ydl:
                if self._is_cancelled(task.id):
                    raise DownloadCancelledException()
                info = ydl.extract_info(task.url, download=True)
                if info:
                    task.thumbnail_url = _extract_best_thumbnail(info)
                    if info.get("title"):
                        task.title = info.get("title")
                return info
        except DownloadCancelledException:
            raise
        except Exception as e:
            raise _format_download_error(e)

    def _cleanup_temp_files(self, task: DownloadTask):
        if task.is_playlist and task.target_subdir and os.path.exists(task.target_subdir):
            for _ in range(3):
                try:
                    shutil.rmtree(task.target_subdir)
                    return
                except Exception:
                    time.sleep(0.3)
        else:
            try:
                for f in os.listdir(task.output_dir):
                    if f.endswith((".part", ".ytdl")) or ".temp." in f:
                        file_path = os.path.join(task.output_dir, f)
                        if os.path.isfile(file_path):
                            for _ in range(3):
                                try:
                                    os.remove(file_path)
                                    break
                                except Exception:
                                    time.sleep(0.3)
            except Exception:
                pass

    def _build_single_options(self, task: DownloadTask, progress_hook: Callable, outtmpl: str) -> dict:
        postprocessors = []

        if task.mode == QualityMode.MP3:
            format_str = "ba/b"
            postprocessors.extend([
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
                {"key": "EmbedThumbnail", "already_have_thumbnail": False},
            ])
        else:
            format_map = {
                QualityMode.BEST: "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
                QualityMode.Q2160P: "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best",
                QualityMode.Q1440P: "bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1440]+bestaudio/best",
                QualityMode.Q1080P: "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best",
                QualityMode.Q720P: "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best",
                QualityMode.Q480P: "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best",
            }
            format_str = format_map.get(task.mode, "bestvideo+bestaudio/best")
            postprocessors.extend([
                {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
                {"key": "EmbedThumbnail", "already_have_thumbnail": False},
            ])

        return {
            "noplaylist": True,
            "writethumbnail": True,
            "format": format_str,
            "outtmpl": outtmpl,
            "windowsfilenames": True,
            "merge_output_format": "mp4" if task.mode != QualityMode.MP3 else None,
            "postprocessors": postprocessors,
            "progress_hooks": [progress_hook],
            "ffmpeg_location": self.ffmpeg_dir,
            "concurrent_fragment_downloads": 4,
            "cachedir": False,
            "retries": 5,
            "quiet": True,
            "no_warnings": True,
        }