import os
import threading
from urllib.request import Request, urlopen
from PIL import Image
import customtkinter as ctk

from utils.history import load_history, save_history, clear_history


class HistoryView(ctk.CTkScrollableFrame):
    def __init__(self, master, on_count_changed=None, **kwargs):
        super().__init__(
            master,
            fg_color="#101318",
            scrollbar_button_color="#1F2430",
            scrollbar_button_hover_color="#2D3544",
            **kwargs
        )
        self.on_count_changed = on_count_changed
        self._current_filter = ""

    def render(self, filter_query: str = ""):
        self._current_filter = filter_query.strip().lower()

        for child in self.winfo_children():
            child.destroy()

        history = load_history()
        if self._current_filter:
            history = [item for item in history if self._current_filter in item.get("title", "").lower()]

        if not history:
            text = "Nie znaleziono wyników." if self._current_filter else "Historia pobierania jest pusta."
            empty_lbl = ctk.CTkLabel(
                self,
                text=text,
                font=("Segoe UI", 13),
                text_color="#434D5E",
            )
            empty_lbl.pack(pady=60)
            if self.on_count_changed:
                self.on_count_changed()
            return

        for item in history:
            self._create_history_row(item)

        if self.on_count_changed:
            self.on_count_changed()

    def _create_history_row(self, item: dict):
        row = ctk.CTkFrame(
            self,
            fg_color="#181C24",
            corner_radius=8,
            border_width=1,
            border_color="#242B35",
        )
        row.pack(fill="x", padx=4, pady=4)

        thumb_lbl = ctk.CTkLabel(
            row,
            text="",
            width=106,
            height=60,
            fg_color="#101318",
            corner_radius=6,
        )
        thumb_lbl.pack(side="left", padx=(10, 8), pady=10)

        thumb_url = item.get("thumbnail_url", "")
        if thumb_url:
            def _load_thumb():
                try:
                    req = Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urlopen(req, timeout=4) as response:
                        img = Image.open(response)
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(106, 60))
                    self.after(0, lambda: thumb_lbl.configure(image=ctk_img, text=""))
                except Exception:
                    pass
            threading.Thread(target=_load_thumb, daemon=True).start()

        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=(4, 10), pady=10)

        meta_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        meta_frame.pack(fill="x")

        badge = ctk.CTkLabel(
            meta_frame,
            text=f" {item.get('mode', 'Wideo')} ",
            font=("Segoe UI", 10, "bold"),
            fg_color="#212732",
            text_color="#60A5FA",
            corner_radius=4,
        )
        badge.pack(side="left", padx=(0, 8))

        date_lbl = ctk.CTkLabel(
            meta_frame,
            text=item.get("date", "--"),
            font=("Segoe UI", 10),
            text_color="#6B7A90",
        )
        date_lbl.pack(side="left")

        if item.get("is_playlist"):
            pl_badge = ctk.CTkLabel(
                meta_frame,
                text="Playlista",
                font=("Segoe UI", 10),
                text_color="#A78BFA",
            )
            pl_badge.pack(side="left", padx=(8, 0))

        title_lbl = ctk.CTkLabel(
            info_frame,
            text=item.get("title", "Bez tytułu"),
            font=("Segoe UI", 12, "bold"),
            text_color="#ECEFF4",
            anchor="w",
            wraplength=420,
            justify="left",
        )
        title_lbl.pack(fill="x", pady=(4, 0))

        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.pack(side="right", padx=12, pady=10)

        ctk.CTkButton(
            btn_frame,
            text="Kopiuj URL",
            width=76,
            height=26,
            font=("Segoe UI", 10),
            fg_color="#212732",
            hover_color="#2D3544",
            text_color="#D8DEE9",
            corner_radius=4,
            command=lambda u=item.get("url", ""): self._copy_url(u),
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame,
            text="Folder",
            width=60,
            height=26,
            font=("Segoe UI", 10),
            fg_color="#212732",
            hover_color="#2D3544",
            text_color="#D8DEE9",
            corner_radius=4,
            command=lambda p=item.get("output_dir", ""): self._open_history_dir(p),
        ).pack(side="left")

    def _copy_url(self, url: str):
        if not url:
            return
        self.clipboard_clear()
        self.clipboard_append(url)
        self.update()

    def _open_history_dir(self, path: str):
        if not path:
            return
        target = path if os.path.exists(path) else os.path.dirname(path)
        if os.path.exists(target):
            os.startfile(target)

    def clear(self, search_query: str = ""):
        query = search_query.strip().lower()
        if query:
            current_history = load_history()
            remaining = [i for i in current_history if query not in i.get("title", "").lower()]
            save_history(remaining)
        else:
            clear_history()

        self.render(search_query)