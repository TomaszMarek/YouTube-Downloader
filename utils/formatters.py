import re

YOUTUBE_URL_REGEX = re.compile(
    r'^(https?://)?(www\.|m\.)?(youtube\.com/(watch\?|playlist\?|shorts/)|youtu\.be/).+$'
)


def is_valid_youtube_url(url: str) -> bool:
    if not url:
        return False
    url = url.strip()
    return bool(YOUTUBE_URL_REGEX.match(url))


def format_bytes(size: float) -> str:
    if not size:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while size >= 1024 and idx < len(units) - 1:
        size /= 1024
        idx += 1
    return f"{size:.2f} {units[idx]}"


def format_speed(bytes_per_sec: float) -> str:
    if not bytes_per_sec:
        return "0 MB/s"
    return f"{format_bytes(bytes_per_sec)}/s"


def format_seconds(seconds: float | int | None) -> str:
    if seconds is None or seconds < 0:
        return "--:--"

    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    mins, secs = divmod(remainder, 60)

    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def normalize_resolution_label(width: int | None, height: int | None) -> str:
    """
    Zwraca etykietę rozdzielczości z uwzględnieniem formatów panoramicznych/kinowych (np. 21:9, 2.40:1).
    """
    if not height:
        return "Nieznana"

    # 480p (standard 854x480, panorama np. 854x356)
    if (width and 800 <= width < 1200) or (350 <= height <= 480):
        return "480p"
    # 720p (standard 1280x720, panorama np. 1280x534)
    if (width and 1200 <= width < 1900) or (530 <= height <= 720):
        return "720p"
    # 1080p (standard 1920x1080, panorama np. 1920x800)
    if (width and 1900 <= width < 2500) or (800 <= height <= 1080):
        return "1080p"
    # 1440p (standard 2560x1440, panorama np. 2560x1066)
    if (width and 2500 <= width < 3800) or (1060 <= height <= 1440):
        return "1440p"
    # 2160p (standard 3840x2160, panorama np. 3840x1600)
    if (width and width >= 3800) or (height >= 1600):
        return "2160p"

    return f"{height}p"