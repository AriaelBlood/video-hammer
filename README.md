# Video Hammer

> ***Note***: This project was built with the help of AI to rapidly develop a personal productivity tool.

A desktop user interface for batch-compressing videos using FFmpeg while preserving their original creation and modification timestamps on Windows.

---

## Features

- **Per-File Independent Tuning**: Configure video encoder, quality (CRF / CQ), resolution, frame rate, and audio codec/bitrate independently for each imported video.
- **Hardware Acceleration Support**: Built-in support for software encoders (`libx264`, `libx265`) as well as hardware encoders:
  - NVIDIA NVENC (`h264_nvenc`, `hevc_nvenc`)
  - Intel QuickSync (`h264_qsv`)
  - AMD AMF (`h264_amf`)
- **3-Point Quality Preview**: Generate 4-second preview clips at 10%, 40%, and 70% of any video with its exact chosen settings, and preview them directly in your default media player before doing the final encode.
- **Original Timestamp Preservation**: Uses native Windows PowerShell `Get-Item` to copy the original file's `CreationTime` and `LastWriteTime` onto the compressed output, ensuring your videos maintain their sort order in Windows File Explorer.
- **Variable Frame Rate (VFR) Fix**: Optional "Force framerate" toggle with auto-detected source FPS to fix phone screen recordings that fail to encode under strict codecs.
- **Interrupted Job Recovery**: Automatically tracks compression jobs in `compress_state.json`. If the app crashes or the machine shuts down during encoding, it detects partial files on the next startup and offers to clean them up.
- **Non-blocking UI**: All FFmpeg and FFprobe tasks run on background threads with real-time percentage, elapsed time, and status indicators.

---

## Requirements

- **Windows 10 / 11** (uses PowerShell for timestamp restoration)
- **[Python 3.10+](https://www.python.org/)** (Python 3.14 tested; standard library only, no pip packages required)
- **[FFmpeg & FFprobe](https://ffmpeg.org/download.html)** installed and added to your system `PATH` environment variable.
  - To verify, open PowerShell and run:
    ```powershell
    ffmpeg -version
    ffprobe -version
    ```

---

## Installation & Running

```bash
git clone https://github.com/AriaelBlood/video-hammer.git
cd video-hammer
python main.py
```

---

## How to Use

1. Click **Add Videos…** to import one or more video files.
2. Select any video in the list to configure its compression settings on the right panel:
   - Choose encoder (software `libx264`/`libx265` or hardware NVENC/QSV/AMF).
   - Set the quality value (CRF for software, CQ for hardware).
   - Set resolution (keep original, 1080p, 720p, 480p, or custom W×H).
   - *(Optional)* For phone screen recordings, enable **Force framerate** (auto-fills with the detected video frame rate).
   - Configure audio codec and bitrate.
3. *(Optional)* Click **Apply Settings to All** to copy the selected file's settings across the entire queue.
4. *(Optional)* Click **Generate Previews** to encode 3 sample clips and click `▶ Clip` to inspect quality in your default video player.
5. Click **Compress (Final) ▶**, select an output folder, and let the batch runner process your videos.

---

## Known Issues

- The `Force framerate` option currently cannot be applied to all videos at once using the "Apply Settings to All" button; it must be toggled per file manually.
- This application currently only works on Windows (uses Windows PowerShell `Get-Item` for filesystem timestamp reattachment and `os.startfile` for media previews).

---

## Contributing

Contributions are welcomed! Feel free to open an issue or submit a pull request.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
