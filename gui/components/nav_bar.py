from typing import Callable
import customtkinter as ctk


class NavBar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_tab_changed: Callable[[str], None],
        on_clear_action: Callable[[], None],
        on_search: Callable[[str], None],
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.on_tab_changed = on_tab_changed
        self.on_clear_action = on_clear_action
        self.on_search = on_search
        self.current_tab = "queue"

        self._build_ui()

    def _build_ui(self):
        tabs_box = ctk.CTkFrame(self, fg_color="transparent")
        tabs_box.pack(side="left")

        # Kolejka
        q_box = ctk.CTkFrame(tabs_box, fg_color="transparent")
        q_box.pack(side="left", padx=(0, 16))

        self.tab_queue_btn = ctk.CTkButton(
            q_box,
            text="Kolejka (0)",
            font=("Segoe UI", 13, "bold"),
            fg_color="transparent",
            hover_color="#181C24",
            text_color="#FFFFFF",
            height=28,
            command=lambda: self.switch_tab("queue"),
        )
        self.tab_queue_btn.pack(side="top")

        self.tab_queue_ind = ctk.CTkFrame(q_box, width=82, height=2, fg_color="#2563EB", corner_radius=1)
        self.tab_queue_ind.pack(side="top", pady=(2, 0))

        # Historia
        h_box = ctk.CTkFrame(tabs_box, fg_color="transparent")
        h_box.pack(side="left")

        self.tab_history_btn = ctk.CTkButton(
            h_box,
            text="Historia (0)",
            font=("Segoe UI", 13, "bold"),
            fg_color="transparent",
            hover_color="#181C24",
            text_color="#64748B",
            height=28,
            command=lambda: self.switch_tab("history"),
        )
        self.tab_history_btn.pack(side="top")

        self.tab_history_ind = ctk.CTkFrame(h_box, width=82, height=2, fg_color="transparent", corner_radius=1)
        self.tab_history_ind.pack(side="top", pady=(2, 0))

        # Prawa strona: czyszczenie i wyszukiwanie
        self.clear_btn = ctk.CTkButton(
            self,
            text="Usuń ukończone",
            height=28,
            font=("Segoe UI", 11),
            corner_radius=6,
            border_width=1,
            border_color="#242B35",
            command=self.on_clear_action,
        )
        self.clear_btn.pack(side="right")

        self.search_entry = ctk.CTkEntry(
            self,
            placeholder_text="Szukaj w historii...",
            placeholder_text_color="#8A99AD",
            width=210,
            height=28,
            font=("Segoe UI", 11),
            fg_color="#181C24",
            border_color="#2A323F",
            text_color="#ECEFF4",
            corner_radius=6,
        )
        self.search_entry.bind("<KeyRelease>", lambda e: self.on_search(self.search_entry.get()))

    def switch_tab(self, tab: str):
        self.current_tab = tab
        if tab == "queue":
            self.tab_queue_btn.configure(text_color="#FFFFFF")
            self.tab_queue_ind.configure(fg_color="#2563EB")
            self.tab_history_btn.configure(text_color="#64748B")
            self.tab_history_ind.configure(fg_color="transparent")
            self.search_entry.pack_forget()
            self.clear_btn.configure(text="Usuń ukończone")
        else:
            self.tab_history_btn.configure(text_color="#FFFFFF")
            self.tab_history_ind.configure(fg_color="#2563EB")
            self.tab_queue_btn.configure(text_color="#64748B")
            self.tab_queue_ind.configure(fg_color="transparent")
            self.search_entry.pack(side="right", padx=(0, 8))
            self.clear_btn.configure(text="Wyczyść historię")

        self.on_tab_changed(tab)

    def update_counts(self, queue_cnt: int, history_cnt: int, can_clear: bool):
        self.tab_queue_btn.configure(text=f"Kolejka ({queue_cnt})")
        self.tab_history_btn.configure(text=f"Historia ({history_cnt})")

        if can_clear:
            self.clear_btn.configure(state="normal", fg_color="#212732", hover_color="#2D3544", text_color="#ECEFF4")
        else:
            self.clear_btn.configure(state="disabled", fg_color="#181C24", text_color="#434D5E")