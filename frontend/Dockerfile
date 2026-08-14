# Development: the Vite dev server, with hot-reload over the bind mounts
# declared in docker-compose.yml. Also the stage the frontend test suite runs
# in (see the tests-frontend service).
FROM node:22-alpine AS dev

WORKDIR /app

# curl: used by the Docker Compose healthcheck.
RUN apk add --no-cache curl

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# --host so the dev server is reachable from other containers/the host,
# not just loopback inside this container.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Production build. Separate stage from `dev` only so the toolchain and the
# node_modules stay out of the image that actually gets served.
FROM dev AS build

RUN npm run build

# What the phone talks to: the built app, plus the reverse proxy that puts the
# API on this same origin. One origin is what makes the app installable — a
# service worker needs a secure context, and an https page may not call a
# plain-http backend on another port.
#
# The only difference between this container on the LAN and on the VPS is the
# certificate it is given and the name it answers to, both passed in as
# environment variables.
FROM nginx:1.27-alpine AS web

RUN apk add --no-cache curl

COPY --from=build /app/dist /usr/share/nginx/html
# The nginx entrypoint runs envsubst over everything in this directory before
# starting, which is how WEB_SERVER_NAME and the certificate paths get in.
COPY nginx/cozinia.conf.template /etc/nginx/templates/default.conf.template
# Security headers live in a snippet the server config `include`s. Kept out of
# the templates dir on purpose: it has no variables to substitute, and it is
# not a standalone server block.
COPY nginx/security-headers.conf /etc/nginx/snippets/security-headers.conf

EXPOSE 80 443
