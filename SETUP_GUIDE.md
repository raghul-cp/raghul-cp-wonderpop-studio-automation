# Setup guide (beginner-friendly, ~30–45 minutes, one-time)

You will do all of this through web pages and one short local command —
nothing heavy runs on your Windows 10 laptop. By the end, GitHub will
generate a new WonderPop Studio Short every time you tell it to, and
upload it to YouTube as **Private** only after you've watched it and
clicked a button yourself.

## 0. What you'll need

- A GitHub account (free) — https://github.com/join
- A Google account that owns (or can manage) the WonderPop Studio YouTube channel
- 15 minutes with your laptop for one local step (getting a YouTube token)
- Nothing else. No credit card anywhere in this guide.

---

## 1. Create the repository

1. On GitHub, click **New repository**.
2. Name it whatever you like (e.g. `wonderpop-studio-automation`).
3. **Public is recommended.** On GitHub's free plan, public repos get
   *unlimited* free Actions minutes; private repos are capped at 2,000
   minutes/month (still plenty for a couple of Shorts a week, but public
   is the simplest choice if you don't mind the code being visible — your
   secrets stay hidden either way, see step 4).
4. Upload every file from this project into it (drag-and-drop on
   GitHub's web UI works fine, or `git push` if you're comfortable with
   Git).

---

## 2. Get a free Groq API key (script + metadata writing)

Groq runs fast AI models for free, no credit card.

1. Go to https://console.groq.com and sign up.
2. Go to **API Keys** → **Create API Key**. Copy it.
3. You'll paste this into GitHub Secrets in step 4.

Model names on Groq's free tier do shift over time. If `generate_script.py`
or `generate_metadata.py` ever errors with a "model not found" style
message, check https://console.groq.com/docs/models for a current free
model name and set it as the `GROQ_MODEL` secret (step 4) — no code
changes needed.

> If you skip this step entirely, the pipeline still works — it falls
> back to a simple built-in story template instead of AI-written ones.

---

## 3. Set up the YouTube Data API (for uploading)

This step is the fiddliest part, but it's free and only needs doing once.

### 3a. Create a Google Cloud project and enable the API
1. Go to https://console.cloud.google.com and create a new project (any name).
2. Go to **APIs & Services → Library**, search **YouTube Data API v3**, click **Enable**.

### 3b. Configure the OAuth consent screen
1. Go to **APIs & Services → OAuth consent screen**.
2. Choose **External**, fill in an app name (e.g. "WonderPop Studio Automation") and your email, and save.
3. Leave it in **Testing** mode — you don't need to publish it. Under **Test users**, add the Google account that owns the YouTube channel.

### 3c. Create an OAuth Client ID
1. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
2. Application type: **Desktop app**.
3. Download the resulting JSON file (e.g. `client_secret.json`) to your laptop.

### 3d. Get a refresh token (one local command)
On your laptop (Windows 10 is fine — this is a normal, lightweight Python script, not an AI model):
A browser window opens. Sign in with the account from step 3b and
approve access. The terminal then prints three values:
Keep this terminal window open — you'll copy these into GitHub Secrets next.

---

## 4. Add your secrets to GitHub

In your repo: **Settings → Secrets and variables → Actions → New repository secret.**
Add each of these (names must match exactly):

| Secret name | Value |
|---|---|
| `GROQ_API_KEY` | from step 2 |
| `YT_CLIENT_ID` | from step 3d |
| `YT_CLIENT_SECRET` | from step 3d || `YT_CLIENT_SECRET` | from step 3d |
| `YT_REFRESH_TOKEN` | from step 3d |

Secrets are encrypted and never shown in logs — this is the one safe
place credentials live in this whole project. They are never committed
to the repo itself.

---

## 5. Make it yours

Open `config/channel.yml` and adjust:
- `niche` — what WonderPop Studio's Shorts are actually about
- `art_style` — the consistent illustration look
- `voice` — the edge-tts narrator voice (see the comment in that file for how to list options)
- `target_scene_count` / `max_total_seconds` — pacing

Open `config/themes.yml` and replace the example story premises with
your own. The pipeline rotates through this list one at a time.

---

## 6. Test run

1. In your repo, go to the **Actions** tab.
2. Click **1 - Generate Short (draft for review)** → **Run workflow**.
3. Wait a few minutes. When it finishes, open the run and scroll down to
   **Artifacts** — download `wonderpop-draft-<run id>`.
4. Unzip it and watch `final_short.mp4`. Check `metadata.json` for the
   generated title/description/tags.

If anything fails, click into the failed step's log — every script in
this project logs plainly what it was doing when it stopped. The
**Troubleshooting** section below covers the common cases.

