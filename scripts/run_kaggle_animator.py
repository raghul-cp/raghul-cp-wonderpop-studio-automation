"""
OPTIONAL / ADVANCED — not required for the core pipeline.

Pushes notebooks/kaggle_scene_animator.ipynb to Kaggle (free account,
free 30 GPU-hours/week, no credit card) with the current run's scene
images embedded in it, waits for it to finish on a free T4 GPU, then
downloads the resulting short video clips into output/video_clips/.
assemble_video.py automatically prefers a clip over the static-image
slideshow for any scene where one is found.

Why Kaggle and not Google Colab: Colab's free tier is built for
interactive, logged-in browser sessions and its terms discourage
unattended/headless automation, so it isn't a good fit for a scheduled
GitHub Actions pipeline. Kaggle publishes a real API
(`kaggle kernels push` / `status` / `output`) that is *designed* to be
called like this, which is why this project uses it instead.

Honesty check: this step adds real complexity (model download time,
GPU queue time, occasional flakiness) for a nice-to-have upgrade over
the slideshow fallback. It's entirely optional — skip it and the
pipeline still produces a complete video every time.

Requires KAGGLE_USERNAME and KAGGLE_KEY secrets (see SETUP_GUIDE.md).
"""
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from common import IMAGES_DIR, VIDEO_CLIPS_DIR, SCRIPT_JSON, read_json, log, fail

NOTEBOOK_SOURCE = Path(__file__).resolve().parent.parent / "notebooks" / "kaggle_scene_animator.ipynb"
BUILD_DIR = Path(__file__).resolve().parent.parent / ".kaggle_build"
POLL_SECONDS = 30
TIMEOUT_SECONDS = 25 * 60   # free T4 sessions are plenty; this is just a safety cap


def require_kaggle_cli():
    try:
        subprocess.run(["kaggle", "--version"], capture_output=True, check=True)
    except Exception:
        fail("The `kaggle` CLI isn't installed. Add `pip install kaggle` to the workflow step.")


def kaggle_username() -> str:
    user = os.environ.get("KAGGLE_USERNAME")
    if not user:
        fail("KAGGLE_USERNAME secret is not set.")
    return user


def build_kernel(kernel_slug: str):
    """Copies the notebook template into a build dir, embeds this run's
    scene images + prompts as base64 in the first cell, and writes the
    kernel-metadata.json Kaggle's API needs."""
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    notebook = json.loads(NOTEBOOK_SOURCE.read_text(encoding="utf-8"))

    script = read_json(SCRIPT_JSON)
    scenes_payload = {}
    for scene in script["scenes"]:
        img_path = IMAGES_DIR / f"scene_{scene['id']}.jpg"
        if img_path.exists():
            scenes_payload[str(scene["id"])] = {
                "visual": scene["visual"],
                "image_b64": base64.b64encode(img_path.read_bytes()).decode("ascii"),
            }

    injected_source = (
        "import json\n"
        f"SCENES = json.loads('''{json.dumps(scenes_payload)}''')\n"
    )
    # The template notebook's first cell is a placeholder this replaces.
    notebook["cells"][0]["source"] = [injected_source]

    (BUILD_DIR / "kaggle_scene_animator.ipynb").write_text(
        json.dumps(notebook), encoding="utf-8"
    )
    (BUILD_DIR / "kernel-metadata.json").write_text(json.dumps({
        "id": kernel_slug,
        "title": "wonderpop-scene-animator",
        "code_file": "kaggle_scene_animator.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": True,
        "enable_internet": True,
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
    }), encoding="utf-8")


def push_and_wait(kernel_slug: str):
    log(f"Pushing kernel {kernel_slug} to Kaggle...")
    subprocess.run(["kaggle", "kernels", "push", "-p", str(BUILD_DIR)], check=True)

    waited = 0
    while waited < TIMEOUT_SECONDS:
        result = subprocess.run(
            ["kaggle", "kernels", "status", kernel_slug],
            capture_output=True, text=True,
        )
        status = result.stdout.strip()
        log(f"Kaggle kernel status: {status}")
        if "complete" in status.lower():
            return True
        if "error" in status.lower() or "cancel" in status.lower():
            log("Kaggle kernel run failed — falling back to the image slideshow.")
            return False
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS

    log("Timed out waiting for Kaggle — falling back to the image slideshow.")
    return False


def download_outputs(kernel_slug: str):
    VIDEO_CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["kaggle", "kernels", "output", kernel_slug, "-p", str(VIDEO_CLIPS_DIR)],
        check=True,
    )
    clips = list(VIDEO_CLIPS_DIR.glob("scene_*.mp4"))
    log(f"Downloaded {len(clips)} animated scene clip(s) to {VIDEO_CLIPS_DIR}")


def main():
    require_kaggle_cli()
    user = kaggle_username()
    kernel_slug = f"{user}/wonderpop-scene-animator"

    build_kernel(kernel_slug)
    ok = push_and_wait(kernel_slug)
    if ok:
        download_outputs(kernel_slug)
    else:
        log("No AI video clips produced this run — assemble_video.py will use the slideshow fallback.")


if __name__ == "__main__":
    main()
