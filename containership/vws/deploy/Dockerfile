# syntax=docker/dockerfile:1
# HERMIT virtual WebSocket gateway — Node profile (decision D-001).
# STATUS: AUTHORED, NOT BUILT. No Docker daemon was available in the authoring environment, so this
# file has never produced an image. Treat it as a reviewed starting point (series I046: BLOCKED).
#
# Pin the base image by digest before any real deployment:
#   docker buildx imagetools inspect node:22-bookworm-slim   ->   FROM node:22-bookworm-slim@sha256:<digest>
FROM node:22-bookworm-slim AS runtime

# The DF node containers need: Python 3.10+, a C11 toolchain + make + OpenSSL headers (Small/Medium/Large),
# and Java for column-verified compiles on Xtra_Large. Omit this layer for a terminal-only deployment.
ARG WITH_FABRIC=1
RUN if [ "$WITH_FABRIC" = "1" ]; then \
      apt-get update && apt-get install -y --no-install-recommends python3 gcc make libc6-dev libssl-dev openssl default-jre-headless \
      && rm -rf /var/lib/apt/lists/*; \
    fi

ENV NODE_ENV=production
WORKDIR /app
# No `npm install`: the gateway, worker and web client have ZERO third-party runtime dependencies.
# Electron/electron-builder are desktop-only devDependencies and are deliberately not installed here.
COPY --chown=node:node package.json LICENSE ./
COPY --chown=node:node protocol ./protocol
COPY --chown=node:node gateway ./gateway
COPY --chown=node:node worker ./worker
COPY --chown=node:node client ./client
COPY --chown=node:node web ./web
COPY --chown=node:node src/main/spiral ./src/main/spiral
COPY --chown=node:node src/renderer ./src/renderer

# DF containers are operator-supplied (they are not part of this repository). Mount or COPY them to /df
# and BUILD them at image build time so runtime sessions never need the build capability:
#   COPY --chown=node:node df/ /df/     &&   RUN cd /df/DF_Fabric && ./BUILD
ENV DF_ROOT=/df

USER node
EXPOSE 10000
# Exec form: node is PID 1 and receives SIGTERM directly (no shell in between to swallow it).
ENTRYPOINT ["node", "gateway/server.js"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:'+(process.env.PORT||10000)+'/health').then(r=>process.exit(r.status===200?0:1)).catch(()=>process.exit(1))"]