---

## 7. Review, then upload

This project's rule is simple: **nothing reaches YouTube without you
watching it first and clicking a second, separate button.**

1. Happy with the draft? Note its run ID (it's in the run's URL, and
   also printed in that run's summary page).
2. Go to **Actions → 2 - Upload Short to YouTube → Run workflow**, paste
   in that run ID, and run it.
3. It uploads straight to your channel as **Private**.

### Important: about going public

Google automatically locks any video uploaded through the API by an
*unaudited* app to Private — permanently, until you resolve it, no
matter what status the code requests. This isn't a bug in this
project; it's a standing Google policy for all third-party API
uploaders. You have two free options:

- **Easiest:** once you're happy with a video, just upload the same
  `final_short.mp4` yourself through the normal YouTube Studio website
  or app (not through this project), pasting in the title/description/tags
  from `metadata.json`. This takes under a minute and doubles as your
  review step anyway.
- **If you want the API upload itself to go public:** request Google's
  free compliance audit for your Cloud project — search Google's
  developer docs for "YouTube API Services audit" for the current
  request form. It's free but can take some time to process, and is
  really meant for apps with many users, so it's optional overkill for
  a single personal channel.

Either way, nothing is ever force-published without your say-so.

---

## 8. Optional: real AI-animated video clips (advanced)

By default, every Short uses a gentle pan-and-zoom ("Ken Burns") effect
over the generated scene images — reliable, needs no GPU, and is the
"animated slideshow" fallback this project is built around.

If you want actual AI-generated motion instead, you can opt into a free
Kaggle GPU notebook:

1. Create a free Kaggle account at https://www.kaggle.com.
2. Go to **Settings → API → Create New Token**; it downloads a `kaggle.json`
   containing your username and key.
3. Add `KAGGLE_USERNAME` and `KAGGLE_KEY` as GitHub Secrets (step 4).
4. After step 6's test run, go to **Actions → 1b - (Optional) Animate
   scenes with AI video on Kaggle → Run workflow**, paste in the same
   run ID, and run it. It sends your scene images to a free Kaggle T4
   GPU, animates each one, and replaces the draft artifact with an
   animated version. Continue with step 7 as normal afterwards.

Be aware: this adds real complexity — a large model download, several
minutes of GPU time, and occasional flakiness, since free video-generation
model availability shifts faster than any guide can track (the notebook's
comments flag exactly where to swap in a current model if needed). Kaggle
also caps free GPU time at 30 hours/week. None of this is required —
skip it entirely and the slideshow path just keeps working.

---

## Costs

| Service | Used for | Free-tier limit (at time of writing) |
|---|---|---|
| Groq API | Script + metadata writing | No credit card; ~14,400 requests/day |
| Pollinations.ai | Scene illustrations | No key/signup; light anonymous rate limit (handled automatically with retries) |
| edge-tts | Voiceover narration | Free, no key, no cap — a wrapper around Microsoft Edge's read-aloud service |
| GitHub Actions | Scheduling + running everything | Unlimited on public repos; 2,000 min/month + 500 MB artifact storage on private repos (free plan) |
| YouTube Data API v3 | Uploading | Free; default quota allows ~6 uploads/day (each upload costs 1,600 of your 10,000 daily units) |
| Kaggle (optional) | AI video clip generation | Free; 30 GPU-hours/week |

With the default 2x/week schedule, every service above stays far under
its free limit.

---

## Troubleshooting

- **"Groq call failed" / model not found** — your free-tier model name
  may have changed; set `GROQ_MODEL` in Secrets to a current one from
  https://console.groq.com/docs/models. The pipeline still finishes
  either way, using its built-in template fallback.
- **Scene images look like plain colored cards with text** — Pollinations
  was unreachable or rate-limited and the offline Pillow fallback kicked
  in. Usually resolves itself next run; if it's constant, try registering
  a free account at https://auth.pollinations.ai to raise the anonymous
  rate limit.
- **`ffmpeg: command not found`** — only happens if you removed the
  "Install ffmpeg" step from the workflow; it's required and already
  included.
- **Upload step fails with an auth error** — your refresh token may have
  been revoked (e.g. you removed the app's access in your Google
  account). Redo step 3d to get a fresh one.
- **Video uploaded but you can't find it as Public** — see "Important:
  about going public" in step 7; this is expected Google API behavior,
  not an error.
- **Kaggle step times out or errors** — check that step's log; the most
  common cause is the model name in `notebooks/kaggle_scene_animator.ipynb`
  having been retired upstream. It's fully optional — just skip to step
  7 and the slideshow version still uploads fine.
