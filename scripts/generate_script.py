"""
Step 1 of 6 — Generate the cartoon story: narration lines + scene (image)
prompts, broken into short scenes for a YouTube Short.

Narration is written in channel.yml's story_language (Tamil by default).
Image prompts (visual / character_sheet) stay in English internally, since
image-generation models follow English prompts far more reliably — the
viewer never sees that text, only the art it produces.

A fixed "character_sheet" is generated once per story and repeated into
every single scene's image prompt in generate_images.py, so the same
character(s) stay visually consistent scene to scene instead of a new
random look each time.

Primary path: free Groq API (no credit card, generous daily free limit;
now tries several model names in common.py so one retirement doesn't
take down the whole pipeline).
Fallback: a local template generator, so the pipeline never hard-fails
even if Groq is unreachable or GROQ_API_KEY is missing. The fallback
stays in English — it's a last-resort safety net, not the main path, so
getting Groq working is what actually gets you Tamil episodes.

Output: output/script.json
"""
import json
import random
import re

from common import (
    OUTPUT_DIR, SCRIPT_JSON, CONFIG_DIR,
    load_channel_config, load_themes, write_json, log, call_groq_chat, fail,
)


def pick_theme(themes: list) -> str:
    """Round-robins through config/themes.yml using a small state file."""
    state_file = CONFIG_DIR / ".theme_index"
    idx = 0
    if state_file.exists():
        try:
            idx = (int(state_file.read_text().strip()) + 1) % len(themes)
        except ValueError:
            idx = 0
    else:
        idx = random.randrange(len(themes))
    state_file.write_text(str(idx))
    return themes[idx]


def build_prompt(channel: dict, theme: str) -> list:
    n = channel["target_scene_count"]
    max_seconds = channel["max_total_seconds"]
    language = channel.get("story_language", "English")
    art_style = channel["art_style"]
    return [
        {
            "role": "system",
            "content": (
                "You are a children's cartoon story writer for a YouTube Shorts "
                "channel. You always respond with STRICT JSON only — no markdown, "
                "no commentary, no code fences."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Channel: {channel['channel_name']}. Niche: {channel['niche']}\n"
                f"Write a {n}-scene short cartoon story based on this premise: {theme}\n"
                f"The whole story will be narrated aloud and must fit in about "
                f"{max_seconds} seconds total (roughly {max_seconds // n} seconds "
                "of narration per scene, so keep each narration line SHORT — "
                "1 to 2 simple sentences).\n\n"
                f"IMPORTANT — two different languages are needed:\n"
                f'- "narration" fields: write these in {language} (native script), '
                f"since this is what the viewer hears and reads as captions.\n"
                '- "visual" and "character_sheet" fields: write these in ENGLISH '
                "only, regardless of the story's language — they are prompts for "
                "an image-generation model, which follows English far more "
                "reliably, and the viewer never sees this text directly.\n\n"
                f'"character_sheet" must be ONE detailed