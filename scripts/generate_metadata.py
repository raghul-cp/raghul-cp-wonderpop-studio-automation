"""
Step 6 of 6 — Generate YouTube metadata (title, description, tags) from
the finished script. Same free Groq path as generate_script.py, with a
template fallback so this step never blocks the pipeline either.

Output: output/metadata.json
"""
import json
import re

from common import (
    SCRIPT_JSON, METADATA_JSON, load_channel_config, read_json,
    write_json, log, call_groq_chat,
)


def build_prompt(channel: dict, script: dict) -> list:
    narration = " ".join(s["narration"] for s in script["scenes"])
    return [
        {
            "role": "system",
            "content": (
                "You write YouTube Shorts metadata. Respond with STRICT JSON "
                "only — no markdown, no commentary, no code fences."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Channel: {channel['channel_name']} ({channel['niche']})\n"
                f"Story: {script.get('theme', '')}\n"
                f"Full narration: {narration}\n\n"
                "Return JSON with this exact shape:\n"
                "{\n"
                '  "title": "a catchy title under 80 characters, include #Shorts",\n'
                '  "description": "2-3 friendly sentences summarizing the story, '
                'end with a few relevant hashtags",\n'
                '  "tags": ["8 to 12 short keyword tags, no # symbol"]\n'
                "}"
            ),
        },
    ]


def extract_json(raw: str) -> dict:
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def fallback_metadata(channel: dict, script: dict) -> dict:
    log("Using local fallback metadata generator (no AI).")
    title = script.get("title_seed", "A WonderPop Studio Short")[:70]
    return {
        "title": f"{title} #Shorts",
        "description": (
            f"{script.get('theme', '')}\n\n"
            f"A {channel['channel_name']} original short. "
            "#shorts #cartoon #animation #kids"
        ),
        "tags": ["shorts", "cartoon", "animation", "kids story", "animated short",
                 channel["channel_name"].lower().replace(" ", "")],
    }


def main():
    channel = load_channel_config()
    script = read_json(SCRIPT_JSON)

    try:
        raw = call_groq_chat(build_prompt(channel, script), max_tokens=500)
        metadata = extract_json(raw)
        assert "title" in metadata and "description" in metadata
        log("Generated metadata via Groq.")
    except Exception as e:
        log(f"Groq metadata generation failed: {e}")
        metadata = fallback_metadata(channel, script)

    metadata.setdefault("tags", [])
    write_json(METADATA_JSON, metadata)
    log(f"Wrote {METADATA_JSON} — title: {metadata['title']}")


if __name__ == "__main__":
    main()
