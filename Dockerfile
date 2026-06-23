# Backend container for the TaxCalamity wealth-advisory API.
# Build context is the repo root so that the `backend.app...` absolute imports
# resolve (the code uses namespace packages with no __init__.py).
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install dependencies first for better layer caching.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application code.
COPY backend ./backend

EXPOSE 8000

# Render (and most PaaS) inject $PORT; default to 8000 locally. Single worker
# keeps the SQLite checkpointer consistent.
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
