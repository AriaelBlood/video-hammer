"""Right panel: per-file configuration, bound to the selected video."""
import tkinter as tk
from tkinter import ttk

from video_job import VIDEO_ENCODERS, AUDIO_CODECS, RESOLUTION_PRESETS


class ConfigPanel(ttk.LabelFrame):
    def __init__(self, master, on_change):
        super().__init__(master, text="Settings for selected video", padding=8)
        self.on_change = on_change
        self.job = None
        self._loading = False  # suppress change events while filling widgets

        row = 0
        ttk.Label(self, text="Video encoder:").grid(row=row, column=0, sticky="w", pady=3)
        self.enc_var = tk.StringVar()
        self.enc_box = ttk.Combobox(self, textvariable=self.enc_var, values=VIDEO_ENCODERS,
                                    state="readonly", width=26)
        self.enc_box.grid(row=row, column=1, sticky="ew", pady=3)
        self.enc_box.bind("<<ComboboxSelected>>", self._save)

        row += 1
        ttk.Label(self, text="CRF (x264/x265):").grid(row=row, column=0, sticky="w", pady=3)
        self.crf_var = tk.IntVar(value=23)
        self.crf_spin = ttk.Spinbox(self, from_=0, to=51, textvariable=self.crf_var, width=6,
                                    command=self._save)
        self.crf_spin.grid(row=row, column=1, sticky="w", pady=3)

        row += 1
        ttk.Label(self, text="HW quality -cq (NVENC/QSV/AMF):").grid(row=row, column=0, sticky="w", pady=3)
        self.hw_var = tk.IntVar(value=27)
        self.hw_spin = ttk.Spinbox(self, from_=0, to=51, textvariable=self.hw_var, width=6,
                                   command=self._save)
        self.hw_spin.grid(row=row, column=1, sticky="w", pady=3)

        row += 1
        ttk.Label(self, text="Resolution:").grid(row=row, column=0, sticky="w", pady=3)
        self.res_var = tk.StringVar()
        self.res_box = ttk.Combobox(self, textvariable=self.res_var, values=RESOLUTION_PRESETS,
                                    state="readonly", width=14)
        self.res_box.grid(row=row, column=1, sticky="w", pady=3)
        self.res_box.bind("<<ComboboxSelected>>", self._save)

        row += 1
        ttk.Label(self, text="Custom W×H:").grid(row=row, column=0, sticky="w", pady=3)
        size_frame = ttk.Frame(self)
        self.w_var = tk.IntVar(value=1280)
        self.h_var = tk.IntVar(value=720)
        ttk.Spinbox(size_frame, from_=16, to=7680, textvariable=self.w_var, width=6,
                    command=self._save).pack(side="left")
        ttk.Label(size_frame, text="×").pack(side="left")
        ttk.Spinbox(size_frame, from_=16, to=4320, textvariable=self.h_var, width=6,
                    command=self._save).pack(side="left")
        size_frame.grid(row=row, column=1, sticky="w", pady=3)

        row += 1
        ttk.Label(self, text="Audio codec:").grid(row=row, column=0, sticky="w", pady=3)
        self.ac_var = tk.StringVar()
        self.ac_box = ttk.Combobox(self, textvariable=self.ac_var, values=AUDIO_CODECS,
                                   state="readonly", width=14)
        self.ac_box.grid(row=row, column=1, sticky="w", pady=3)
        self.ac_box.bind("<<ComboboxSelected>>", self._save)

        row += 1
        ttk.Label(self, text="Audio bitrate:").grid(row=row, column=0, sticky="w", pady=3)
        self.ab_var = tk.StringVar(value="128k")
        self.ab_box = ttk.Combobox(self, textvariable=self.ab_var,
                                   values=["64k", "96k", "128k", "192k", "256k", "320k"], width=8)
        self.ab_box.grid(row=row, column=1, sticky="w", pady=3)
        self.ab_box.bind("<<ComboboxSelected>>", self._save)

        self.columnconfigure(1, weight=1)
        self.set_job(None)

    # -- public --------------------------------------------------
    def set_job(self, job):
        """Load a VideoJob's values into the widgets (or disable panel if None)."""
        self.job = job
        self._loading = True
        try:
            state = "normal" if job else "disabled"
            for w in self.winfo_children():
                try:
                    w.configure(state=state)
                except tk.TclError:
                    pass  # frames have no state
            if job:
                self.enc_var.set(job.vencoder)
                self.crf_var.set(job.crf)
                self.hw_var.set(job.hw_quality)
                self.res_var.set(job.resolution)
                self.w_var.set(job.custom_width)
                self.h_var.set(job.custom_height)
                self.ac_var.set(job.acodec)
                self.ab_var.set(job.abitrate)
        finally:
            self._loading = False

    # -- private -------------------------------------------------
    def _save(self, _event=None):
        if self._loading or self.job is None:
            return
        self.job.vencoder = self.enc_var.get()
        self.job.crf = int(self.crf_var.get())
        self.job.hw_quality = int(self.hw_var.get())
        self.job.resolution = self.res_var.get()
        self.job.custom_width = int(self.w_var.get())
        self.job.custom_height = int(self.h_var.get())
        self.job.acodec = self.ac_var.get()
        self.job.abitrate = self.ab_var.get()
        self.on_change(self.job)  # app refreshes the list row
