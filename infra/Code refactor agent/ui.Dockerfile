FROM node:20-alpine

WORKDIR /app

RUN corepack enable

COPY ["apps/Code refactor agent/refactor-agent-ui/package.json", "./package.json"]
COPY ["apps/Code refactor agent/refactor-agent-ui/pnpm-lock.yaml", "./pnpm-lock.yaml"]
RUN pnpm install --frozen-lockfile

COPY ["apps/Code refactor agent/refactor-agent-ui/", "./"]

EXPOSE 3001

CMD ["pnpm", "exec", "next", "dev", "--hostname", "0.0.0.0", "--port", "3001"]
