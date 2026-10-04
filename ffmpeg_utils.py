"""ffmpeg preview builder: encode 3 short clips with the job's own settings."""
import os
import re
import subprocess

from ffprobe_utils import FFMPEG, CREATE_NO_WINDOW

PREVIEW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "previews")
CLIP_SECONDS = 4
POSITIONS = (0.10, 0.40, 0.70)  # fraction of duration


def _timestamp(seconds: float) -> str:
    return f"{int(seconds // 3600):02d}:{int(seconds % 3600 // 60):02d}:{seconds % 60:05.2f}"


def build_video_args(job):
    """Shared ffmpeg args for a job's video/audio settings (used by previews AND final encode)."""
    args = []
    size = job.target_size
    if size:
        # keep aspect ratio via height, force even width (-2)
        args += ["-vf", f"scale=-2:{size[1]}"]
    args += ["-c:v", job.encoder_name]
    if job.encoder_name in ("libx264", "libx265"):
        args += ["-crf", str(job.crf), "-preset", "medium"]
    elif "nvenc" in job.encoder_name:
        args += ["-cq", str(job.hw_quality)]
    else:  # qsv / amf
        args += ["-global_quality", str(job.hw_quality)]
    # force a constant frame rate (fixes VFR screen-recordings that fail to compress)
    if getattr(job, "change_framerate", False) and job.target_fps > 0:
        args += ["-r", str(job.target_fps), "-vsync", "cfr"]
    if job.acodec.startswith("none"):
        args += ["-an"]
    elif job.acodec == "copy":
        args += ["-c:a", "copy"]
    else:
        args += ["-c:a", job.acodec, "-b:a", job.abitrate]
    return args


def make_preview(job, index: int) -> str:
    """Encode one preview clip; returns its path."""
    if job.duration <= 0:
        raise RuntimeError("Probe the video before generating previews.")
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    base = os.path.splitext(job.filename)[0]
    out = os.path.join(PREVIEW_DIR, f"{base}__preview{index + 1}.mp4")
    start = job.duration * POSITIONS[index]
    cmd = [FFMPEG, "-y", "-v", "error",
           "-ss", _timestamp(start), "-i", job.path, "-t", str(CLIP_SECONDS)]
    cmd += build_video_args(job)
    cmd += [out]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                            creationflags=CREATE_NO_WINDOW)
    if result.returncode != 0 or not os.path.exists(out):
        raise RuntimeError(f"ffmpeg preview failed:\n{result.stderr.strip()[-500:]}")
    return out


def make_previews(job):
    """Encode all 3 preview clips; returns list of paths. Raises on first failure."""
    return [make_preview(job, i) for i in range(3)]


def stderr_progress(line: str):
    """Parse 'time=00:01:23.45' from an ffmpeg stderr line -> seconds or None."""
    m = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
    if m:
        h, mn, s = m.groups()
        return int(h) * 3600 + int(mn) * 60 + float(s)
    return None


def copy_file_timestamps(src_path: str, dst_path: str):
    """Copy creation and modification timestamps from src to dst using PowerShell Get-Item."""
    ps_exe = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), r"System32\WindowsPowerShell\v1.0\powershell.exe")
    if not os.path.exists(ps_exe):
        ps_exe = "powershell"

    ps_cmd = (
        f"$s = (Get-Item -LiteralPath '{src_path}'); "
        f"$d = (Get-Item -LiteralPath '{dst_path}'); "
        f"$d.CreationTime = $s.CreationTime; "
        f"$d.LastWriteTime = $s.LastWriteTime"
    )
    res = subprocess.run(
        [ps_exe, "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW
    )
    if res.returncode != 0:
        raise RuntimeError(f"PowerShell timestamp copy failed: {res.stderr.strip()}")


def get_unique_output_path(output_dir: str, original_filename: str) -> str:
    """Generate a non-colliding output path like filename_compressed.mp4, or filename_compressed (1).mp4"""
    base, _ = os.path.splitext(original_filename)
    candidate = os.path.join(output_dir, f"{base}_compressed.mp4")
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(output_dir, f"{base}_compressed ({counter}).mp4")
        counter += 1
    return candidate


def encode_video(job, output_path: str, progress_callback=None, cancel_event=None):
    """
    Run full ffmpeg compression for a job.
    - progress_callback(processed_seconds: float)
    - cancel_event: threading.Event checked periodically
    Returns output_path on success.
    Raises RuntimeError on error or InterruptedError on cancellation.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [FFMPEG, "-y", "-i", job.path]
    cmd += build_video_args(job)
    cmd += [output_path]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1,
        creationflags=CREATE_NO_WINDOW
    )

    last_stderr_lines = []

    try:
        # ffmpeg writes progress info to stderr with \r or \n
        while True:
            if cancel_event and cancel_event.is_set():
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except OSError:
                        pass
                raise InterruptedError("Encoding was cancelled by user.")

            line = proc.stderr.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                last_stderr_lines.append(line)
                if len(last_stderr_lines) > 20:
                    last_stderr_lines.pop(0)

                secs = stderr_progress(line)
                if secs is not None and progress_callback:
                    progress_callback(secs)

        retcode = proc.wait()
        if retcode != 0:
            err_msg = "".join(last_stderr_lines).strip()
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            raise RuntimeError(f"FFmpeg exited with error code {retcode}:\n{err_msg[-600:]}")

        # Post-encode: Copy timestamps using PowerShell Get-Item as required
        copy_file_timestamps(job.path, output_path)

        return output_path

    except Exception:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
        raise
