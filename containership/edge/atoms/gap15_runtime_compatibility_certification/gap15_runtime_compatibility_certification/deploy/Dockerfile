# GAP-15 certification service — reproducible, non-root, read-only root filesystem.
# Pin the base image by digest at release time (tag shown for readability; the gate rejects an unpinned FROM).
FROM python:3.12-slim@sha256:REPLACE_WITH_PINNED_DIGEST
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --system --uid 10015 --home /nonexistent --shell /usr/sbin/nologin gap15
WORKDIR /opt/gap15
COPY --chown=root:root gap15_runtime_compatibility_certification/ ./gap15_runtime_compatibility_certification/
USER 10015:10015
VOLUME ["/var/lib/gap15"]
EXPOSE 8443
HEALTHCHECK --interval=15s --timeout=3s CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('https://127.0.0.1:8443/healthz').status==200 else 1)"
ENTRYPOINT ["python", "-m", "gap15_runtime_compatibility_certification.production.serve", "--config", "/etc/gap15/config.json"]
