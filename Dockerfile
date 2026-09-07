# CyboPal ONE Hermes DevKit — live simulator (linux/arm64, DGX Spark / GB10).
# Weights are NOT baked in. Omni is `scripts/serve-vllm.sh` against a GB10 vLLM.
#
#   docker build -t ghcr.io/drowzeys/keys-cybopal-one-hermes-devkit:0.1.0 .
#   docker run --rm --network host IMAGE

FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.source="https://github.com/drowzeys/keys-CyboPal-ONE-Hermes-DevKit-LiveSimulator-Nemotron3Nano-Omni-for-DGX-Spark" \
      org.opencontainers.image.description="CyboPal ONE live 6-DOF simulator + Hermes DevKit for DGX Spark" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=5000

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
        libglib2.0-0 libgomp1 libgl1 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY mock_device.py agent_core.py AGENTS.md LICENSE /app/
COPY cybopal /app/cybopal
COPY static /app/static
COPY skills /app/skills
COPY scripts /app/scripts
COPY docs /app/docs
COPY docker/entrypoint.sh /usr/local/bin/cybopal-entrypoint
RUN chmod +x /usr/local/bin/cybopal-entrypoint /app/scripts/*.sh /app/scripts/*.py \
        /app/mock_device.py /app/agent_core.py

EXPOSE 5000
HEALTHCHECK --interval=15s --timeout=3s --retries=8 \
  CMD curl -fsS http://127.0.0.1:${PORT}/api/v1/health || exit 1

ENTRYPOINT ["/usr/local/bin/cybopal-entrypoint"]
CMD []
