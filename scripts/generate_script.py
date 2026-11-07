"""
Step 1 of 6 — Generate the cartoon story: narration lines + scene (image)
prompts, broken into short scenes for a YouTube Short.

Primary path: free Groq API (no credit card, generous daily free limit).
Fallback: a local template generator, so the pipeline never hard-fails
even if Groq is unreachable or GROQ_API_KEY is missing.

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
                "1 to 2 simple sentences).\n"
                "Return JSON with this exact shape:\n"
                "{\n"
                '  "title_seed": "a short working title",\n'
                '  "theme": "the premise restated in a few words",\n'
                '  "scenes": [\n'
                '    {"id": 1, "narration": "...", "visual": "a vivid, concrete '
                'description of what is drawn in this scene, no text/words in the image"}\n'
                "  ]\n"
                "}\n"
                f"Include exactly {n} scenes, ids 1.." + str(n) + "."
            ),
        },
    ]


def extract_json(raw: str) -> dict:
    # Strip markdown code fences if the model added them anyway.
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def fallback_script(channel: dict, theme: str) -> dict:
    """A simple, zero-dependency template so the pipeline always produces
    *something* usable even without an LLM. Quality is intentionally basic —
    this is a safety net, not the main path."""
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
    scenes = [
        {
            "id": i + 1,
            "narration": f"{chosen[i]} ({theme.split('.')[0]}.)",
            "visual": f"{theme}, scene depicting: {chosen[i]}",
        }
        for i in range(n)
    ]
    return {"title_seed": theme.split(".")[0][:60], "theme": theme, "scenes": scenes}


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
        log(f"Generated script via Groq with {len(script['scenes'])} scenes.")
    except Exception as e:
        log(f"Groq script generation failed: {e}")
        script = fallback_script(channel, theme)

    script["channel"] = channel["channel_name"]
    write_json(SCRIPT_JSON, script)
    log(f"Wrote {SCRIPT_JSON}")


if __name__ == "__main__":
    main()
