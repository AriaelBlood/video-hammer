# Video Compressor UI — Plan

A Tkinter desktop app that compresses videos using `bin\ffmpeg.exe` (via `subprocess`),
with per-file settings, preview clips, and a progress bar.

## User Decisions
- FFmpeg tools: `bin\ffmpeg.exe` + `bin\ffprobe.exe` both available in project `bin` folder ✅ (also `ffplay.exe` exists)
- Previews: short clips open in the **default video player** (`os.startfile`) — no in-app video display
- Encoders: software (`libx264`, `libx265`) **and** hardware (`h264_nvenc`, `hevc_nvenc`, `h264_qsv`, `h264_amf`) included
- Language: Python 3 + Tkinter, all ffmpeg calls via `subprocess`

## Architecture
```
project/
├── bin/            ffmpeg.exe, ffprobe.exe
├── plan.md         this file
└── compressor.py   (single file v1; split later if it grows)
```

### Layers
1. **UI (Tkinter)** — main window, file table, per-file config panel, preview buttons, progress bar
2. **Job model** — `VideoJob` dataclass: path, duration, resolution + settings (vcodec, crf, resolution, acodec, abitrate)
3. **FFmpeg wrapper** — builds commands, runs subprocess, parses progress from stderr
4. **Workers (threading)** — all ffmpeg calls off the main thread; UI updated via `root.after()`

### UI Layout (top → bottom)
1. Toolbar: [Add Videos…] [Remove Selected] [Apply Settings to All]
2. Treeview file list: filename, size, duration, resolution, settings summary
3. Config panel (applies to selected file):
   - Video encoder: libx264 / libx265 / h264_nvenc / hevc_nvenc / h264_qsv / h264_amf
   - CRF spinbox (0–51 for x264/x265; bitrate/quality mapping for HW encoders)
   - Resolution preset: keep / 1080p / 720p / 480p / custom
   - Audio: aac / libmp3lame / copy / none + bitrate
4. Preview row: [Generate Previews] → 3 clip buttons (10% / 40% / 70% of duration, ~4s each)
5. Bottom: [OK — Start Encoding] [Cancel] + progress bar + status label

### Key Techniques
- Duration/probe: `ffprobe -v error -show_entries format=duration,stream=width,height ...`
- Fast seek preview: `-ss <t>` **before** `-i`, `-t 4`
- Progress: parse `time=HH:MM:SS.ms` from stderr, percent = time / duration
- No console window: `creationflags=subprocess.CREATE_NO_WINDOW`
- Cancel: flag checked in reader loop → `proc.terminate()`
- Output: `<name>_compressed.mp4` in user-chosen folder; uniquify if exists
- Errors: non-zero exit → show last stderr lines in messagebox

## Tasks

### M1 — UI skeleton
- [ ] T1.1: App window, toolbar, Treeview, bottom progress area
- [ ] T1.2: Add/Remove videos (filedialog, multi-select)
- [ ] T1.3: Per-file config panel bound to selection (settings save per row)

### M2 — Probe
- [ ] T2.1: ffprobe wrapper (duration, width, height)
- [ ] T2.2: Show probe info in table columns

### M3 — Preview
- [ ] T3.1: Generate 3 preview clips per file with its own settings
- [ ] T3.2: Buttons to open clips in default player

### M4 — Encode
- [ ] T4.1: Build final ffmpeg command from job settings (incl. HW encoder variants)
- [ ] T4.2: Background worker thread, one file at a time
- [ ] T4.3: Progress parsing → progress bar + status via `root.after`
- [ ] T4.4: Cancel support + completion/failure report

### M5 — Polish
- [ ] T5.1: "Apply settings to all files" button
- [ ] T5.2: Custom resolution field, output folder picker
- [ ] T5.3: Error dialogs with ffmpeg stderr tail

---

## Addendum — Critical Features (added after review)

### 1. Timestamp Reattachment (CRITICAL)
After each file finishes final compression, copy the original's timestamps to the new file so it keeps its position when sorted by date in File Explorer.
- **Do NOT use ffmpeg built-in metadata flags** — they don't work reliably for this.
- Use **PowerShell** via `subprocess` instead. The correct cmdlet is **`Get-Item`** (singular, noun form):
  ```powershell
  $src = Get-Item $old; $dst = Get-Item $new
  $dst.CreationTime  = $src.CreationTime
  $dst.LastWriteTime = $src.LastWriteTime
  ```
