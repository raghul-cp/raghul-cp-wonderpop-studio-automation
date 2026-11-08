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


GROQ_MODEL_CANDIDATES = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]


def call_groq_chat(messages, max_tokens=1200, temperature=0.9) -> str:
    """
    Calls Groq's free, OpenAI-compatible chat completion endpoint.
    Requires GROQ_API_KEY in the environment (set via GitHub Secrets).

    Groq's free-tier model line-up shifts over time, so this tries a short
    list of models in order and only gives up if every single one fails —
    one retired model name should no longer be able to knock the whole
    pipeline into its template fallback. Set GROQ_MODEL to force one
    specific model instead of trying the list.

    Raises RuntimeError (with every model's error attached) only if all
    attempts fail, so callers can fall back gracefully.
    """
    import requests

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")

    forced_model = os.environ.get("GROQ_MODEL", "").strip()
    models_to_try = [forced_model] if forced_model else GROQ_MODEL_CANDIDATES

    errors = []
    for model in models_to_try:
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
            if resp.status_code == 401:
                # Bad/expired key — no point trying other models.
                raise RuntimeError(f"Groq rejected the API key (401). Check the GROQ_API_KEY secret. Response: {resp.text[:300]}")
            resp.raise_for_status()
            data = resp.json()
            log(f"Groq call succeeded using model '{model}'.")
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            detail = getattr(e, "response", None)
            body = detail.text[:300] if detail is not None else str(e)
            errors.append(f"{model}: {body}")
            log(f"Groq model '{model}' failed, trying next if available: {body}")

    raise RuntimeError("All Groq models failed:\n" + "\n".join(errors))


def fail(msg: str):
    log(f"ERROR: {msg}")
    sys.exit(1)