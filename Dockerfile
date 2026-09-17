FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "until alembic upgrade head; do echo 'waiting for db...'; sleep 2; done && uvicorn main:app --host 0.0.0.0 --port 8000"]
