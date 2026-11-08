"""
Step 2 of 6 — Generate one illustration per scene.

Primary path: Pollinations.ai (https://image.pollinations.ai) — free,
no API key, no signup. The anonymous tier is rate-limited (be polite:
we sleep between requests) and may add a small watermark; register for
free at https://auth.pollinations.ai if you want to remove that.

Every scene's prompt is prefixed with script.json's "character_sheet" (a
fixed description of the main character written once in generate_script.py)
and rendered with the SAME seed for every scene in the episode, so the
character and palette stay much more consistent scene to scene than
independent random generations would.

Fallback: if Pollinations is unreachable or rate-limited, we draw a
simple colored card with the scene text using Pillow, entirely offline,
so the pipeline never stalls waiting on an external image service. The
fallback uses a Tamil-capable font (Lohit Tamil, installed by the
workflow) so it degrades gracefully even for Tamil narration.

Output: output/images/scene_<id>.jpg
"""
import hashlib
import textwrap
import time
import urllib.parse

import requests
from PIL import Image, ImageDraw, ImageFont

from common import (
    IMAGES_DIR, SCRIPT_JSON, load_channel_config, read_json, log,
)

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
REQUEST_SLEEP_SECONDS = 8   # be polite to the free, no-key anonymous tier
MAX_RETRIES = 3

# Tamil-capable font (installed via `fonts-lohit-taml` in the workflow).
# Falls back to DejaVu (no Tamil glyphs, but won't crash) if not found.
TAMIL_FONT_PATH = "/usr/share/fonts/truetype/lohit-tamil/Lohit-Tamil.ttf"
FALLBACK_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def build_prompt(art_style: str, character_sheet: str, visual: str) -> str:
    parts = [p for p in [character_sheet, visual, art_style] if p]
    return ", ".join(parts)


def episode_seed(script: dict) -> int:
    """One stable seed per episode (derived from its title), shared by every
    scene so the overall palette/style stays consistent across the short."""
    basis = script.get("title_seed", "") or script.get("theme", "wonderpop")
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 1_000_000


def try_pollinations(prompt: str, width: int, height: int, seed: int, out_path):
    encoded = urllib.parse.quote(prompt)
    url = POLLINATIONS_URL.format(prompt=encoded)
    params = {"width": width, "height": height, "seed": seed, "nologo": "true", "model": "flux"}
    resp = requests.get(url, params=params, timeout=90)
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "")
    if "image" not in content_type:
        raise RuntimeError(f"Unexpected content-type: {content_type}")
    out_path.write_bytes(resp.content)


def load_best_font(size: int) -> ImageFont.FreeTypeFont:
    for path in (TAMIL_FONT_PATH, FALLBACK_FONT_PATH):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def fallback_card(text: str, width: int, height: int, out_path, bg_rgb):
    """Draws a simple, readable placeholder card offline with Pillow."""
    img = Image.new("RGB", (width, height), bg_rgb)
    draw = ImageDraw.Draw(img)
    font = load_best_font(54)

    wrapped = textwrap.fill(text, width=22)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align="center")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.multiline_text(
        ((width - tw) / 2, (height - th) / 2), wrapped, font=font,
        fill=(255, 255, 255), align="center",
    )
    img.save(out_path, "JPEG", quality=90)


def main():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    channel = load_channel_config()
    script = read_json(SCRIPT_JSON)
    width, height = channel["resolution"]
    art_style = channel["art_style"]
    character_sheet = script.get("character_sheet", "")
    seed = episode_seed(script)
    log(f"Episode seed: {seed} (shared across all scenes for visual consistency)")

    # A small rotating palette so fallback cards still look intentional.
    palette = [(91, 134, 229), (229, 134, 91), (134, 229, 145), (200, 110, 200)]

    for i, scene in enumerate(script["scenes"]):
        out_path = IMAGES_DIR / f"scene_{scene['id']}.jpg"
        prompt = build_prompt(art_style, character_sheet, scene["visual"])

        done = False
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                log(f"Scene {scene['id']}: requesting image from Pollinations (attempt {attempt})")
                try_pollinations(prompt, width, height, seed, out_path)
                done = True
                break
            except Exception as e:
                log(f"Scene {scene['id']}: Pollinations attempt {attempt} failed: {e}")
                time.sleep(REQUEST_SLEEP_SECONDS)

        if not done:
            log(f"Scene {scene['id']}: falling back to a local placeholder image.")
            fallback_card(
                scene["narration"], width, height, out_path,
                palette[i % len(palette)],
            )

        # Stay well under the anonymous rate limit before the next request.
        time.sleep(REQUEST_SLEEP_SECONDS)

    log(f"Wrote {len(script['scenes'])} scene images to {IMAGES_DIR}")


if __name__ == "__main__":
    main()