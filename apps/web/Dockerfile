# =============================================================================
# eBook Studio AI web image (Next.js 15)
# Build context is the REPOSITORY ROOT because the app depends on the
# `packages/shared` workspace package:
#   docker build -f apps/web/Dockerfile .
# =============================================================================
FROM node:22-alpine AS runner

RUN corepack enable && apk add --no-cache libc6-compat curl

WORKDIR /app

# --- Workspace sources -----------------------------------------------------
COPY packages/shared ./packages/shared
COPY apps/web ./apps/web

WORKDIR /app/apps/web

# NEXT_PUBLIC_* values are inlined into the client bundle at build time.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

# Install (the `file:` dependency links ../../packages/shared) and build.
RUN pnpm install --no-frozen-lockfile
RUN pnpm build

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

EXPOSE 3000

HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=5 \
  CMD curl -fsS http://localhost:3000/ || exit 1

CMD ["pnpm", "start"]
