# Minimal non-root image (MC-028-T03). Base image digest must be pinned by the release pipeline;
# the tag below is a placeholder until a registry mirror is approved (waiver W-09).
FROM python:3.11-slim@sha256:PIN_ME_IN_RELEASE_PIPELINE
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SETUPTOOLS_USE_DISTUTILS=stdlib
RUN groupadd -r -g 10066 inv66 && useradd -r -u 10066 -g inv66 -d /nonexistent -s /usr/sbin/nologin inv66
COPY constraints.txt /tmp/constraints.txt
COPY dist/*.whl /tmp/
RUN pip install --no-cache-dir -c /tmp/constraints.txt /tmp/*.whl && rm -f /tmp/*.whl
USER 10066:10066
VOLUME ["/var/lib/inv66"]
EXPOSE 8443
HEALTHCHECK --interval=10s --timeout=2s CMD python -c "import urllib.request,ssl;urllib.request.urlopen('https://127.0.0.1:8443/healthz',context=ssl._create_unverified_context(),timeout=2)"
# run with: --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges
ENTRYPOINT ["inv66"]
