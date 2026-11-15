# Build from the repository root:  docker build -f frontend/Dockerfile .   (or `docker compose up --build`)
# The interface in the browser (Next.js server). Requests to /api and /health are forwarded to the backend;
# that address is fixed when the image is built (SHADOW_API_URL), because Next.js writes the rule into the build.

FROM node:22-slim AS builder
WORKDIR /app/frontend
# the desktop app (Electron) is not part of this image
ENV ELECTRON_SKIP_BINARY_DOWNLOAD=1 NEXT_TELEMETRY_DISABLED=1
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG SHADOW_API_URL=http://backend:8000
ENV SHADOW_API_URL=$SHADOW_API_URL
# after the build: drop the dev dependencies, the build cache and the compiler binary for another libc
RUN npm run build && npm prune --omit=dev && rm -rf .next-dev/cache node_modules/@next/swc-linux-*-musl


FROM node:22-slim
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
WORKDIR /app/frontend
COPY --from=builder --chown=node:node /app/frontend/ ./
ARG SHADOW_API_URL=http://backend:8000
ENV SHADOW_API_URL=$SHADOW_API_URL

USER node
EXPOSE 3000
HEALTHCHECK --interval=5s --timeout=3s --start-period=20s --retries=10 \
    CMD node -e "fetch('http://127.0.0.1:3000/login').then(r => process.exit(r.ok ? 0 : 1), () => process.exit(1))"
CMD ["node_modules/.bin/next", "start", "-p", "3000", "-H", "0.0.0.0"]
