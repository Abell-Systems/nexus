FROM node:20-slim AS frontend-src
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./

FROM frontend-src AS frontend
RUN npm run build

# Same sources without the matcher: the static staging bundle carries no matcher code and no /api client.
FROM frontend-src AS frontend-static
RUN VITE_STATIC_ONLY=1 npm run build

# Staging of the white-space page only (--target static): the built SPA behind an unprivileged nginx. No API, no corpus.
# nginx 1.30 is the stable branch still supported on 2026-10-23 (1.27 reached its end of life in June 2025). Exact version and digest on
# purpose: bump them deliberately, with the tests, not through a moving tag.
FROM nginxinc/nginx-unprivileged:1.30.6-alpine3.24@sha256:f5116ed4606f3eb015dd4a8e28cb9b351476dc0ad4bc6e9f93b19cec130cdf03 AS static
COPY deploy/nginx-static.conf /etc/nginx/nginx.conf
COPY --from=frontend-static /frontend/dist /usr/share/nginx/html

# Default target (the last stage): the MVP with its API and verified artifacts.
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/src/main ./src/main
COPY --from=frontend /frontend/dist ./static
WORKDIR /app/src/main
USER nobody
EXPOSE 8080
# Artifacts are verified before the server listens (~25 s), hence the long start period.
HEALTHCHECK --start-period=90s --interval=30s --timeout=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"
ENTRYPOINT ["python", "-m", "infrastructure.mvp_entrypoint"]
CMD ["--artifacts", "/srv/nexus/data", "--static", "/app/static", "--host", "0.0.0.0"]
