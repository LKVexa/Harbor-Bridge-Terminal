# INV-07 controller image.  Deterministic build rules:
#  * base image MUST be pinned by digest -- the build fails until PIN is replaced (waiver W-005);
#  * no pip dependencies at runtime (stdlib only); git from the distro, version checked at start;
#  * non-root UID, read-only root filesystem expected (state on a volume).
ARG BASE=python:3.12-slim@sha256:PIN_REQUIRED
FROM ${BASE}
RUN test "${BASE#*@sha256:}" != "PIN_REQUIRED" || (echo "pin the base image digest (W-005)" && exit 1)
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/inv07
COPY inv07_gitops_transition_layer/ /opt/inv07/inv07_gitops_transition_layer/
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SOURCE_DATE_EPOCH=1790000000
USER 65532:65532
ENTRYPOINT ["python", "-B", "-m", "inv07_gitops_transition_layer.components.cli"]
CMD ["status", "/etc/inv07/config.json", "--base-dir", "/var/lib/inv07"]
