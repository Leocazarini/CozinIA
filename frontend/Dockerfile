FROM node:22-alpine

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
