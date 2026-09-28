FROM node:22-bookworm-slim AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js postcss.config.js tailwind.config.js ./
COPY src ./src
COPY public ./public
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY backend ./backend
COPY --from=frontend /app/dist ./dist
ENV PYTHONUNBUFFERED=1
EXPOSE 10000
CMD ["sh", "-c", "python backend/server.py --host 0.0.0.0 --port ${PORT:-10000}"]
