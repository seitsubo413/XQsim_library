# syntax=docker/dockerfile:1
#
# XQsim Patch Trace Backend (linux/amd64)
#
# - We run on linux/amd64 so the bundled `src/compiler/gridsynth` (ELF x86_64) works.
# - We do NOT change XQsim core logic; container only provides a reproducible runtime.
#
# Apple Silicon (arm64) host: run linux/arm64 natively to avoid qemu crashes.
FROM --platform=linux/arm64 python:3.10-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (keep minimal; wheels exist for most deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    build-essential \
    ghc \
    cabal-install \
    && rm -rf /var/lib/apt/lists/*

# Install python deps
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -U pip && \
    # Keep upstream requirements.txt unchanged; fix platform-specific constraints at build time.
    # - ray==2.5.0 requires grpcio<=1.49.1 on macOS; align here as well for consistency.
    # - stim==1.11.0 fails to build on aarch64 due to x86 flags; install stim separately (wheel-only).
    sed 's/^grpcio==.*/grpcio==1.49.1/' /app/requirements.txt | grep -v '^stim==' > /tmp/requirements-docker.txt && \
    pip install --no-cache-dir -r /tmp/requirements-docker.txt && \
    # Allow source build on aarch64 (wheels may not be published for this platform/Python combo).
    pip install --no-cache-dir stim==1.15.0 && \
    # API server deps (interface layer)
    # NOTE: This repo pins ray==2.5.0 (requirements.txt). Ray 2.5.0 is not compatible with
    # pydantic v2 (FastAPI>=0.100 pulls pydantic v2), and /trace triggers Ray init.
    # Keep FastAPI on a pydantic v1-compatible version to avoid Ray dashboard/import crashes.
    pip install --no-cache-dir "pydantic<2" "fastapi==0.95.2" "uvicorn==0.22.0"

# Copy source
COPY . /app

# Build and install a native (arm64) gridsynth binary.
# The repo bundles an x86_64 Linux gridsynth which is not usable on arm64.
# We build the Haskell-based gridsynth via the `newsynth` package and place it where gsc_compiler expects.
RUN cabal update && \
    # Use a recent `newsynth` release compatible with the GHC/base version in this image.
    cabal install --installdir=/usr/local/bin --install-method=copy --overwrite-policy=always newsynth && \
    test -x /usr/local/bin/gridsynth && \
    cp -f /usr/local/bin/gridsynth /app/src/compiler/gridsynth && \
    chmod +x /app/src/compiler/gridsynth

EXPOSE 8000

# Start API server
CMD ["python", "-m", "uvicorn", "api_server:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]


