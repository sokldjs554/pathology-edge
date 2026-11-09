FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 CC=gcc CXX=g++

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-dev g++ git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv && chown -R ubuntu:ubuntu /opt/venv
USER ubuntu
ENV PATH="/opt/venv/bin:$PATH"

COPY --chmod=0644 requirements-lock.txt /tmp/pathology-edge-requirements.txt
# The optional CA secret is only for local verification behind a managed proxy.
# Codespaces normally builds without it; TLS verification remains enabled.
RUN --mount=type=secret,id=build_ca,mode=0444 \
    if [ -f /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi; \
    python -m pip install --extra-index-url https://download.pytorch.org/whl/cpu \
      -r /tmp/pathology-edge-requirements.txt \
    && python -m pip check

# Install editable source after Codespaces mounts the user's checkout.
# No source copy, data download, training or server is baked into this image.
