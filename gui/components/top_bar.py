from typing import Callable
from urllib.parse import parse_qs, urlparse
import customtkinter as ctk

from core.models import QualityMode
from utils.formatters import is_valid_youtube_url


class TopBar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        default_mode: str,
        on_download: Callable[[str, QualityMode], None],
        on_select_playlist: Callable[[str], None],
        on_mode_changed: Callable[[str], None],
        on_type_auto_detected: Callable[[str], None],
        **kwargs,
    ):
        super().__init__(master, fg_color="#181C24", corner_radius=10, border_width=1, border_color="#242B35", **kwargs)

        self.on_download = on_download
        self.on_select_playlist = on_select_playlist
        self.on_mode_changed = on_mode_changed
        self.on_type_auto_detected = on_type_auto_detected

        self._build_ui(default_mode)

    def _build_ui(self, default_mode: str):
        self.url_entry = ctk.CTkEntry(
            self,
            placeholder_text="Wklej adres URL filmu lub playlisty z YouTube...",
            placeholder_text_color="#8A99AD",
            height=40,
            font=("Segoe UI", 12),
            fg_color="#101318",
            border_color="#2A323F",
            text_color="#ECEFF4",
            corner_radius=8,
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(12, 8), pady=12)

        self.url_entry.bind("<Return>", lambda e: self.trigger_download())
        self.url_entry.bind("<KeyRelease>", lambda e: self._handle_url_change())
        self.url_entry.bind("<<Paste>>", lambda e: self.after(50, self._handle_url_change))
        self.url_entry.bind("<Control-v>", lambda e: self.after(50, self._handle_url_change))
        self.url_entry.bind("<Enter>", lambda e: self._check_clipboard_on_hover())


        available_modes = [m.value for m in QualityMode]
        initial_mode = default_mode if default_mode in available_modes else QualityMode.Q720P.value

        self.mode_select = ctk.CTkOptionMenu(
            self,
            values=available_modes,
            width=110,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color="#212732",
            button_color="#2A323F",
            button_hover_color="#364050",
            dropdown_fg_color="#181C24",
            dropdown_hover_color="#2A323F",
            dropdown_text_color="#ECEFF4",
            corner_radius=8,
            command=self._handle_mode_change,
        )
        self.mode_select.set(initial_mode)
        self.mode_select.pack(side="left", padx=(0, 8), pady=12)

        # Przycisk tworzymy i pakujemy na stałe obok przycisku "Pobierz"
        self.select_items_btn = ctk.CTkButton(
            self,
            text="Wybierz utwory",
            width=110,
            height=40,
            font=("Segoe UI", 11, "bold"),
            fg_color="#212732",
            hover_color="#2D3544",
            text_color="#ECEFF4",
            corner_radius=8,
            state="disabled",  # Domyślnie wyszarzony
            command=lambda: self.on_select_playlist(self.get_url()),
        )
        self.select_items_btn.pack(side="right", padx=(0, 8), pady=12)

        self.download_btn = ctk.CTkButton(
            self,
            text="Pobierz",
            width=100,
            height=40,
            font=("Segoe UI", 13, "bold"),
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            text_color="#FFFFFF",
            corner_radius=8,
            command=self.trigger_download,
        )
        self.download_btn.pack(side="right", padx=(0, 12), pady=12)

    def _handle_mode_change(self, choice: str):
        if self.on_mode_changed:
            self.on_mode_changed(choice)

    def get_url(self) -> str:
        return self.url_entry.get().strip()

    def set_url(self, url: str):
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, url)
        self._handle_url_change()

    def clear_url(self):
        self.url_entry.delete(0, "end")
        self.update_select_button(is_playlist=False)

    def show_error(self):
        self.url_entry.configure(border_color="#BF616A")
        self.after(1500, lambda: self.url_entry.configure(border_color="#2A323F"))

    def update_select_button(self, is_playlist: bool):
        # Nie usuwamy przycisku z układu - zmieniamy tylko jego dostępność
        if is_playlist:
            self.select_items_btn.configure(
                state="normal",
                fg_color="#212732",
                text_color="#ECEFF4"
            )
        else:
            self.select_items_btn.configure(
                state="disabled",
                fg_color="#181C24",
                text_color="#4C566A"
            )

    def set_select_button_state(self, text: str, state: str):
        self.select_items_btn.configure(text=text, state=state)

    def trigger_download(self):
        raw_url = self.get_url()
        if not raw_url or not is_valid_youtube_url(raw_url):
            self.show_error()
            return

        selected_mode_str = self.mode_select.get()
        selected_mode = next(m for m in QualityMode if m.value == selected_mode_str)
        self.on_download(raw_url, selected_mode)

    def _handle_url_change(self):
        raw_url = self.get_url()
        if not raw_url:
            self.update_select_button(False)
            self.on_type_auto_detected("none")
            return

        parsed = urlparse(raw_url)
        query = parse_qs(parsed.query)
        has_video = bool(query.get("v")) or "youtu.be" in parsed.netloc.lower()
        has_list = bool(query.get("list"))

        if has_list and query.get("list", [""])[0].startswith("RD"):
            has_list = False

        if has_list and not has_video:
            self.on_type_auto_detected("force_playlist")
            self.update_select_button(True)
        elif has_video and not has_list:
            self.on_type_auto_detected("force_single")
            self.update_select_button(False)
        elif has_list and has_video:
            self.on_type_auto_detected("both_allowed")
        else:
            self.on_type_auto_detected("both_allowed")
            self.update_select_button(False)

    def _check_clipboard_on_hover(self):
        if self.get_url():
            return
        try:
            cb = self.clipboard_get().strip()
            # Wklejaj wyłącznie wtedy, gdy cały ciąg jest poprawnym linkiem YouTube
            if cb and is_valid_youtube_url(cb):
                self.set_url(cb)
        except Exception:
            pass

    def set_download_btn_state(self, enabled: bool):
        if enabled:
            self.download_btn.configure(state="normal", fg_color="#2563EB")
        else:
            self.download_btn.configure(state="disabled", fg_color="#181C24")