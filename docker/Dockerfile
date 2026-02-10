FROM python:3.11-slim

# ---- Python behavior (dev-friendly) ----
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---- Workdir ----
WORKDIR /app

# ---- System deps (kept minimal but flexible for dev) ----
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# ---- Install dependencies first (better layer caching) ----
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

CMD ["bash"]
