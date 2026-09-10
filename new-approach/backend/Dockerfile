FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY pyproject.toml /app/
COPY app /app/app

RUN pip install --no-cache-dir -e .

EXPOSE 8000
