"""
Step 4 of 6 — Build a single, timeline-accurate SRT subtitle file for the
whole video, using the word-boundary timestamps edge-tts already gave us
in generate_voiceover.py. No speech-recognition model needed.

Groups words into short on-screen caption chunks (good for Shorts-style
captions) and offsets each scene's word timings by the cumulative
duration of the scenes before it, so the SRT lines up with the final,
concatenated video produced in assemble_video.py.

Output: output/subtitles.srt
"""
from common import (
    AUDIO_DIR, SCRIPT_JSON, DURATIONS_JSON, SUBTITLES_SRT,
    read_json, log,
)

WORDS_PER_CAPTION = 4
MAX_CAPTION_SECONDS = 2.5


def ms_to_srt_time(ms: float) -> str:
    ms = max(0, int(ms))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def chunk_words(words: list) -> list:
    """Groups a scene's words into short caption chunks."""
    chunks = []
    current = []
    chunk_start = None
    for w in words:
        if not current:
            chunk_start = w["start_ms"]
        current.append(w)
        duration_s = (w["end_ms"] - chunk_start) / 1000
        if len(current) >= WORDS_PER_CAPTION or duration_s >= MAX_CAPTION_SECONDS:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    return chunks


def main():
    script = read_json(SCRIPT_JSON)
    durations = read_json(DURATIONS_JSON)

    cumulative_ms = 0.0
    srt_lines = []
    index = 1

    for scene in script["scenes"]:
        sid = scene["id"]
        words_path = AUDIO_DIR / f"scene_{sid}_words.json"
        if words_path.exists():
            words = read_json(words_path)
        else:
            words = []

        if words:
            for chunk in chunk_words(words):
                start = cumulative_ms + chunk[0]["start_ms"]
                end = cumulative_ms + chunk[-1]["end_ms"]
                text = " ".join(w["word"] for w in chunk)
                srt_lines.append(
                    f"{index}\n{ms_to_srt_time(start)} --> {ms_to_srt_time(end)}\n{text}\n"
                )
                index += 1
        else:
            # No word timing available (e.g. edge-tts fallback path) —
            # show the full narration for the scene's whole duration.
            scene_duration_ms = durations.get(str(sid), 3.0) * 1000
            srt_lines.append(
                f"{index}\n{ms_to_srt_time(cumulative_ms)} --> "
                f"{ms_to_srt_time(cumulative_ms + scene_duration_ms)}\n{scene['narration']}\n"
            )
            index += 1

        cumulative_ms += durations.get(str(sid), 3.0) * 1000

    SUBTITLES_SRT.write_text("\n".join(srt_lines), encoding="utf-8")
    log(f"Wrote {SUBTITLES_SRT} ({index - 1} captions)")


if __name__ == "__main__":
    main()
