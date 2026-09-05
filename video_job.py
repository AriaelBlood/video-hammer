"""VideoJob dataclass: one loaded video + its own compression settings."""
from dataclasses import dataclass, field, asdict
import os

VIDEO_ENCODERS = [
    "libx264 (software H.264)",
    "libx265 (software H.265)",
    "h264_nvenc (NVIDIA)",
    "hevc_nvenc (NVIDIA HEVC)",
    "h264_qsv (Intel QuickSync)",
    "h264_amf (AMD)",
]
AUDIO_CODECS = ["aac", "libmp3lame", "copy", "none (mute)"]
RESOLUTION_PRESETS = ["keep original", "1080p", "720p", "480p", "custom"]

# maps UI label -> ffmpeg encoder name
ENCODER_MAP = {
    "libx264 (software H.264)": "libx264",
    "libx265 (software H.265)": "libx265",
    "h264_nvenc (NVIDIA)": "h264_nvenc",
    "hevc_nvenc (NVIDIA HEVC)": "hevc_nvenc",
    "h264_qsv (Intel QuickSync)": "h264_qsv",
    "h264_amf (AMD)": "h264_amf",
}
CODEC_FAMILY = {  # which quality model applies
    "libx264": "crf", "libx265": "crf",
    "h264_nvenc": "hw", "hevc_nvenc": "hw",
    "h264_qsv": "hw", "h264_amf": "hw",
}
RESOLUTION_MAP = {"1080p": (1920, 1080), "720p": (1280, 720), "480p": (854, 480)}


@dataclass
class VideoJob:
    path: str
    # settings (per-file)
    vencoder: str = "libx264 (software H.264)"
    crf: int = 23
    hw_quality: int = 27          # -cq value for hardware encoders
    resolution: str = "keep original"
    custom_width: int = 1280
    custom_height: int = 720
    acodec: str = "aac"
    abitrate: str = "128k"
    # probe info (filled later, M2)
    duration: float = 0.0
    src_width: int = 0
    src_height: int = 0
    probe_failed: bool = False
    # preview clip paths (filled in M3)
    preview_clips: list = field(default_factory=list)

    @property
    def filename(self) -> str:
        return os.path.basename(self.path)

    @property
    def encoder_name(self) -> str:
        return ENCODER_MAP.get(self.vencoder, "libx264")

    @property
    def quality_value(self) -> int:
        return self.crf if CODEC_FAMILY.get(self.encoder_name) == "crf" else self.hw_quality

    @property
    def target_size(self):
        if self.resolution == "keep original":
            return None
        if self.resolution == "custom":
            return (self.custom_width, self.custom_height)
        return RESOLUTION_MAP[self.resolution]

    def settings_summary(self) -> str:
        enc = self.encoder_name
        res = self.resolution if self.resolution != "custom" else f"{self.custom_width}x{self.custom_height}"
        return f"{enc} Q{self.quality_value}, {res}, {self.acodec} {self.abitrate}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "VideoJob":
        d = dict(d)
        d.pop("preview_clips", None)
        return cls(**d)
