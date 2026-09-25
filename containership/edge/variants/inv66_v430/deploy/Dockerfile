# Reproducible, non-root runtime image for INV-66 4.3.0 (MC-028 / MC-061).
# Base pinned by digest; rebuild via CI only.  Replace the digest when the base is patched (MC-062 SLA).
FROM python:3.11-slim@sha256:REPLACE_WITH_APPROVED_BASE_DIGEST AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /opt/inv66
COPY constraints.txt pyproject.toml ./
COPY inv66_enterprise_wasm_control_plane ./inv66_enterprise_wasm_control_plane
COPY LICENSE NOTICE THIRD-PARTY-NOTICES.md ./
RUN pip install -c constraints.txt . \
 && useradd --system --uid 10066 --home /var/lib/inv66 inv66 \
 && mkdir -p /var/lib/inv66/store && chown -R inv66 /var/lib/inv66
USER 10066
VOLUME ["/var/lib/inv66/store"]
EXPOSE 8466
HEALTHCHECK --interval=10s --timeout=2s CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8466/healthz',timeout=2).status==200 else 1)"
ENTRYPOINT ["inv66", "serve", "--store", "/var/lib/inv66/store"]
