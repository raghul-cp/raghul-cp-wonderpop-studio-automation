"""
Step 3 of 6 — Generate voiceover narration for every scene.

Uses edge-tts (https://github.com/rany2/edge-tts) — a free Python
library that calls Microsoft Edge's online neural text-to-speech
service. No API key, no account, no cost. It also streams back
word-boundary timestamps, which generate_subtitles.py uses to build
perfectly synced captions without needing any speech-recognition model.

Output:
  output/audio/scene_<id>.mp3
  output/audio/scene_<id>_words.json   (word, start_ms, end_ms — relative to scene start)
  output/durations.json                (scene id -> duration in seconds)
"""
import asyncio

import edge_tts

from common import (
    AUDIO_DIR, SCRIPT_JSON, DURATIONS_JSON, load_channel_config,
    read_json, write_json, ffprobe_duration_seconds, log,
)


async def synthesize_scene(text: str, voice: str, rate: str, mp3_path, words_path):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    words = []
    with open(mp3_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset/duration arrive in 100-nanosecond units.
                start_ms = chunk["offset"] / 10_000
                end_ms = start_ms + (chunk["duration"] / 10_000)
                words.append({
                    "word": chunk["text"],
                    "start_ms": round(start_ms),
                    "end_ms": round(end_ms),
                })
    write_json(words_path, words)


async def main_async():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    channel = load_channel_config()
    script = read_json(SCRIPT_JSON)
    voice = channel["voice"]
    rate = channel.get("voice_rate", "+0%")

    durations = {}
    for scene in script["scenes"]:
        sid = scene["id"]
        mp3_path = AUDIO_DIR / f"scene_{sid}.mp3"
        words_path = AUDIO_DIR / f"scene_{sid}_words.json"
        log(f"Scene {sid}: synthesizing voiceover ({voice})")
        try:
            await synthesize_scene(scene["narration"], voice, rate, mp3_path, words_path)
        except Exception as e:
            log(f"Scene {sid}: edge-tts failed ({e}). Retrying once with default rate.")
            await synthesize_scene(scene["narration"], voice, "+0%", mp3_path, words_path)

        durations[str(sid)] = ffprobe_duration_seconds(mp3_path)
        log(f"Scene {sid}: duration {durations[str(sid)]:.2f}s")

    write_json(DURATIONS_JSON, durations)
    log(f"Wrote {DURATIONS_JSON}")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()