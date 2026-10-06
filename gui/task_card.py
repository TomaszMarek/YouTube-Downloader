import os
import threading
from typing import Callable
from urllib.request import Request, urlopen
import customtkinter as ctk
from PIL import Image

from core.models import DownloadStatus, DownloadTask
from utils.formatters import format_bytes, format_seconds, format_speed


class TaskCard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        task: DownloadTask,
        on_cancel: Callable[[str], None],
        on_remove: Callable[[str], None],
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color="#181C24",
            corner_radius=8,
            border_width=1,
            border_color="#242B35",
            **kwargs,
        )
        self.task_id = task.id
        self.output_dir = task.output_dir
        self.on_cancel = on_cancel
        self.on_remove = on_remove
        self.thumbnail_loaded = False
        self.pack(fill="x", padx=4, pady=4)

        self.thumb_lbl = ctk.CTkLabel(
            self,
            text="",
            width=106,
            height=60,
            fg_color="#101318",
            corner_radius=6,
        )
        self.thumb_lbl.pack(side="left", padx=(10, 8), pady=10)
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=8)

        self.title_lbl = ctk.CTkLabel(
            self.content_frame,
            text=task.title,
            font=("Segoe UI", 12, "bold"),
            text_color="#ECEFF4",
            anchor="w",
        )
        self.title_lbl.pack(fill="x", pady=(0, 4))

        self.progress_bar = ctk.CTkProgressBar(
            self.content_frame,
            height=6,
            fg_color="#101318",
            progress_color="#2563EB",
            corner_radius=3,
        )
        self.progress_bar.pack(fill="x", pady=(0, 6))
        self.progress_bar.set(0)
        self.bottom_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.bottom_frame.pack(fill="x")

        self.status_lbl = ctk.CTkLabel(
            self.bottom_frame,
            text=task.status.value,
            font=("Segoe UI", 11),
            text_color="#8B9BB4",
            anchor="w",
        )
        self.status_lbl.pack(side="left", fill="x", expand=True)

        self.delete_btn = ctk.CTkButton(
            self.bottom_frame,
            text="Usuń",
            width=58,
            height=24,
            font=("Segoe UI", 10),
            fg_color="#1E222A",
            text_color="#4C566A",
            corner_radius=4,
            command=self._handle_remove,
            state="disabled",
        )
        self.delete_btn.pack(side="right", padx=(4, 0))

        self.cancel_btn = ctk.CTkButton(
            self.bottom_frame,
            text="Anuluj",
            width=58,
            height=24,
            font=("Segoe UI", 10),
            fg_color="#7A2828",
            hover_color="#963232",
            text_color="#FFFFFF",
            corner_radius=4,
            command=self._handle_cancel,
        )
        self.cancel_btn.pack(side="right", padx=(4, 0))

        self.open_btn = ctk.CTkButton(
            self.bottom_frame,
            text="Folder",
            width=58,
            height=24,
            font=("Segoe UI", 10),
            fg_color="#212732",
            hover_color="#2D3544",
            text_color="#ECEFF4",
            corner_radius=4,
            command=self._open_folder,
            state="disabled",
        )
        self.open_btn.pack(side="right")

        if getattr(task, "thumbnail_url", None):
            self._load_thumbnail_async(task.thumbnail_url)

    def _load_thumbnail_async(self, url: str):
        if not url or self.thumbnail_loaded:
            return

        def _worker():
            try:
                req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urlopen(req, timeout=4) as response:
                    img = Image.open(response)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(106, 60))
                self.after(0, lambda: self._apply_thumbnail(ctk_img))
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_thumbnail(self, ctk_img: ctk.CTkImage):
        self.thumbnail_loaded = True
        self.thumb_lbl.configure(image=ctk_img, text="")

    def _open_folder(self):
        if os.path.exists(self.output_dir):
            os.startfile(self.output_dir)

    def _handle_cancel(self):
        self.cancel_btn.configure(
            state="disabled",
            fg_color="#181C24",
            text_color="#364050",
        )
        self.status_lbl.configure(text="Anulowanie...", text_color="#EBCB8B")
        if self.on_cancel:
            self.on_cancel(self.task_id)

    def _handle_remove(self):
        self.on_remove(self.task_id)
        self.destroy()

    def _set_terminal_buttons(self):
        self.cancel_btn.configure(
            state="disabled",
            fg_color="#181C24",
            text_color="#364050",
        )
        self.delete_btn.configure(
            state="normal",
            fg_color="#7F1D1D",
            hover_color="#991B1B",
            text_color="#FFFFFF",
        )

    def render(self, task: DownloadTask):
        self.title_lbl.configure(text=task.title)
        self.progress_bar.set(task.progress)

        if not self.thumbnail_loaded and getattr(task, "thumbnail_url", None):
            self._load_thumbnail_async(task.thumbnail_url)

        if task.status == DownloadStatus.DOWNLOADING:
            pct = task.progress * 100
            spd = format_speed(task.speed)
            dl_sz = format_bytes(task.downloaded_bytes)
            tot_sz = format_bytes(task.total_bytes)
            status_text = f"{pct:.1f}%  •  {spd}  •  {dl_sz} / {tot_sz}"
            self.status_lbl.configure(text=status_text, text_color="#D8DEE9")

            self.open_btn.configure(
                state="normal",
                fg_color="#212732",
                hover_color="#2D3544",
                text_color="#ECEFF4",
            )
            self.cancel_btn.configure(
                state="normal",
                fg_color="#7A2828",
                hover_color="#963232",
                text_color="#FFFFFF",
            )
            self.delete_btn.configure(
                state="disabled",
                fg_color="#1E222A",
                text_color="#4C566A",
            )

        elif task.status == DownloadStatus.PROCESSING:
            self.status_lbl.configure(text="Scalanie strumieni (FFmpeg)...", text_color="#EBCB8B")
            self.open_btn.configure(
                state="normal",
                fg_color="#212732",
                hover_color="#2D3544",
                text_color="#ECEFF4",
            )

        elif task.status == DownloadStatus.FAILED:
            msg = task.error_message if task.error_message else "Nieznany błąd"
            self.status_lbl.configure(text=f"Błąd: {msg}", text_color="#BF616A")
            self._set_terminal_buttons()

        elif task.status == DownloadStatus.CANCELLED:
            self.status_lbl.configure(text="Anulowano pobieranie", text_color="#D08770")
            self.progress_bar.configure(progress_color="#3B4252")
            self.open_btn.configure(
                state="disabled",
                fg_color="#212732",
                text_color="#4C566A",
            )
            self._set_terminal_buttons()

        elif task.status == DownloadStatus.COMPLETED:
            if task.error_message == "ALREADY_EXISTS":
                msg = "Playlista już pobrana na dysk." if task.is_playlist else "Plik już istnieje na dysku."
                self.status_lbl.configure(text=msg, text_color="#EBCB8B")
            elif task.error_message and ("Brak" in task.error_message or "Pominięto" in task.error_message):
                self.status_lbl.configure(
                    text=f"Ukończono ({task.error_message})",
                    text_color="#EBCB8B"
                )
            else:
                self.status_lbl.configure(text="Ukończono pomyślnie", text_color="#A3BE8C")

            self.open_btn.configure(
                state="normal",
                fg_color="#212732",
                hover_color="#2D3544",
                text_color="#ECEFF4",
            )
            self._set_terminal_buttons()