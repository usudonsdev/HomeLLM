FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY segment.py /app/segment.py
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "/app/segment.py"]
