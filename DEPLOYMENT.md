# Deployment Guide — AI Fake News Detector

The app is a **single Python service** — FastAPI serves the API, the chat UI, and the
static files, so there is no separate frontend to build or host.

Before any deployment, make sure you have real API keys ready (from `.env`):

- `TAVILY_API_KEY` (or `SERPER_API_KEY`) — required for live evidence retrieval
- `OPENAI_API_KEY` or `GROQ_API_KEY` — optional, enables LLM explanations

**Never commit `.env` or real keys.** Inject them as platform environment variables.

---

## Option 1 — Render (one click, recommended)

A `render.yaml` blueprint is included, so:

1. Push this repo to GitHub.
2. Go to https://render.com → **New** → **Blueprint** → connect the repo.
3. Render reads `render.yaml`, creates the web service, and starts deploying.
4. After the first deploy, open the service → **Environment** and set the secrets
   (marked `sync: false` in the blueprint):
   `TAVILY_API_KEY`, `SERPER_API_KEY`, `OPENAI_API_KEY`, `GROQ_API_KEY`.
5. Click **Deploy** again and open the generated `https://<name>.onrender.com/chat`.

Notes:

- Render free services **sleep after inactivity** — the first request after sleep
  takes ~30–60 seconds to wake up.
- The start command uses `$PORT`, which Render injects automatically.

## Option 2 — Railway

1. Go to https://railway.app → **New Project** → **Deploy from GitHub** → this repo.
2. Railway reads `railway.toml` (build + start commands).
3. Add the secret variables in the **Variables** tab.
4. Open the generated URL (`/chat` for the UI, `/docs` for the API).

## Option 3 — Docker (any host: VPS, Hugging Face Spaces, Fly.io)

```bash
docker build -t ai-fake-news-detector .
docker run -p 8000:8000 --env-file .env ai-fake-news-detector
```

- The image listens on port 8000. Use a platform port override where required
  (e.g. on Fly.io / Spaces, run `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`).
- `.dockerignore` keeps `.env`, `.venv`, caches, and tests out of the image.

## Option 4 — VPS (DigitalOcean / Hetzner / EC2)

```bash
sudo apt update && sudo apt install -y python3-venv nginx git
cd /opt && git clone <your-repo-url> hackathon_project
cd hackathon_project
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env        # paste real keys
```

Create `/etc/systemd/system/factcheck.service`:

```ini
[Unit]
Description=AI Fake News Detector
After=network.target

[Service]
WorkingDirectory=/opt/hackathon_project
ExecStart=/opt/hackathon_project/.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now factcheck
```

Then add an nginx site:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## Post-deploy checks

| Check | URL |
|-------|-----|
| Health | `GET /health` → `{"status": "healthy", ...}` |
| Chat UI | `/<base>/chat` |
| API docs | `/<base>/docs` |
| Fact-check | `POST /<base>/api/fact-check` with `{"claim": "..."}` |

If every claim returns **UNVERIFIED**, the platform is missing a valid retrieval key
(or the key is wrong — Tavily returns `401` for invalid keys). Check the platform
env vars and restart.

## Known deployment notes

- Chat sessions and the rate limiter are **in-memory** — they reset on restart and
  on multi-worker setups. Keep the default single worker for the demo.
- Health checks: use `/health` (returns 200).
- If your frontend is ever hosted separately, set `CORS_ORIGINS` to your site's origin.
