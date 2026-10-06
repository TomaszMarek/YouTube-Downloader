from typing import Callable
import customtkinter as ctk


class SelectionView(ctk.CTkFrame):
    def __init__(self, master, on_confirm: Callable[[str], None], on_back: Callable[[], None], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_confirm = on_confirm
        self.on_back = on_back

        self.playlist_check_vars: dict[int, ctk.BooleanVar] = {}
        self._build_ui()

    def _build_ui(self):
        top_ctrl = ctk.CTkFrame(self, fg_color="#181C24", corner_radius=8, border_width=1, border_color="#242B35")
        top_ctrl.pack(fill="x", padx=4, pady=(0, 8))

        self.title_lbl = ctk.CTkLabel(
            top_ctrl,
            text="Wybór utworów",
            font=("Segoe UI", 12, "bold"),
            text_color="#ECEFF4",
            anchor="w",
        )
        self.title_lbl.pack(side="left", padx=12, pady=10)

        self.counter_lbl = ctk.CTkLabel(
            top_ctrl,
            text="",
            font=("Segoe UI", 11),
            text_color="#8B9BB4",
        )
        self.counter_lbl.pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            top_ctrl,
            text="Zaznacz wszystko",
            width=100,
            height=26,
            font=("Segoe UI", 10),
            fg_color="#212732",
            hover_color="#2D3544",
            text_color="#D8DEE9",
            command=self._select_all,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            top_ctrl,
            text="Odznacz",
            width=70,
            height=26,
            font=("Segoe UI", 10),
            fg_color="#212732",
            hover_color="#2D3544",
            text_color="#D8DEE9",
            command=self._deselect_all,
        ).pack(side="left")

        self.confirm_btn = ctk.CTkButton(
            top_ctrl,
            text="Pobierz wybrane",
            height=26,
            font=("Segoe UI", 11, "bold"),
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            command=self._handle_confirm,
        )
        self.confirm_btn.pack(side="right", padx=(6, 12), pady=8)

        ctk.CTkButton(
            top_ctrl,
            text="Powrót",
            width=70,
            height=26,
            font=("Segoe UI", 10),
            fg_color="#212732",
            hover_color="#2D3544",
            text_color="#D8DEE9",
            command=self.on_back,
        ).pack(side="right")

        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="#101318",
            scrollbar_button_color="#1F2430",
            scrollbar_button_hover_color="#2D3544",
        )
        self.list_frame.pack(fill="both", expand=True)

    def load_entries(self, title: str, entries: list):
        self.playlist_check_vars.clear()
        for child in self.list_frame.winfo_children():
            child.destroy()

        short_title = title[:50] + ("..." if len(title) > 50 else "")
        self.title_lbl.configure(text=short_title)

        for idx, entry in enumerate(entries, start=1):
            var = ctk.BooleanVar(value=True)
            self.playlist_check_vars[idx] = var
            item_title = entry.get("title") or f"Pozycja #{idx}"

            item_card = ctk.CTkFrame(
                self.list_frame,
                fg_color="#141820",
                corner_radius=6,
                border_width=1,
                border_color="#1E2530",
            )
            item_card.pack(fill="x", padx=6, pady=3)

            cb = ctk.CTkCheckBox(
                item_card,
                text="",
                variable=var,
                width=20,
                checkbox_width=18,
                checkbox_height=18,
                command=self._update_counter,
                fg_color="#2563EB",
                hover_color="#1D4ED8",
                border_color="#364050",
            )
            cb.pack(side="left", padx=(10, 6), pady=8)

            num_lbl = ctk.CTkLabel(
                item_card,
                text=f"{idx:02d}.",
                font=("Segoe UI", 11, "bold"),
                text_color="#64748B",
                width=28,
                anchor="w",
            )
            num_lbl.pack(side="left", pady=8)

            txt_lbl = ctk.CTkLabel(
                item_card,
                text=item_title,
                font=("Segoe UI", 11),
                text_color="#E2E8F0",
                anchor="w",
            )
            txt_lbl.pack(side="left", fill="x", expand=True, padx=(4, 10), pady=8)

            def _toggle(v=var):
                v.set(not v.get())
                self._update_counter()

            item_card.bind("<Button-1>", lambda e, tr=_toggle: tr())
            txt_lbl.bind("<Button-1>", lambda e, tr=_toggle: tr())
            num_lbl.bind("<Button-1>", lambda e, tr=_toggle: tr())

        self._update_counter()

    def _select_all(self):
        for v in self.playlist_check_vars.values():
            v.set(True)
        self._update_counter()

    def _deselect_all(self):
        for v in self.playlist_check_vars.values():
            v.set(False)
        self._update_counter()

    def _update_counter(self):
        selected = sum(1 for v in self.playlist_check_vars.values() if v.get())
        total = len(self.playlist_check_vars)
        self.counter_lbl.configure(text=f"({selected}/{total})")
        self.confirm_btn.configure(
            text=f"Pobierz wybrane ({selected})",
            state="normal" if selected > 0 else "disabled",
        )

    def _handle_confirm(self):
        selected_indices = [str(idx) for idx, v in self.playlist_check_vars.items() if v.get()]
        if selected_indices:
            self.on_confirm(",".join(selected_indices))