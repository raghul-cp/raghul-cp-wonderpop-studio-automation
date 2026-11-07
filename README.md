# WonderPop Studio — free YouTube Shorts automation

Generates short cartoon stories end-to-end — script, scene art, voiceover,
synced subtitles, a finished vertical video, and YouTube metadata — on a
schedule, using only free tools. Nothing heavy runs on your laptop; the
whole pipeline runs in GitHub Actions' free cloud runners. **Every upload
requires you to manually review the draft and click "Run workflow" a
second time** — nothing ever goes to YouTube automatically.

**New here? Start with [SETUP_GUIDE.md](SETUP_GUIDE.md)** for the full
click-by-click setup (about 30–45 minutes, one time).

## How it works
┌─────────────────────────── GitHub Actions (free, scheduled) ───────────────────────────┐
│ │
│ 1. generate_script.py → story + per-scene narration & art prompts (Groq, free) │
│ 2. generate_images.py → one illustration per scene (Pollinations.ai, free) │
│ 3. generate_voiceover.py → narration audio + word timings (edge-tts, free) │
│ 4. generate_subtitles.py → synced .srt from those word timings (no AI needed) │
│ 5. assemble_video.py → Ken Burns slideshow + voice + burned-in subs (FFmpeg) │
│ 6. generate_metadata.py → title / description / tags (Groq, free) │
│ │
│ → uploaded as a downloadable “draft” artifact, NOT to YouTube │
└──────────────────────────────────────────────────────────────────────────────────────────┘
│
you watch the draft, decide
│
▼
┌──────────────────── “2 - Upload Short to YouTube” (manual only) ───────────────────────┐
│ upload_youtube.py → uploads to YOUR channel as Private via the YouTube Data API │
└──────────────────────────────────────────────────────────────────────────────────────────┘
An optional, more advanced path (`1b - Animate scenes with AI video on Kaggle`)
swaps the static-image slideshow for real AI-animated video clips, rendered
for free on Kaggle's GPU notebooks. It's entirely opt-in — skip it and the
slideshow path above runs by default every time.

## What costs money here

Nothing, as configured. See the cost table in [SETUP_GUIDE.md](SETUP_GUIDE.md#costs)
for the specific free-tier limit of every service used (Groq, Pollinations.ai,
edge-tts, GitHub Actions, the YouTube Data API, and optionally Kaggle).

## Repo layout

| Path | What it's for |
|---|---|
| `config/channel.yml` | Channel name, art style, voice, video length — edit this first |
| `config/themes.yml` | The pool of story premises to rotate through |
| `scripts/` | The pipeline, one script per step (see diagram above) |
| `notebooks/kaggle_scene_animator.ipynb` | Optional: real AI video clips via Kaggle |
| `.github/workflows/` | The 3 GitHub Actions workflows |
| `.env.example` | Every secret the project needs, with no real values |

## Customizing

Everything your channel's "voice" depends on lives in `config/channel.yml`
and `config/themes.yml` — no code changes needed to change the niche, art
style, narrator voice, or story ideas.
