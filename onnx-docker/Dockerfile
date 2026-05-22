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

COPY kokoro-martin.onnx /app/kokoro-martin.onnx
COPY voices-martin.npz /app/voices-martin.npz
COPY onnx-docker/main.py /app/main.py
COPY onnx-docker/tts_normalizer.py /app/tts_normalizer.py

EXPOSE 8881

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8881", "--loop", "uvloop", "--http", "httptools"]
