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

ENV PORT=8080
EXPOSE 8080

# Shell form so $PORT is expanded — hosts like Render assign their own port.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
