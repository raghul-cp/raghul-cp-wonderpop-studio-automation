"""
Shared helpers used by every script in the pipeline.
Nothing in here calls a paid service.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
IMAGES_DIR = OUTPUT_DIR / "images"
AUDIO_DIR = OUTPUT_DIR / "audio"
VIDEO_CLIPS_DIR = OUTPUT_DIR / "video_clips"       # optional Kaggle output lands here
SCENES_RENDERED_DIR = OUTPUT_DIR / "scenes_rendered"
SCRIPT_JSON = OUTPUT_DIR / "script.json"
DURATIONS_JSON = OUTPUT_DIR / "durations.json"
SUBTITLES_SRT = OUTPUT_DIR / "subtitles.srt"
METADATA_JSON = OUTPUT_DIR / "metadata.json"
FINAL_VIDEO = OUTPUT_DIR / "final_short.mp4"

CONFIG_DIR = REPO_ROOT / "config"


def log(msg: str):
    print(f"[wonderpop] {msg}", flush=True)


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_channel_config() -> dict:
    return load_yaml(CONFIG_DIR / "channel.yml")


def load_themes() -> list:
    data = load_yaml(CONFIG_DIR / "themes.yml")
    return data["themes"]


def read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def ensure_dirs():
    for d in (OUTPUT_DIR, IMAGES_DIR, AUDIO_DIR, VIDEO_CLIPS_DIR, SCENES_RENDERED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def ffprobe_duration_seconds(path: Path) -> float:
    """Returns the duration of an audio/video file in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def call_groq_chat(messages, max_tokens=1200, temperature=0.9) -> str:
    """
    Calls Groq's free, OpenAI-compatible chat completion endpoint.
    Requires GROQ_API_KEY in the environment (set via GitHub Secrets).
    Model names on Groq's free tier change over time — override with
    the GROQ_MODEL env var if the default below has been retired.
    Raises RuntimeError on any failure so callers can fall back gracefully.
    """
    import requests

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")

    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"Groq call failed ({e}). Check GROQ_API_KEY and GROQ_MODEL.") from e


def fail(msg: str):
    log(f"ERROR: {msg}")
    sys.exit(1)
