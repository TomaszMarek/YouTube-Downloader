import os
from tkinter import filedialog
from typing import Callable
import customtkinter as ctk


class PathBar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        initial_dir: str,
        initial_type: str,
        on_dir_changed: Callable[[str], None],
        on_type_changed: Callable[[str], None],
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.current_download_dir = initial_dir
        self.on_dir_changed = on_dir_changed
        self.on_type_changed = on_type_changed

        self._build_ui(initial_type)

    def _build_ui(self, initial_type: str):
        self.path_container = ctk.CTkFrame(self, fg_color="#181C24", corner_radius=6, border_width=1, border_color="#242B35")
        self.path_container.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.path_lbl = ctk.CTkLabel(
            self.path_container,
            text=self._format_path(self.current_download_dir),
            font=("Segoe UI", 11),
            text_color="#8B9BB4",
            anchor="w",
        )
        self.path_lbl.pack(side="left", fill="x", expand=True, padx=(10, 8), pady=4)

        ctk.CTkButton(
            self.path_container,
            text="Zmień",
            width=54,
            height=24,
            font=("Segoe UI", 11),
            fg_color="#212732",
            hover_color="#2D3544",
            text_color="#ECEFF4",
            corner_radius=4,
            command=self._change_dir,
        ).pack(side="right", padx=(0, 6), pady=4)

        ctk.CTkButton(
            self.path_container,
            text="Folder",
            width=54,
            height=24,
            font=("Segoe UI", 11),
            fg_color="#212732",
            hover_color="#2D3544",
            text_color="#ECEFF4",
            corner_radius=4,
            command=self._open_dir,
        ).pack(side="right", padx=(0, 4), pady=4)

        self.download_type_var = ctk.StringVar(value=initial_type)

        radio_frame = ctk.CTkFrame(self, fg_color="transparent")
        radio_frame.pack(side="right")

        self.radio_single = ctk.CTkRadioButton(
            radio_frame,
            text="Pojedynczy film",
            variable=self.download_type_var,
            value="single",
            font=("Segoe UI", 11),
            fg_color="#2563EB",
            text_color="#C2CBE0",
            radiobutton_width=16,
            radiobutton_height=16,
            command=self._handle_type_change,
        )
        self.radio_single.pack(side="left", padx=(0, 10))

        self.radio_playlist = ctk.CTkRadioButton(
            radio_frame,
            text="Cała playlista",
            variable=self.download_type_var,
            value="playlist",
            font=("Segoe UI", 11),
            fg_color="#2563EB",
            text_color="#C2CBE0",
            radiobutton_width=16,
            radiobutton_height=16,
            command=self._handle_type_change,
        )
        self.radio_playlist.pack(side="left")

    def _format_path(self, path: str) -> str:
        max_len = 50
        return f"Zapis: ...{path[-(max_len - 10):]}" if len(path) > max_len else f"Zapis: {path}"

    def _change_dir(self):
        new_dir = filedialog.askdirectory(initialdir=self.current_download_dir)
        if new_dir:
            self.current_download_dir = new_dir
            self.path_lbl.configure(text=self._format_path(new_dir))
            self.on_dir_changed(new_dir)

    def _open_dir(self):
        target = self.current_download_dir
        if not os.path.exists(target):
            os.makedirs(target, exist_ok=True)
        os.startfile(target)

    def _handle_type_change(self):
        self.on_type_changed(self.download_type_var.get())

    def apply_auto_detection(self, mode: str):
        if mode == "force_playlist":
            self.download_type_var.set("playlist")
            self.radio_single.configure(state="disabled")
            self.radio_playlist.configure(state="normal")
        elif mode == "force_single":
            self.download_type_var.set("single")
            self.radio_single.configure(state="normal")
            self.radio_playlist.configure(state="disabled")
        elif mode == "both_allowed":
            self.radio_single.configure(state="normal")
            self.radio_playlist.configure(state="normal")
        elif mode == "none":
            self.radio_single.configure(state="normal")
            self.radio_playlist.configure(state="normal")

    def is_playlist(self) -> bool:
        return self.download_type_var.get() == "playlist"

    def _on_radio_change(self):
        is_pl = self.download_type_var.get() == "playlist"
        if self.on_type_changed:
            self.on_type_changed(is_pl)