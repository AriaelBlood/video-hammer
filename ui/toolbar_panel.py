"""Top toolbar: add / remove videos, apply settings to all, start compression."""
import tkinter as tk
from tkinter import ttk, filedialog

VIDEO_EXTENSIONS = [("Video files", "*.mp4 *.mkv *.avi *.mov *.webm *.ts *.m4v *.flv *.wmv"),
                    ("All files", "*.*")]


class ToolbarPanel(ttk.LabelFrame):
    def __init__(self, master, on_add, on_remove, on_apply_all, on_compress):
        super().__init__(master, text="Tools", padding=(8, 8, 8, 4))
        self.on_add = on_add
        self.on_remove = on_remove

        ttk.Button(self, text="Add Videos…", command=self._pick_files).pack(side="left")
        ttk.Button(self, text="Remove Selected", command=self.on_remove).pack(side="left", padx=(6, 0))
        ttk.Separator(self, orient="vertical").pack(side="left", fill="y", padx=10, pady=2)
        ttk.Button(self, text="Apply Settings to All", command=on_apply_all).pack(side="left")
        ttk.Button(self, text="Compress (Final) ▶", command=on_compress).pack(side="right")

    def _pick_files(self):
        paths = filedialog.askopenfilenames(title="Select video files", filetypes=VIDEO_EXTENSIONS)
        if paths:
            self.on_add(list(paths))