- Note: `Copy-Item` does NOT copy timestamps — properties must be set explicitly.
- Runs after a successful encode; part of the per-file completion step.

### 2. State Tracking via `compress_state.json` (CRITICAL)
- The app keeps a JSON state file recording every final job: source path, output path, status.
- Status lifecycle: `running` (written when encode starts) → `finished` (only after encode AND timestamp copy both succeed).
- On startup the app scans the state file:
  - Output file exists but is NOT marked `finished` → treated as **corrupt/unfinished**; user is offered redo or delete.
  - `finished` entries are skipped (already done).
- This makes interrupted encodes detectable across app restarts.

### 3. UI Layout Reference: `REF/app layout.png`
User provided a layout sketch:
- Top: full-width toolbar.
- Left (large ~70%): list of imported videos — name, creation date, settings summary, per-row [Preview] button.
- Right (~30%): config panel for the selected file + the 3 preview clips, each with an [Open] button (opens default player).
- Bottom: progress bar + status.

### Updated Tasks
- [ ] T4.5: Timestamp reattachment — PowerShell `Get-Item` copy of CreationTime/LastWriteTime after each successful encode
- [ ] T6.1: `compress_state.json` schema + read/write helpers
- [ ] T6.2: Mark jobs `running` on start → `finished` on success (after encode + timestamp copy)
- [ ] T6.3: On startup: detect unfinished/corrupt outputs (file exists, not marked finished), show report with redo/delete actions
- [ ] T1.4: Adjust UI skeleton to match REF/app layout.png (left list / right config split)

### Progress Log
- M1 UI skeleton DONE (T1.1–T1.4). Structure: `main.py` (entry), `app.py` (window wiring), `video_job.py` (`VideoJob` dataclass), `ui/` package with `ToolbarPanel`, `FileListPanel`, `ConfigPanel`, `ProgressPanel` classes. Compiles clean and launches (window verified).
- Next: M2 — ffprobe integration (duration/size shown in list "Created"/info columns).
- M2 probe DONE (T2.1–T2.3). New `ffprobe_utils.py` (wraps `bin\ffprobe.exe`, JSON output, CREATE_NO_WINDOW). `VideoJob` gained `probe_failed`. `FileListPanel` now shows Created date (filesystem getctime) + Info column `m:ss · WxH`. Probing runs in a daemon thread, row refreshes via `root.after`. Verified against a generated 3s test clip: {'duration': 3.0, 'width': 320, 'height': 240}. App relaunches fine.
- Next: M3 — preview clips (3 clips at 10/40/70%, encoded with per-file settings, opened in default player).
- M3 previews DONE (T3.1–T3.2 + manual Generate button per user request). New `ffmpeg_utils.py` (`build_video_args` shared with final encode, `make_previews` = 3 clips @10/40/70%, 4s, fast-seek; `stderr_progress` helper for M4). New `ui/preview_panel.py` — Generate Previews button (NOT automatic), 3 clip Open buttons → `os.startfile` default player. Clips stored in `previews/` (gitignored). Verified: clips probe back as valid 4s videos. Git: `master` branch, commits `0cc459d` (M1+M2), `2c902bc` (gitignore), `33d0843` (M3).
- Next: M4 — final encoding with progress bar, cancel, background worker.
- M4 encode & timestamp reattachment DONE (T4.1–T4.5).
  - Background compression runner across all added videos with output folder picker.
  - Per-video status column updated in real-time (`Queued`, `Encoding…`, `Done ✔`, `Failed ✖`, `Cancelled`).
  - Overall progress bar and elapsed status text updated via stderr parsing.
  - User cancellation support with graceful subprocess cleanup.
  - PowerShell timestamp copy (`copy_file_timestamps`) using explicit path to `powershell.exe` to guarantee `CreationTime` and `LastWriteTime` match the source file perfectly. Verified with automated test: `MATCH SUCCESS!`.
  - Git commit: `48d9fe7`.
- Next: M6 — State tracking (`compress_state.json`) & corruption/unfinished detection on startup.
