FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app/src/main
ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "main:app", "--app-dir", "/app/src/main", "--host", "0.0.0.0", "--port", "8080"]
