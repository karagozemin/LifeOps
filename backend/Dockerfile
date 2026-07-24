# LifeOps backend — production image (Render / Railway / Fly / any Docker host)
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY samples ./samples

# Required at runtime:
#   LIFEOPS_PAYTO=0x<your X Layer wallet>   (A2MCP payTo)
#   OKX_API_KEY / OKX_SECRET_KEY / OKX_PASSPHRASE (OKX facilitator)
#   LIFEOPS_REPLAY_DB=/var/data/replays.sqlite3  (persistent replay protection)
# Optional:
#   OPENAI_API_KEY=sk-...                   (deterministic fallback works without it)
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
