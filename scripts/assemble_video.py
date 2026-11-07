"""
Step 5 of 6 — Assemble the final video with FFmpeg.

For each scene, in order:
  * If output/video_clips/scene_<id>.mp4 exists (an AI-animated clip,
    optionally produced by the Kaggle notebook — see notebooks/ and
    generate_video_clips.yml), it is used as the scene's visual.
  * Otherwise we fall back to an animated "Ken Burns" slow pan/zoom over
    the scene's static image (output/images/scene_<id>.jpg). This is the
    default path and needs no AI video generation at all.

Each rendered scene gets its own voiceover track muxed in, matched to
its exact duration. Scenes are then concatenated and the full subtitle
track is burned in as one final pass.

Output: output/final_short.mp4
"""
import subprocess

from common import (
    IMAGES_DIR, AUDIO_DIR, VIDEO_CLIPS_DIR, SCENES_RENDERED_DIR,
    SCRIPT_JSON, DURATIONS_JSON, SUBTITLES_SRT, FINAL_VIDEO, OUTPUT_DIR,
    load_channel_config, read_json, log, fail,
)


def run_ffmpeg(args: list, step: str):
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args
    log(f"{step}: running ffmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        fail(f"{step} failed.\nCommand: {' '.join(cmd)}\nstderr:\n{result.stderr}")


def render_scene_from_image(image_path, audio_path, duration, w, h, fps, out_path):
    frames = max(1, int(duration * fps))
    filter_complex = (
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},"
        f"zoompan=z='min(zoom+0.0015,1.2)':d={frames}:s={w}x{h}:fps={fps}[v]"
    )
    run_ffmpeg([
        "-loop", "1", "-framerate", str(fps), "-i", str(image_path),
        "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        "-t", str(duration), "-shortest",
        str(out_path),
    ], step=f"render {out_path.name} (image slideshow)")


def render_scene_from_clip(clip_path, audio_path, duration, w, h, fps, out_path):
    filter_complex = (
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},fps={fps}[v]"
    )
    run_ffmpeg([
        "-stream_loop", "-1", "-i", str(clip_path),
        "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        "-t", str(duration), "-shortest",
        str(out_path),
    ], step=f"render {out_path.name} (AI video clip)")


def main():
    channel = load_channel_config()
    w, h = channel["resolution"]
    fps = channel["fps"]
    script = read_json(SCRIPT_JSON)
    durations = read_json(DURATIONS_JSON)

    SCENES_RENDERED_DIR.mkdir(parents=True, exist_ok=True)
    rendered_paths = []

    for scene in script["scenes"]:
        sid = scene["id"]
        duration = durations.get(str(sid), 3.0)
        audio_path = AUDIO_DIR / f"scene_{sid}.mp3"
        out_path = SCENES_RENDERED_DIR / f"scene_{sid}.mp4"
        clip_path = VIDEO_CLIPS_DIR / f"scene_{sid}.mp4"

        if clip_path.exists():
            log(f"Scene {sid}: AI video clip found — using it instead of the slideshow fallback.")
            render_scene_from_clip(clip_path, audio_path, duration, w, h, fps, out_path)
        else:
            image_path = IMAGES_DIR / f"scene_{sid}.jpg"
            render_scene_from_image(image_path, audio_path, duration, w, h, fps, out_path)

        rendered_paths.append(out_path)

    # Concatenate all scenes (all share identical codec/resolution/fps, so a
    # plain stream copy concat works and is fast).
    concat_list_path = OUTPUT_DIR / "concat_list.txt"
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for p in rendered_paths:
            f.write(f"file '{p.resolve()}'\n")

    concatenated_path = OUTPUT_DIR / "concatenated.mp4"
    run_ffmpeg([
        "-f", "concat", "-safe", "0", "-i", str(concat_list_path),
        "-c", "copy", str(concatenated_path),
    ], step="concatenate scenes")

    # Burn in subtitles as the final pass.
    if SUBTITLES_SRT.exists() and SUBTITLES_SRT.stat().st_size > 0:
        srt_escaped = str(SUBTITLES_SRT.resolve()).replace(":", "\\:")
        style = (
            "FontName=DejaVu Sans,FontSize=20,Bold=1,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,BorderStyle=3,Outline=2,Shadow=0,"
            "Alignment=2,MarginV=160"
        )
        run_ffmpeg([
            "-i", str(concatenated_path),
            "-vf", f"subtitles='{srt_escaped}':force_style='{style}'",
            "-c:a", "copy",
            str(FINAL_VIDEO),
        ], step="burn in subtitles")
    else:
        log("No subtitles found — copying concatenated video as the final file.")
        run_ffmpeg(["-i", str(concatenated_path), "-c", "copy", str(FINAL_VIDEO)], step="finalize")

    log(f"Final video ready: {FINAL_VIDEO}")


if __name__ == "__main__":
    main()
