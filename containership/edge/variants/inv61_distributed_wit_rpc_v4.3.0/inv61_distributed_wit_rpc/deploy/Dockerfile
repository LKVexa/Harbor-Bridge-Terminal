# Reproducible container: pinned base digest must be filled by the release steward (W-011).
FROM python:3.12-slim AS run
RUN useradd --system --uid 10061 inv61 && mkdir -p /var/lib/inv61 && chown inv61 /var/lib/inv61
COPY dist/ /dist/
RUN cd /dist && sha256sum -c SHA256SUMS --ignore-missing \
 && pip install --no-index --no-deps /dist/*.whl && rm -rf /dist
USER inv61
EXPOSE 7461
ENTRYPOINT ["inv61-node"]
