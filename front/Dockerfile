FROM docker.io/oven/bun:1-alpine

WORKDIR /app

COPY package.json bun.lock bunfig.toml tsconfig.json ./
RUN bun install --frozen-lockfile --production

COPY src ./src

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000

EXPOSE 3000

CMD ["bun", "src/index.ts"]
