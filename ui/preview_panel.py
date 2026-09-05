"""Right panel bottom: manual preview generation + per-clip open buttons."""
import os
import subprocess
import tkinter as tk
from tkinter import ttk

PREVIEW_LABELS = ("Clip 1 (10%)", "Clip 2 (40%)", "Clip 3 (70%)")


class PreviewPanel(ttk.LabelFrame):
    def __init__(self, master, on_generate, on_progress_status=None):
        super().__init__(master, text="Previews", padding=8)
        self.on_generate = on_generate
        self.paths = []

        self.generate_btn = ttk.Button(self, text="Generate Previews", command=self._fire)
        self.generate_btn.pack(fill="x")

        self.status_var = tk.StringVar(value="No previews yet.")
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(fill="x", pady=(6, 2))

        self.clip_buttons = []
        for label in PREVIEW_LABELS:
            btn = ttk.Button(self, text=f"▶ {label}", state="disabled",
                             command=lambda b=None: None)
            btn.pack(fill="x", pady=2)
            self.clip_buttons.append(btn)

    # -- public --------------------------------------------------
    def set_job(self, job):
        self.generate_btn.configure(state="normal" if job else "disabled")
        if job is None:
            self.status_var.set("No video selected.")
            self._set_clips([])
        elif not self.paths:
            self.status_var.set("Press Generate Previews to create 3 test clips.")

    def set_busy(self, busy: bool, text: str = ""):
        self.generate_btn.configure(state="disabled" if busy else "normal")
        if text:
            self.status_var.set(text)

    def set_clips(self, paths):
        self.paths = list(paths)
        for i, btn in enumerate(self.clip_buttons):
            if i < len(self.paths):
                btn.configure(state="normal",
                              command=lambda p=self.paths[i]: self._open(p))
            else:
                btn.configure(state="disabled", command=lambda: None)
        self.status_var.set(f"{len(self.paths)} preview clip(s) ready — click ▶ to watch.")

    def show_error(self, message: str):
        self.status_var.set("⚠ preview failed (see message box)")
        from tkinter import messagebox
        messagebox.showerror("Preview failed", message)

    # -- private -------------------------------------------------
    def _fire(self):
        self.on_generate()

    def _open(self, path):
        if os.path.exists(path):
            os.startfile(path)  # Windows default player
