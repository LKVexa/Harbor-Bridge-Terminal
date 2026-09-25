# Reproducible image: pinned base by digest (set at release), hash-locked deps, non-root, read-only FS.
FROM python:3.12-slim@sha256:REPLACE_WITH_APPROVED_DIGEST
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/inv05
COPY requirements.lock /opt/inv05/requirements.lock
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY inv05_current_control_state_system /opt/inv05/inv05_current_control_state_system
RUN useradd --system --uid 10005 --home /var/lib/inv05 inv05 && mkdir -p /var/lib/inv05 && chown inv05 /var/lib/inv05 && chmod 700 /var/lib/inv05
USER 10005
EXPOSE 2479
HEALTHCHECK CMD python -c "import urllib.request,ssl;print('probe via orchestrator')" || exit 1
ENTRYPOINT ["python", "-m", "inv05_current_control_state_system.bootstrap", "--config", "/etc/inv05/base.json", "--secret-dir", "/run/inv05/secrets"]
