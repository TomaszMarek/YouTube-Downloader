import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

from core.downloader import DownloadCancelledException, DownloadEngine
from core.events import EventBus
from core.models import DownloadStatus, DownloadTask, QualityMode, TaskEvent
from utils.formatters import normalize_resolution_label
from utils.history import add_history_entry


def _format_track_count(n: int) -> str:
    if n == 1:
        return "1 utwór"
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return f"{n} utwory"
    return f"{n} utworów"


class QueueManager:
    def __init__(self, event_bus: EventBus, max_concurrent_downloads: int = 2):
        self.event_bus = event_bus
        self.tasks: Dict[str, DownloadTask] = {}
        self.cancelled_task_ids = set()
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_downloads)
        self.engine = DownloadEngine(is_cancelled_check=self.is_task_cancelled)
        self._lock = threading.Lock()

    def add_task(
        self,
        url: str,
        output_dir: str,
        mode: QualityMode,
        is_playlist: bool = False,
        playlist_items: str | None = None,
    ) -> DownloadTask:
        task_id = str(uuid.uuid4())
        task = DownloadTask(
            id=task_id,
            url=url,
            output_dir=output_dir,
            mode=mode,
            is_playlist=is_playlist,
            playlist_items=playlist_items,
        )
        self.tasks[task_id] = task
        self.event_bus.emit(TaskEvent(task_id=task.id, event_type="task_added", task=task))
        self.executor.submit(self._worker, task)
        return task

    def cancel_task(self, task_id: str):
        with self._lock:
            self.cancelled_task_ids.add(task_id)
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status == DownloadStatus.WAITING:
                    task.status = DownloadStatus.CANCELLED
                    self.event_bus.emit(TaskEvent(task_id=task.id, event_type="cancelled", task=task))

    def is_task_cancelled(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self.cancelled_task_ids

    def remove_task(self, task_id: str):
        with self._lock:
            self.tasks.pop(task_id, None)
            self.cancelled_task_ids.discard(task_id)

    def _worker(self, task: DownloadTask):
        task.status = DownloadStatus.DOWNLOADING
        self.event_bus.emit(TaskEvent(task_id=task.id, event_type="started", task=task))

        downloaded_items_counter = 0
        last_seen_title = None
        total_items = len(task.playlist_items.split(",")) if task.playlist_items else None

        def on_progress(d: dict):
            nonlocal downloaded_items_counter, last_seen_title, total_items
            status = d.get("status")

            if status == "downloading":
                task.status = DownloadStatus.DOWNLOADING
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                task.downloaded_bytes = downloaded
                task.total_bytes = total
                if total > 0:
                    task.progress = downloaded / total
                task.speed = d.get("speed") or 0.0
                task.eta = d.get("eta") or 0

                info_dict = d.get("info_dict", {})
                current_title = info_dict.get("title")

                if total_items is None and task.is_playlist:
                    total_items = (
                        info_dict.get("playlist_count")
                        or info_dict.get("playlist_n_entries")
                        or info_dict.get("n_entries")
                    )

                if current_title and current_title != last_seen_title:
                    last_seen_title = current_title
                    downloaded_items_counter += 1

                if current_title:
                    if task.is_playlist:
                        cnt_str = f"/{total_items}" if total_items else ""
                        task.title = f"[{downloaded_items_counter}{cnt_str}] {current_title}"
                    else:
                        task.title = current_title

                self.event_bus.emit(TaskEvent(task_id=task.id, event_type="progress", task=task))

            elif status == "finished":
                self.event_bus.emit(TaskEvent(task_id=task.id, event_type="processing", task=task))

        try:
            info = self.engine.run(task, on_progress)
            task.status = DownloadStatus.COMPLETED

            if info:
                extracted_title = info.get("title") or info.get("playlist_title")
                if extracted_title and task.title == "Pobieranie metadanych...":
                    task.title = extracted_title

            if task.downloaded_bytes == 0 and not task.skipped_items:
                task.progress = 1.0
                task.error_message = "ALREADY_EXISTS"
                self.event_bus.emit(TaskEvent(task_id=task.id, event_type="completed_already_exists", task=task))
                return

            target_path = task.target_subdir if (task.is_playlist and task.target_subdir) else task.output_dir

            if task.is_playlist:
                playlist_name = (
                    info.get("playlist_title")
                    or info.get("title")
                    or (os.path.basename(task.target_subdir) if task.target_subdir else "Playlista")
                )
                actual_count = 0
                if task.target_subdir and os.path.exists(task.target_subdir):
                    media_exts = (".mp4", ".mkv", ".webm", ".mp3", ".m4a")
                    actual_count = sum(
                        1 for f in os.listdir(task.target_subdir)
                        if f.lower().endswith(media_exts) and not f.endswith((".part", ".ytdl"))
                    )

                if actual_count > 0:
                    history_title = f"{playlist_name} ({_format_track_count(actual_count)})"
                else:
                    dl_cnt = info.get("downloaded_count", 0) if info else 0
                    history_title = f"{playlist_name} ({_format_track_count(dl_cnt)})" if dl_cnt else playlist_name

                task.title = history_title
            else:
                history_title = task.title

            actual_width = None
            actual_height = None
            if info:
                if info.get("height"):
                    actual_width = info.get("width")
                    actual_height = info.get("height")
                elif task.is_playlist and "entries" in info and info["entries"]:
                    first_valid = next((e for e in info["entries"] if e and e.get("height")), None)
                    if first_valid:
                        actual_width = first_valid.get("width")
                        actual_height = first_valid.get("height")

            detected_label = normalize_resolution_label(actual_width, actual_height)

            if task.mode == QualityMode.MP3:
                saved_quality = "MP3"
            elif detected_label != "Nieznana":
                saved_quality = detected_label
            else:
                saved_quality = task.mode.value

            add_history_entry(
                title=history_title,
                url=task.url,
                mode=saved_quality,
                output_dir=target_path,
                is_playlist=task.is_playlist,
                thumbnail_url=task.thumbnail_url,
            )

            if task.skipped_items:
                if len(task.skipped_items) <= 2:
                    titles = ", ".join(f'"{t}"' for t in task.skipped_items)
                    task.error_message = f"Pominięto (zablokowane): {titles}"
                else:
                    first_two = ", ".join(f'"{t}"' for t in task.skipped_items[:2])
                    rem = len(task.skipped_items) - 2
                    task.error_message = f"Pominięto (zablokowane): {first_two} i {rem} inne"

                self.event_bus.emit(TaskEvent(task_id=task.id, event_type="completed_with_warning", task=task))
            else:
                requested_mode = task.mode.value
                expected_height = None
                if "p" in requested_mode:
                    try:
                        expected_height = int(requested_mode.split("(")[-1].replace("p)", "").replace("p", "").strip())
                    except ValueError:
                        pass

                actual_equiv_height = None
                if "p" in detected_label:
                    try:
                        actual_equiv_height = int(detected_label.replace("p", "").strip())
                    except ValueError:
                        pass

                if expected_height and actual_equiv_height and actual_equiv_height < expected_height:
                    task.error_message = f"Brak {expected_height}p. Pobrano: {detected_label}"
                    self.event_bus.emit(TaskEvent(task_id=task.id, event_type="completed_with_warning", task=task))
                else:
                    self.event_bus.emit(TaskEvent(task_id=task.id, event_type="completed", task=task))

        except DownloadCancelledException:
            task.status = DownloadStatus.CANCELLED
            self.event_bus.emit(TaskEvent(task_id=task.id, event_type="cancelled", task=task))
        except Exception as e:
            task.status = DownloadStatus.FAILED
            task.error_message = str(e)[:100]
            self.event_bus.emit(TaskEvent(task_id=task.id, event_type="error", task=task))

    def shutdown(self):
        self.executor.shutdown(wait=False, cancel_futures=True)