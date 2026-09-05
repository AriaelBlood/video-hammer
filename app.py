"""Main application window: wires the panels together."""
import tkinter as tk
from tkinter import ttk, messagebox
import os
import threading

from video_job import VideoJob
from ffprobe_utils import probe
from ui.toolbar_panel import ToolbarPanel
from ui.file_list_panel import FileListPanel
from ui.config_panel import ConfigPanel
from ui.progress_panel import ProgressPanel


class VideoCompressorApp:
    BIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Video Compressor")
        self.root.geometry("1050x640")
        self.root.minsize(880, 520)

        self.jobs = {}  # path -> VideoJob

        self.toolbar = ToolbarPanel(self.root, on_add=self.add_videos,
                                    on_remove=self.remove_selected,
                                    on_apply_all=self.apply_settings_to_all,
                                    on_compress=self.start_compression)
        self.toolbar.pack(fill="x")

        # left list (~70%) | right config (~30%)
        self.paned = ttk.PanedWindow(self.root, orient="horizontal")
        self.paned.pack(fill="both", expand=True, padx=8)

        self.file_list = FileListPanel(self.paned, on_select=self.on_file_selected)
        self.config_panel = ConfigPanel(self.paned, on_change=self.on_settings_changed)
        self.paned.add(self.file_list, weight=7)
        self.paned.add(self.config_panel, weight=3)

        self.progress = ProgressPanel(self.root, on_cancel=self.cancel)
        self.progress.pack(fill="x")

        # graceful close (kills worker threads between awaits)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.version_label = tk.Label(text="V 0.0.1alph")
        self.auther_label = tk.Label(text="by AshnVeyl")
        self.version_label.pack(anchor='e',padx=20)
        self.auther_label.pack(anchor='e',padx=6)

    # -- lifecycle ------------------------------------------------
    def run(self):
        self.root.mainloop()

    def _on_close(self):
        self.root.destroy()

    # -- toolbar actions ------------------------------------------
    def add_videos(self, paths):
        added = 0
        for p in paths:
            if p in self.jobs:
                continue
            job = VideoJob(path=p)
            self.jobs[p] = job
            self.file_list.add_job(job)
            added += 1
            self._start_probe(job)
        self.progress.set_status(f"Added {added} video(s). {len(self.jobs)} in list.")

    def _start_probe(self, job):
        """Run ffprobe off the UI thread; update the row when done."""
        def worker():
            try:
                info = probe(job.path)
                job.duration = info["duration"]
                job.src_width = info["width"]
                job.src_height = info["height"]
            except Exception:
                job.probe_failed = True
            self.root.after(0, lambda: self.file_list.refresh_job(job))
        threading.Thread(target=worker, daemon=True).start()

    def remove_selected(self):
        for p in self.file_list.remove_selected():
            self.jobs.pop(p, None)
        self.on_file_selected(None)

    def apply_settings_to_all(self):
        src = self.config_panel.job
        if src is None:
            messagebox.showinfo("Apply to all", "Select a video in the list first.")
            return
        for job in self.jobs.values():
            if job is src:
                continue
            for attr in ("vencoder", "crf", "hw_quality", "resolution",
                         "custom_width", "custom_height", "acodec", "abitrate"):
                setattr(job, attr, getattr(src, attr))
            self.file_list.refresh_job(job)
        self.progress.set_status("Applied settings to all videos.")

    def start_compression(self):
        # M4: final encoding — for now, placeholder
        messagebox.showinfo("Compress", "Final encoding comes in milestone M4.\n"
                                        "UI skeleton is working.")

    def cancel(self):
        pass  # M4

    # -- selection / config binding --------------------------------
    def on_file_selected(self, path):
        self.config_panel.set_job(self.jobs.get(path) if path else None)

    def on_settings_changed(self, job):
        self.file_list.refresh_job(job)
