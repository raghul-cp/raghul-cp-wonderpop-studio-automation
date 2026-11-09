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
    per_scene_seconds = max_seconds // n

    # A single triple-quoted block on purpose: one long string made of many
    # short adjacent-quoted lines is fragile to copy/paste (a line wrapped
    # mid-string by a phone or editor breaks the syntax). A triple-quoted
    # string tolerates stray line breaks fine since real newlines are valid
    # inside it. Double braces ({{ }}) below are literal JSON braces, since
    # this is an f-string.
    user_content = f"""Channel: {channel['channel_name']}. Niche: {channel['niche']}
Write a {n}-scene short cartoon story based on this premise: {theme}
The whole story will be narrated aloud and must fit in about {max_seconds} seconds total (roughly {per_scene_seconds} seconds of narration per scene, so keep each narration line SHORT, 1 to 2 simple sentences).

IMPORTANT: two different languages are needed.
- narration fields: write these in {language} (native script), since this is what the viewer hears and reads as captions.
- visual and character_sheet fields: write these in ENGLISH only, regardless of the story's language, since they are prompts for an image-generation model which follows English far more reliably. The viewer never sees this text directly.

character_sheet must be ONE detailed paragraph, in English, fixing the main character's species or type, exact colors, outfit, and any distinguishing features, in this visual style: {art_style}. Every scene's visual field must describe that same character consistently, reusing the same descriptive terms, so the character looks like the same individual in every scene, just in a different pose or setting.

Return JSON with this exact shape:
{{
  "title_seed": "a short working title, in English",
  "theme": "the premise restated in a few words, in English",
  "character_sheet": "fixed English visual description of the main character, reused in every scene",
  "scenes": [
    {{"id": 1, "narration": "spoken line in {language}", "visual": "English scene description, including the character from character_sheet, no text or words in the image"}}
  ]
}}
Include exactly {n} scenes, ids 1 through {n}."""

    return [
        {
            "role": "system",
            "content": (
                "You are a children's cartoon story writer for a YouTube Shorts "
                "channel. You always respond with STRICT JSON only, no markdown, "
                "no commentary, no code fences."
            ),
        },
        {"role": "user", "content": user_content},
    ]


def extract_json(raw: str) -> dict:
    # Strip markdown code fences if the model added them anyway.
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def fallback_script(channel: dict, theme: str) -> dict:
    """A simple, zero-dependency template so the pipeline always produces
    *something* usable even without an LLM. Stays in English and is
    intentionally plain — this is a safety net, not the main path. If you
    see this kind of output in your final video, it means the Groq call
    failed for every model in common.GROQ_MODEL_CANDIDATES — check that
    step's log for the real reason."""
    log("Using local fallback script generator (no AI).")
    n = channel["target_scene_count"]
    beats = [
        "Our hero is introduced, going about an ordinary day.",
        "Something unexpected happens that causes a small problem.",
        "The hero tries to solve it alone and struggles.",
        "A friend offers a new way to look at things.",
        "The hero tries again, this time with a different approach.",
        "The problem is resolved and the hero feels proud.",
        "The hero shares what they learned with someone else.",
        "The story ends on a warm, hopeful note.",
    ]
    chosen = (beats * ((n // len(beats)) + 1))[:n]
    character_sheet = (
        f"the main character from this story: {theme.split('.')[0]}, "
        "consistent design across every scene"
    )
    # NOTE: "visual" deliberately does NOT repeat character_sheet here —
    # generate_images.py already prepends character_sheet to every scene's
    # prompt itself, so baking it in here too would duplicate it.
    scenes = [
        {
            "id": i + 1,
            "narration": chosen[i],
            "visual": f"scene showing: {chosen[i]}",
        }
        for i in range(n)
    ]
    return {
        "title_seed": theme.split(".")[0][:60],
        "theme": theme,
        "character_sheet": character_sheet,
        "scenes": scenes,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    channel = load_channel_config()
    themes = load_themes()
    theme = pick_theme(themes)
    log(f"Theme for this run: {theme}")

    script = None
    try:
        raw = call_groq_chat(build_prompt(channel, theme))
        script = extract_json(raw)
        assert "scenes" in script and len(script["scenes"]) > 0
        script.setdefault("character_sheet", "")
        log(f"Generated script via Groq with {len(script['scenes'])} scenes.")
    except Exception as e:
        log(f"Groq script generation failed on every model: {e}")
        script = fallback_script(channel, theme)

    script["channel"] = channel["channel_name"]
    write_json(SCRIPT_JSON, script)
    log(f"Wrote {SCRIPT_JSON}")


if __name__ == "__main__":
    main()