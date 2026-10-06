from enum import Enum
from typing import Optional
from dataclasses import dataclass, field

class DownloadStatus(Enum):
    WAITING = "Oczekuje w kolejce"
    DOWNLOADING = "Pobieranie"
    PROCESSING = "Scalanie (FFmpeg)"
    COMPLETED = "Zakończono"
    CANCELLED = "Anulowano"
    FAILED = "Błąd"


class QualityMode(Enum):
    BEST = "Najwyższa (Auto)"
    Q2160P = "4K (2160p)"
    Q1440P = "2K (1440p)"
    Q1080P = "1080p"
    Q720P = "720p"
    Q480P = "480p"
    MP3 = "Audio (MP3)"


@dataclass
class DownloadTask:
    id: str
    url: str
    output_dir: str
    mode: QualityMode
    is_playlist: bool = False
    status: DownloadStatus = DownloadStatus.WAITING
    title: str = "Pobieranie metadanych..."
    progress: float = 0.0
    speed: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    eta: Optional[int] = None
    error_message: Optional[str] = None
    target_subdir: Optional[str] = None
    thumbnail_url: str = ""
    playlist_items: Optional[str] = None
    skipped_items: list[str] = field(default_factory=list)


@dataclass
class TaskEvent:
    task_id: str
    event_type: str
    task: Optional[DownloadTask] = None
    data: Optional[dict] = None