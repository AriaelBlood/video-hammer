"""Left panel: list of loaded videos with their settings summary."""
import os
import time
import tkinter as tk
from tkinter import ttk


class FileListPanel(ttk.LabelFrame):
    COLUMNS = ("file", "created", "info", "settings")

    def __init__(self, master, on_select):
        super().__init__(master, text="Videos", padding=6)
        self.on_select = on_select

        self.tree = ttk.Treeview(self, columns=self.COLUMNS, show="headings", selectmode="extended")
        headers = {"file": "File", "created": "Created", "info": "Info", "settings": "Settings"}
        widths = {"file": 200, "created": 125, "info": 160, "settings": 220}
        for col in self.COLUMNS:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="w")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._fire_select)

    # -- helpers -------------------------------------------------
    def _row_values(self, job):
        created = "—"
        try:
            created = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getctime(job.path)))
        except OSError:
            pass
        info = "probing…"
        if job.duration > 0:
            mins, secs = divmod(int(job.duration), 60)
            info = f"{mins}:{secs:02d}"
            if job.src_width:
                info += f" · {job.src_width}×{job.src_height}"
        elif job.probe_failed:
            info = "⚠ probe failed"
        return (job.filename, created, info, job.settings_summary())

    def add_job(self, job):
        self.tree.insert("", "end", iid=job.path, values=self._row_values(job))

    def refresh_job(self, job):
        if self.tree.exists(job.path):
            self.tree.item(job.path, values=self._row_values(job))

    def remove_selected(self):
        for iid in self.tree.selection():
            self.tree.delete(iid)
        return list(self.tree.selection())

    def selected_paths(self):
        return list(self.tree.selection())

    def clear(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)

    def _fire_select(self, _event):
        sel = self.tree.selection()
        self.on_select(sel[0] if sel else None)
