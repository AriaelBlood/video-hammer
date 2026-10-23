"""ffprobe wrapper: extract media info from video files using system PATH or local bin/."""
import json
import os
import shutil
import subprocess

# Look up in system PATH first; fallback to local bin/ if present
_LOCAL_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
FFPROBE = shutil.which("ffprobe") or os.path.join(_LOCAL_BIN, "ffprobe.exe")
FFMPEG = shutil.which("ffmpeg") or os.path.join(_LOCAL_BIN, "ffmpeg.exe")

# no console window pops up on Windows
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def get_ffmpeg_status() -> dict:
    """Check whether ffmpeg and ffprobe are accessible on the system."""
    ffmpeg_ok = bool(shutil.which("ffmpeg") or os.path.exists(FFMPEG))
    ffprobe_ok = bool(shutil.which("ffprobe") or os.path.exists(FFPROBE))
    return {
        "ffmpeg": FFMPEG if ffmpeg_ok else None,
        "ffprobe": FFPROBE if ffprobe_ok else None,
        "ready": ffmpeg_ok and ffprobe_ok
    }


def _parse_fps(stream: dict) -> float:
    """Best-effort average fps from a video stream dict (e.g. '30/1' -> 30.0)."""
    for key in ("avg_frame_rate", "r_frame_rate"):
        raw = stream.get(key) or ""
        try:
            num, den = raw.split("/")
            num, den = float(num), float(den)
            if den > 0 and num > 0:
                return round(num / den, 3)
        except (ValueError, ZeroDivisionError):
            continue
    return 0.0


def probe(path: str) -> dict:
    """Return {duration, width, height, fps} for a video file. Raises RuntimeError on failure."""
    cmd = [FFPROBE, "-v", "error", "-print_format", "json",
           "-show_entries", "format=duration",
           "-show_streams", path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                            creationflags=CREATE_NO_WINDOW)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()[:300]}")
    data = json.loads(result.stdout)
    duration = float(data.get("format", {}).get("duration", 0) or 0)
    width = height = 0
    fps = 0.0
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            width = int(stream.get("width") or 0)
            height = int(stream.get("height") or 0)
            fps = _parse_fps(stream)
            break
    return {"duration": duration, "width": width, "height": height, "fps": fps}
