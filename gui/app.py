import os
import threading
from urllib.parse import parse_qs, urlparse
import customtkinter as ctk
from yt_dlp import YoutubeDL

from core.events import EventBus
from core.models import DownloadStatus, QualityMode, TaskEvent
from core.queue_manager import QueueManager
from gui.components.nav_bar import NavBar
from gui.components.path_bar import PathBar
from gui.components.top_bar import TopBar
from gui.task_card import TaskCard
from gui.views.history_view import HistoryView
from gui.views.selection_view import SelectionView
from utils.config import load_settings, save_settings
from utils.history import load_history
from utils.paths import get_default_download_dir

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Downloader")
        self.geometry("820x640")
        self.minsize(700, 500)
        self.configure(fg_color="#101318")

        self.settings = load_settings()
        self.current_download_dir = self.settings.get("download_dir", get_default_download_dir())
        self.cards: dict[str, TaskCard] = {}
        self._playlist_cache: dict[str, tuple[str, list]] = {}
        self.pending_playlist_url = ""

        self.event_bus = EventBus()
        self.queue_manager = QueueManager(event_bus=self.event_bus, max_concurrent_downloads=2)

        self._build_ui()
        self._update_ui_state()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.after(50, self._process_events)

    def _build_ui(self):
        self.top_bar = TopBar(
            self,
            default_mode=self.settings.get("default_mode", QualityMode.Q720P.value),
            on_download=self._start_download,
            on_select_playlist=self._load_playlist_selection,
            on_mode_changed=lambda m: self._save_settings(),
            on_type_auto_detected=self._on_url_type_detected,
        )
        self.top_bar.pack(fill="x", padx=16, pady=(16, 10))

        self.path_bar = PathBar(
            self,
            initial_dir=self.current_download_dir,
            initial_type=self.settings.get("download_type", "single"),
            on_dir_changed=self._on_dir_changed,
            on_type_changed=lambda t: self._on_download_type_changed(t == "playlist"),
        )
        self.path_bar.pack(fill="x", padx=16, pady=(0, 10))

        self.nav_bar = NavBar(
            self,
            on_tab_changed=self._switch_view,
            on_clear_action=self._handle_clear,
            on_search=lambda q: self.history_view.render(q),
        )
        self.nav_bar.pack(fill="x", padx=16, pady=(0, 8))

        self.queue_frame = ctk.CTkScrollableFrame(self, fg_color="#101318", scrollbar_button_color="#1F2430")
        self.queue_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.queue_empty_lbl = ctk.CTkLabel(
            self.queue_frame,
            text="Brak aktywnych zadań w kolejce.",
            font=("Segoe UI", 13),
            text_color="#434D5E",
        )
        self.queue_empty_lbl.pack(pady=60)

        self.history_view = HistoryView(self, on_count_changed=self._update_ui_state)
        self.selection_view = SelectionView(
            self,
            on_confirm=self._on_playlist_selection_confirmed,
            on_back=lambda: self._switch_view("queue"),
        )

    def _on_url_type_detected(self, mode: str):
        self.path_bar.apply_auto_detection(mode)
        raw_url = self.top_bar.get_url()
        has_list = "list=" in raw_url and not "list=RD" in raw_url
        is_playlist_selected = self.path_bar.download_type_var.get() == "playlist"
        self.top_bar.update_select_button(has_list and is_playlist_selected)

    def _on_download_type_changed(self, is_playlist: bool):
        raw_url = self.top_bar.get_url()
        has_list = "list=" in raw_url and not "list=RD" in raw_url
        self.top_bar.update_select_button(is_playlist and has_list)

        if not is_playlist and self.selection_view.winfo_ismapped():
            self._switch_view("queue")

        self._save_settings()

    def _start_download(self, raw_url: str, mode: QualityMode):
        is_pl = self.path_bar.is_playlist()
        clean_url = self._clean_url(raw_url, is_pl)

        self.queue_manager.add_task(
            url=clean_url,
            output_dir=self.current_download_dir,
            mode=mode,
            is_playlist=is_pl,
            playlist_items=None,
        )
        self.top_bar.clear_url()
        if self.nav_bar.current_tab != "queue":
            self.nav_bar.switch_tab("queue")

    def _on_playlist_selection_confirmed(self, items_str: str):
        selected_mode_str = self.top_bar.mode_select.get()
        selected_mode = next(m for m in QualityMode if m.value == selected_mode_str)

        self.queue_manager.add_task(
            url=self.pending_playlist_url,
            output_dir=self.current_download_dir,
            mode=selected_mode,
            is_playlist=True,
            playlist_items=items_str,
        )
        self.top_bar.clear_url()
        self._switch_view("queue")
        self.nav_bar.switch_tab("queue")

    def _switch_view(self, view: str):
        self.queue_frame.pack_forget()
        self.history_view.pack_forget()
        self.selection_view.pack_forget()

        if view == "queue":
            self.nav_bar.pack(fill="x", padx=16, pady=(0, 8))
            self.queue_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

            self.top_bar.set_download_btn_state(True)
            raw_url = self.top_bar.get_url()
            has_list = "list=" in raw_url and "list=RD" not in raw_url
            is_pl = self.path_bar.download_type_var.get() == "playlist"
            self.top_bar.update_select_button(is_pl and has_list)

            self._update_ui_state()

        elif view == "history":
            self.nav_bar.pack(fill="x", padx=16, pady=(0, 8))
            self.history_view.pack(fill="both", expand=True, padx=12, pady=(0, 12))
            self.history_view.render(self.nav_bar.search_entry.get())
            self.top_bar.set_download_btn_state(True)
            self._update_ui_state()

        elif view == "selection":
            self.nav_bar.pack_forget()
            self.selection_view.pack(fill="both", expand=True, padx=12, pady=(0, 12))

            # Blokada górnych przycisków w widoku selekcji
            self.top_bar.set_download_btn_state(False)
            self.top_bar.update_select_button(False)

    def _update_ui_state(self):
        q_count = len(self.cards)
        h_count = len(load_history())

        if self.nav_bar.current_tab == "history":
            can_clear = h_count > 0
        else:
            finished = (DownloadStatus.COMPLETED, DownloadStatus.CANCELLED, DownloadStatus.FAILED)
            can_clear = any(t.status in finished for t in self.queue_manager.tasks.values() if t.id in self.cards)

        self.nav_bar.update_counts(q_count, h_count, can_clear)
        if not self.cards:
            self.queue_empty_lbl.pack(pady=60)
        else:
            self.queue_empty_lbl.pack_forget()

    def _handle_clear(self):
        if self.nav_bar.current_tab == "history":
            self.history_view.clear(self.nav_bar.search_entry.get())
            self.nav_bar.search_entry.delete(0, "end")
        else:
            finished = (DownloadStatus.COMPLETED, DownloadStatus.CANCELLED, DownloadStatus.FAILED)
            for t_id in [k for k, t in self.queue_manager.tasks.items() if t.status in finished]:
                card = self.cards.pop(t_id, None)
                if card:
                    card.destroy()
        self._update_ui_state()

    def _load_playlist_selection(self, raw_url: str):
        if not raw_url:
            return
        clean_url = self._clean_url(raw_url, is_playlist=True)
        self.pending_playlist_url = clean_url

        if clean_url in self._playlist_cache:
            title, entries = self._playlist_cache[clean_url]
            self.selection_view.load_entries(title, entries)
            self._switch_view("selection")
            return

        self.top_bar.set_select_button_state("Pobieranie spisu...", "disabled")

        def _fetch():
            try:
                opts = {"extract_flat": "in_playlist", "quiet": True, "skip_download": True}
                with YoutubeDL(opts) as ydl:
                    data = ydl.extract_info(clean_url, download=False)
                entries = [e for e in data.get("entries", []) if e]
                title = data.get("title", "Playlista")
                self._playlist_cache[clean_url] = (title, entries)
                self.after(0, lambda: (
                    self.top_bar.set_select_button_state("Wybierz utwory", "normal"),
                    self.selection_view.load_entries(title, entries),
                    self._switch_view("selection"),
                ))
            except Exception:
                self.after(0, lambda: self.top_bar.set_select_button_state("Wybierz utwory", "normal"))

        threading.Thread(target=_fetch, daemon=True).start()

    def _clean_url(self, raw: str, is_playlist: bool) -> str:
        p = urlparse(raw)
        q = parse_qs(p.query)
        if is_playlist and "list" in q:
            return f"https://www.youtube.com/playlist?list={q['list'][0]}"
        if not is_playlist and "v" in q:
            return f"https://www.youtube.com/watch?v={q['v'][0]}"
        return raw

    def _on_dir_changed(self, new_dir: str):
        self.current_download_dir = new_dir
        self._save_settings()

    def _save_settings(self):
        self.settings["download_dir"] = self.current_download_dir
        self.settings["default_mode"] = self.top_bar.mode_select.get()
        self.settings["download_type"] = self.path_bar.download_type_var.get()
        save_settings(self.settings)

    def _process_events(self):
        while not self.event_bus.empty():
            ev: TaskEvent = self.event_bus.get_event()
            if not ev.task:
                continue
            if ev.event_type == "task_added":
                self.cards[ev.task.id] = TaskCard(
                    self.queue_frame, ev.task, self.queue_manager.cancel_task,
                    lambda tid: (self.cards.pop(tid, None), self._update_ui_state()),
                )
                self._update_ui_state()
            elif ev.task.id in self.cards:
                self.cards[ev.task.id].render(ev.task)
                if ev.event_type in ("completed", "completed_already_exists", "completed_with_warning", "error", "cancelled"):
                    self._update_ui_state()
        self.after(50, self._process_events)

    def _on_closing(self):
        self.withdraw()
        try:
            self._save_settings()
            self.queue_manager.shutdown()
        except Exception:
            pass
        finally:
            self.destroy()
            os._exit(0)