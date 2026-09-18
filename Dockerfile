FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN python -m pip install \
    --no-cache-dir \
    -r requirements.txt

COPY app ./app
COPY data ./data
COPY alembic.ini .
COPY alembic ./alembic

EXPOSE 8000

CMD ["python", "-m", "app.start"]
