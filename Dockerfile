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

RUN groupadd --gid 10001 agentforge \
    && useradd --uid 10001 --gid 10001 \
       --home-dir /app --no-create-home agentforge \
    && mkdir -p /app/logs /app/chroma_db \
    && chown agentforge:agentforge /app/logs /app/chroma_db

USER agentforge

EXPOSE 8000

CMD ["python", "-m", "app.start"]
