FROM  node:21-slim as base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable
WORKDIR /app
COPY package.json package.json

FROM base AS deps
RUN  pnpm install

FROM deps AS build-step
COPY . /app/
RUN pnpm run build
RUN ls -lah ./dist/

FROM base
COPY --from=deps /app/node_modules /app/node_modules
COPY --from=build-step /app/dist /app/dist
COPY --from=build-step /app/.output /app/.output

ENV PORTAL_BACKEND_INFRA="https://cloud.caps-platform.de"
EXPOSE 3000

CMD [ "pnpm", "start" ]



