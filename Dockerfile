FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=frontend-builder /app/frontend/dist ./static

ENV PYTHONPATH=/app/src/main
ENV PORT=8080
EXPOSE 8080

CMD uvicorn main:app --app-dir /app/src/main --host 0.0.0.0 --port ${PORT}
