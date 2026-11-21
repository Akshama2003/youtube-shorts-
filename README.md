# YT Shorts Studio

Ek poori AI "creator team" jo PowerShell se chalti hai: trending topic dhundhti hai, research karti hai, script likhti hai, voice-over karti hai, video edit karke subtitles lagati hai, compliance check karti hai, aur phir YouTube pe upload kar deti hai.

## Team (har role ek agent)

| # | Agent | Kaam |
|---|-------|------|
| 1 | Trend Scout | Google Trends se topic chunta hai (sensitive / risky topics reject) |
| 2 | Research Analyst | Sirf pakke facts ki fact-sheet banata hai (no invented stats) |
| 3 | Scriptwriter | Hook + scene-by-scene original script |
| 4 | SEO & Packaging | Title, description, tags, hashtags, pinned comment idea |
| 5 | Voice Artist | Free Microsoft neural voice (Hindi/English), word timings ke saath |
| 6 | Visual Director | Pexels / Pixabay royalty-free footage; na mile to khud ke generated cards |
| 7 | Video Editor | 1080x1920 vertical, word-highlight subtitles, loudness normalize |
| 8 | QA & Compliance | Technical + copyright + YouTube policy + fact review. Fail = rewrite loop |
| 9 | Publisher | YouTube Data API se upload (AI disclosure ke saath) |

```
Scout -> Researcher -> Writer -> SEO -> Voice -> Visuals -> Editor -> QA --pass--> Publisher
                          ^                                          |
                          +------------- feedback (rewrite) ---------+  (max MAX_REVISIONS)
```

## 1. Clone + setup (Windows PowerShell)

```powershell
git clone https://github.com/<your-username>/yt-shorts-studio.git
cd yt-shorts-studio
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
notepad .env
.\.venv\Scripts\python.exe main.py doctor
```

`setup.ps1` Python venv, packages aur FFmpeg (winget se) install kar deta hai. FFmpeg install hone ke baad PowerShell band karke dobara kholo.

## 2. Keys

- **ANTHROPIC_API_KEY**: https://console.anthropic.com -> API Keys
- **Stock footage key (optional, quality behtar)**: `PIXABAY_API_KEY` (free account, https://pixabay.com/api/docs/) ya `PEXELS_API_KEY` (https://www.pexels.com/api/, kabhi kabhi key issuance paused hoti hai). Dono ho to dono use hote hain. Koi key na ho to Wikimedia Commons ki sirf public-domain/CC0 images use hoti hain (kam variety), aur wo bhi na mile to generated cards.
- **YouTube** (ek baar):
  1. https://console.cloud.google.com -> naya project
  2. "YouTube Data API v3" enable karo
  3. OAuth consent screen banao (External), apna Gmail "Test user" me add karo
  4. Credentials -> Create OAuth client ID -> **Desktop app** -> JSON download
  5. File ka naam `client_secret.json` karke project folder me rakho
  6. `.\.venv\Scripts\python.exe main.py auth` chalao, browser me login karo

## 3. Run

```powershell
.\scripts\run.ps1 -Count 1 -NoPublish      # pehle test: video banao, upload mat karo
.\scripts\run.ps1 -Count 1                 # banao + QA + upload
.\scripts\run.ps1 -Count 3                 # 3 videos
.\scripts\run.ps1 -Topic "Why is the sky blue"
.\.venv\Scripts\python.exe main.py trends  # aaj ke trends dekho
.\.venv\Scripts\python.exe main.py publish output\<job-folder>   # approved video baad me upload
```

Roz automatic chalane ke liye:

```powershell
.\scripts\schedule.ps1 -Time "18:00" -Count 1
```

Har video ka folder `output\<date>-<topic>\` me milta hai: `final.mp4`, `script.json`, `seo.json`, `qa.json`, `assets.json` (har clip ka license record).

## 4. Settings (`.env`)

| Key | Matlab |
|-----|--------|
| `LANGUAGE` | `hi` (Hindi, Devanagari) ya `en` |
| `VOICE` | khali = default. Jaise `hi-IN-MadhurNeural`, `en-US-AndrewNeural` |
| `TARGET_SECONDS` / `MAX_SECONDS` | 45 / 58 |
| `YT_PRIVACY` | `private` / `unlisted` / `public` |
| `AUTO_PUBLISH` | `false` = sirf banao, upload manually karo |
| `DISCLOSE_AI` | `true` = "altered/synthetic content" label + description note |
| `MAX_REVISIONS` | QA reject ke baad kitni baar script dobara likhe |

Background music: royalty-free `.mp3` files `assets\music\` me daalo (sirf wahi jinka license aapke paas ho). Folder khali hai to music nahi lagta.

## 5. Push to your own GitHub

```powershell
git init
git add .
git commit -m "YT Shorts Studio"
gh repo create yt-shorts-studio --private --source . --push
```

(`gh` nahi hai to github.com pe empty repo banao aur `git remote add origin ...; git push -u origin main` karo.) `.env`, `token.json`, `client_secret.json` `.gitignore` me hain, push nahi hote.

## 6. Copyright aur YouTube policy: kya covered hai aur kya nahi

Covered:
- Script AI se original likhi jati hai, kisi ka text/lyrics copy nahi.
- Footage sirf Pexels / Pixabay (commercial use free) ya khud ke generated cards; har asset ka license `assets.json` me.
- Voice Microsoft ke free neural TTS se, koi real person ki cloned voice nahi.
- QA har video pe copyright, misinformation, medical/financial advice, harmful content, misleading title check karta hai. Fail hone pe upload hota hi nahi.
- Pichhle videos se similar script reject hoti hai (repetitive content se bachne ke liye).
- AI disclosure on by default.

Dhyan rakhne wali baatein:
- **Koi tool 100% guarantee nahi de sakta.** QA ek AI reviewer hai; shuru ke videos `private` pe upload karke khud dekho, phir `public` karo.
- YouTube ki "inauthentic / mass-produced content" policy low-effort repetitive videos ko demonetize kar sakti hai. Roz 1-3 achhe videos, 20 kachche se behtar.
- Naya Google Cloud project jab tak YouTube ka API audit pass nahi karta, uploaded videos **private lock** ho sakte hain. Audit form: https://support.google.com/youtube/contact/yt_api_form
- Upload quota default 10,000 units/day hai, ek upload ~1,600 units = roughly 6 uploads/day.
- Ye Google Trends RSS use karta hai; agar feed na mile to evergreen topic chunta hai.

## Troubleshooting

- `ffmpeg not found` -> PowerShell band karke dobara kholo, `ffmpeg -version` check karo.
- Hindi subtitles ajeeb dikhein -> `.env` me `SUB_FONT=Nirmala UI`.
- Script `running scripts is disabled` -> `powershell -ExecutionPolicy Bypass -File ...` use karo.
