"""State tracking manager for compression jobs via compress_state.json.

Lifecycle of a job:
  'running'   -> written when a compression job starts
  'finished'  -> written only after encode AND PowerShell timestamp copy both succeed
  'cancelled' -> marked if user stopped the process
  'failed'    -> marked if ffmpeg or timestamp copy threw an error

On app startup:
  Any entry with status == 'running' whose output_path exists on disk
  is considered interrupted / corrupt.
"""
import json
import os
import time

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compress_state.json")


def load_state() -> dict:
    """Load existing state dict from compress_state.json, or empty dict if not present/corrupt."""
    if not os.path.exists(STATE_FILE):
        return {"jobs": {}}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict) or "jobs" not in data:
                return {"jobs": {}}
            return data
    except Exception:
        return {"jobs": {}}


def save_state(state: dict):
    """Save state dict atomically to compress_state.json."""
    tmp_path = STATE_FILE + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, STATE_FILE)
    except Exception as e:
        print(f"Warning: Failed to save compress_state.json: {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def record_job_start(source_path: str, output_path: str, settings_summary: str) -> str:
    """Record that a compression job has begun. Returns a unique job_id."""
    state = load_state()
    job_id = f"{int(time.time() * 1000)}_{os.path.basename(source_path)}"
    state["jobs"][job_id] = {
        "id": job_id,
        "source_path": source_path,
        "output_path": output_path,
        "settings": settings_summary,
        "status": "running",
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "finished_at": None,
        "error": None
    }
    save_state(state)
    return job_id


def record_job_finished(job_id: str):
    """Mark a job as successfully finished (both encode and timestamp copy succeeded)."""
    state = load_state()
    if job_id in state["jobs"]:
        state["jobs"][job_id]["status"] = "finished"
        state["jobs"][job_id]["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save_state(state)


def record_job_failed(job_id: str, error_msg: str):
    """Mark a job as failed with error details."""
    state = load_state()
    if job_id in state["jobs"]:
        state["jobs"][job_id]["status"] = "failed"
        state["jobs"][job_id]["error"] = error_msg
        state["jobs"][job_id]["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save_state(state)


def record_job_cancelled(job_id: str):
    """Mark a job as cancelled."""
    state = load_state()
    if job_id in state["jobs"]:
        state["jobs"][job_id]["status"] = "cancelled"
        state["jobs"][job_id]["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save_state(state)


def check_unfinshed_or_corrupted_jobs() -> list:
    """
    Scan for jobs recorded as 'running' whose output file is present on disk.
    Returns list of dicts describing the interrupted jobs.
    """
    state = load_state()
    corrupt_jobs = []
    for job_id, info in list(state["jobs"].items()):
        if info.get("status") == "running":
            out_file = info.get("output_path", "")
            if out_file and os.path.exists(out_file):
                corrupt_jobs.append(info)
    return corrupt_jobs


def resolve_corrupt_job(job_id: str, delete_file: bool = True):
    """Clean up a corrupt job record and optionally remove its partial output file."""
    state = load_state()
    if job_id in state["jobs"]:
        info = state["jobs"][job_id]
        out_file = info.get("output_path", "")
        if delete_file and out_file and os.path.exists(out_file):
            try:
                os.remove(out_file)
            except OSError:
                pass
        info["status"] = "resolved_corrupt"
        save_state(state)
