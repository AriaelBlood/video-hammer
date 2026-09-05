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
