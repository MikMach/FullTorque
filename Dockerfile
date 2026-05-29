FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Comando por omissão (o compose pode substituí-lo).
CMD ["gunicorn", "fulltorque.wsgi", "--bind", "0.0.0.0:8000", "--workers", "3"]
