"""Main application window: wires the panels together."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import threading

from video_job import VideoJob
from ffprobe_utils import probe
from ffmpeg_utils import encode_video, get_unique_output_path
from state_manager import (
    record_job_start,
    record_job_finished,
    record_job_failed,
    record_job_cancelled,
    check_unfinshed_or_corrupted_jobs,
    resolve_corrupt_job
)
from ui.toolbar_panel import ToolbarPanel
from ui.file_list_panel import FileListPanel
from ui.config_panel import ConfigPanel
from ui.preview_panel import PreviewPanel
from ui.progress_panel import ProgressPanel


class VideoCompressorApp:
    BIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Video Compressor")
        self.root.geometry("1050x640")
        self.root.minsize(880, 520)

        self.jobs = {}  # path -> VideoJob
        self._encode_worker_thread = None
        self._cancel_event = threading.Event()
        self._is_encoding = False

        self.toolbar = ToolbarPanel(self.root, on_add=self.add_videos,
                                    on_remove=self.remove_selected,
                                    on_apply_all=self.apply_settings_to_all,
                                    on_compress=self.start_compression)
        self.toolbar.pack(fill="x")

        # left list (~70%) | right config (~30%)
        self.paned = ttk.PanedWindow(self.root, orient="horizontal")
        self.paned.pack(fill="both", expand=True, padx=8)

        self.file_list = FileListPanel(self.paned, on_select=self.on_file_selected)

        right = ttk.Frame(self.paned)
        self.config_panel = ConfigPanel(right, on_change=self.on_settings_changed)
        self.config_panel.pack(fill="both", expand=True)
        self.preview_panel = PreviewPanel(right, on_generate=self.generate_previews)
        self.preview_panel.pack(fill="x", pady=(8, 0))

        self.paned.add(self.file_list, weight=7)
        self.paned.add(right, weight=3)

        self.progress = ProgressPanel(self.root, on_cancel=self.cancel)
        self.progress.pack(fill="x")

        # graceful close (kills worker threads between awaits)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.version_label = tk.Label(text="V 0.1.0 alph")
        self.auther_label = tk.Label(text="by AshnVeyl")
        self.version_label.pack(anchor='e',padx=20)
        self.auther_label.pack(anchor='e',padx=6)

        # Check for interrupted / corrupt jobs from previous run
        self.root.after(200, self._check_startup_corrupt_jobs)

    def _check_startup_corrupt_jobs(self):
        corrupt = check_unfinshed_or_corrupted_jobs()
        if not corrupt:
            return

        count = len(corrupt)
        names = "\n".join(f"• {os.path.basename(c.get('output_path', ''))} (Source: {os.path.basename(c.get('source_path', ''))})"
                          for c in corrupt[:5])
        if count > 5:
            names += f"\n...and {count - 5} more."

        msg = (
            f"Detected {count} unfinished/interrupted compression job(s) from a previous session.\n\n"
            f"The following partial file(s) exist on disk:\n{names}\n\n"
            f"Would you like to DELETE the partial/corrupted output file(s) now?\n"
            f"(Click 'Yes' to delete them, or 'No' to keep them as-is)"
        )

        should_delete = messagebox.askyesno("Unfinished / Corrupted Files Detected", msg)
        for c in corrupt:
            resolve_corrupt_job(c["id"], delete_file=should_delete)

        if should_delete:
            self.progress.set_status(f"Cleaned up {count} interrupted output file(s).")
        else:
            self.progress.set_status(f"Retained {count} interrupted output file(s).")

    # -- lifecycle ------------------------------------------------
    def run(self):
        self.root.mainloop()

    def _on_close(self):
        if self._is_encoding:
            if not messagebox.askyesno("Exit", "Encoding is currently in progress. Cancel and exit?"):
                return
            self._cancel_event.set()
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
                job.src_fps = info["fps"]
                # Prefill target fps with the source's own fps (nice quality-of-life)
                if job.src_fps > 0 and job.target_fps <= 0:
                    job.target_fps = job.src_fps
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
        if self._is_encoding:
            return

        if not self.jobs:
            messagebox.showinfo("Compress", "Please add some videos first.")
            return

        # Let user choose output directory
        first_video_dir = os.path.dirname(next(iter(self.jobs.values())).path)
        out_dir = filedialog.askdirectory(
            title="Select Output Folder for Compressed Videos",
            initialdir=first_video_dir
        )
        if not out_dir:
            return

        self._is_encoding = True
        self._cancel_event.clear()
        self.toolbar.set_busy(True)
        self.preview_panel.set_busy(True)
        self.progress.set_busy(True)
        self.progress.set_progress(0.0)

        # Reset statuses for jobs to be encoded
        for job in self.jobs.values():
            job.status = "Queued"
            job.error_message = ""
            self.file_list.refresh_job(job)

        jobs_list = list(self.jobs.values())

        def runner():
            succeeded = 0
            failed = 0
            cancelled = False

            total_jobs = len(jobs_list)

            for idx, job in enumerate(jobs_list):
                if self._cancel_event.is_set():
                    cancelled = True
                    job.status = "Cancelled"
                    self.root.after(0, lambda j=job: self.file_list.refresh_job(j))
                    continue

                job.status = "Encoding…"
                self.root.after(0, lambda j=job: self.file_list.refresh_job(j))

                output_path = get_unique_output_path(out_dir, job.filename)
                job.output_path = output_path

                # Record start in compress_state.json
                job_id = record_job_start(job.path, output_path, job.settings_summary())

                def on_progress(secs, cur_idx=idx, j_duration=job.duration):
                    if j_duration > 0:
                        file_pct = min(1.0, secs / j_duration)
                    else:
                        file_pct = 0.5
                    overall_pct = ((cur_idx + file_pct) / total_jobs) * 100.0
                    mins, rem_s = divmod(int(secs), 60)
                    msg = f"Encoding {cur_idx + 1}/{total_jobs}: {job.filename} [{mins}:{rem_s:02d}] ({overall_pct:.1f}%)"
                    self.root.after(0, lambda: (self.progress.set_progress(overall_pct),
                                                self.progress.set_status(msg)))

                try:
                    encode_video(job, output_path, progress_callback=on_progress, cancel_event=self._cancel_event)
                    # Succeeded: encode + PowerShell timestamp copy both finished
                    record_job_finished(job_id)
                    job.status = "Done ✔"
                    succeeded += 1
                except InterruptedError:
                    record_job_cancelled(job_id)
                    cancelled = True
                    job.status = "Cancelled"
                except Exception as exc:
                    record_job_failed(job_id, str(exc))
                    job.status = "Failed ✖"
                    job.error_message = str(exc)
                    failed += 1

                self.root.after(0, lambda j=job: self.file_list.refresh_job(j))

            self.root.after(0, lambda: self._compression_finished(succeeded, failed, cancelled))

        self._encode_worker_thread = threading.Thread(target=runner, daemon=True)
        self._encode_worker_thread.start()

    def cancel(self):
        if self._is_encoding:
            self._cancel_event.set()
            self.progress.set_status("Cancelling current encoding job…")

    def _compression_finished(self, succeeded, failed, cancelled):
        self._is_encoding = False
        self.toolbar.set_busy(False)
        self.preview_panel.set_busy(False)
        self.progress.set_busy(False)
        self.progress.set_progress(100.0 if not cancelled and failed == 0 else self.progress.bar["value"])

        if cancelled:
            summary = f"Encoding cancelled.\nCompleted: {succeeded}\nFailed: {failed}"
            self.progress.set_status("Encoding was cancelled.")
            messagebox.showwarning("Cancelled", summary)
        else:
            summary = f"Encoding finished!\nSuccessfully encoded: {succeeded}\nFailed: {failed}"
            self.progress.set_status(f"Finished: {succeeded} succeeded, {failed} failed.")
            if failed > 0:
                messagebox.showerror("Completed with Errors", summary)
            else:
                messagebox.showinfo("Completed", summary)

    # -- selection / config binding --------------------------------
    def on_file_selected(self, path):
        job = self.jobs.get(path) if path else None
        self.config_panel.set_job(job)
        self.preview_panel.set_job(job)

    def on_settings_changed(self, job):
        self.file_list.refresh_job(job)

    # -- previews (M3) ---------------------------------------------
    def generate_previews(self):
        job = self.config_panel.job
        if job is None:
            return
        if job.duration <= 0:
            messagebox.showinfo("Previews", "Still probing this video — try again in a second.")
            return
        self.preview_panel.set_busy(True, "Generating preview clips…")
        self.progress.set_busy(True)
        self.progress.set_status(f"Generating previews for {job.filename}…")

        def worker():
            from ffmpeg_utils import make_previews
            try:
                paths = make_previews(job)
                self.root.after(0, lambda: self._previews_done(job, paths))
            except Exception as exc:
                err = str(exc)
                self.root.after(0, lambda: self._previews_failed(err))
        threading.Thread(target=worker, daemon=True).start()

    def _previews_done(self, job, paths):
        job.preview_clips = paths
        self.preview_panel.set_clips(paths)
        self.preview_panel.set_busy(False)
        self.progress.set_busy(False)
        self.progress.set_status(f"Previews ready for {job.filename}.")

    def _previews_failed(self, err):
        self.preview_panel.set_busy(False)
        self.preview_panel.show_error(err)
        self.progress.set_busy(False)
        self.progress.set_status("Preview generation failed.")
