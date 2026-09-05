"""Bottom panel: overall progress bar, status text and Cancel button."""
import tkinter as tk
from tkinter import ttk


class ProgressPanel(ttk.Frame):
    def __init__(self, master, on_cancel):
        super().__init__(master, padding=(8, 4, 8, 8))
        self.on_cancel = on_cancel

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status_var, anchor="w").pack(side="top", fill="x")

        row = ttk.Frame(self)
        row.pack(side="top", fill="x", pady=(4, 0))
        self.bar = ttk.Progressbar(row, mode="determinate", maximum=100)
        self.bar.pack(side="left", fill="x", expand=True)
        self.cancel_btn = ttk.Button(row, text="Cancel", command=self.on_cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=(8, 0))

    # -- helpers -------------------------------------------------
    def set_status(self, text: str):
        self.status_var.set(text)

    def set_progress(self, percent: float):
        self.bar["value"] = max(0.0, min(100.0, percent))

    def set_busy(self, busy: bool):
        self.cancel_btn.configure(state="normal" if busy else "disabled")
