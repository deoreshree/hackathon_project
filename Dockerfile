# AI Fake News Detector — container image.
# Build:  docker build -t ai-fake-news-detector .
# Run:    docker run -p 8000:8000 --env-file .env ai-fake-news-detector

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code. Secrets (.env) are NEVER copied into the image —
# inject them at runtime via --env-file or platform env vars.
COPY backend ./backend
COPY rag ./rag
COPY static ./static
COPY .env.example ./.env.example

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
