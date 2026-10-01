FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

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
