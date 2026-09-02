FROM node:22-alpine@sha256:c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32 AS deps
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:22-alpine@sha256:c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32 AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web ./
RUN npm run build

FROM node:22-alpine@sha256:c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32 AS runner
WORKDIR /app
ENV NODE_ENV=production
# The runtime only needs the Node binary. Apply available Alpine security fixes
# and remove package-manager toolchains (and their transitive dependencies) so
# build-only npm/corepack/yarn vulnerabilities are not shipped to production.
RUN apk upgrade --no-cache \
    && rm -rf \
        /usr/local/lib/node_modules/npm \
        /usr/local/lib/node_modules/corepack \
        /opt/yarn-v1.22.22 \
        /usr/local/bin/npm \
        /usr/local/bin/npx \
        /usr/local/bin/corepack \
        /usr/local/bin/yarn \
        /usr/local/bin/yarnpkg
COPY --chown=node:node --from=builder /app/.next/standalone ./
COPY --chown=node:node --from=builder /app/.next/static ./.next/static
COPY --chown=node:node --from=builder /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
