"""ffprobe wrapper: extract media info from video files using bin/ffprobe.exe."""
import json
import os
import subprocess

BIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")
FFPROBE = os.path.join(BIN_DIR, "ffprobe.exe")
FFMPEG = os.path.join(BIN_DIR, "ffmpeg.exe")
# no console window pops up on Windows
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def probe(path: str) -> dict:
    """Return {duration, width, height} for a video file. Raises RuntimeError on failure."""
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
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            width = int(stream.get("width") or 0)
            height = int(stream.get("height") or 0)
            break
    return {"duration": duration, "width": width, "height": height}
