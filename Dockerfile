FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Build tooling required by Nuitka on Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    patchelf \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install nuitka

COPY . .

# Build-time launcher so the compiled binary starts uvicorn directly.
RUN printf '%s\n' \
    'import os' \
    'import uvicorn' \
    'from main import app' \
    '' \
    'if __name__ == "__main__":' \
    '    host = os.getenv("HOST", "0.0.0.0")' \
    '    port = int(os.getenv("PORT", "8000"))' \
    '    uvicorn.run(app, host=host, port=port)' \
    > /build/claim_craft.py

# Compile to standalone native executable folder.
RUN python -m nuitka \
    --standalone \
    --follow-imports \
    --assume-yes-for-downloads \
    --output-dir=/build/out \
    --remove-output \
    /build/claim_craft.py


FROM python:3.11-slim AS runtime

ENV APP_HOME=/app \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR ${APP_HOME}

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy only compiled artifacts, not source code.
COPY --from=builder /build/out/claim_craft.dist/ ${APP_HOME}/

EXPOSE 8000

CMD ["./claim_craft.bin"]
