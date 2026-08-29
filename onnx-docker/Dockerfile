FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget curl espeak-ng libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    numpy \
    kokoro-onnx==0.5.0

COPY german_text_rules.py /app/german_text_rules.py
COPY onnx-docker/main.py /app/main.py
COPY onnx-docker/tts_normalizer.py /app/tts_normalizer.py
COPY onnx-docker/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8881

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8881", "--loop", "uvloop", "--http", "httptools"]
