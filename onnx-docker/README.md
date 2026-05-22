# Kokoro ONNX FastAPI service

This folder contains the FastAPI wrapper for the German Martin ONNX model.

The service exposes an OpenAI-compatible `/v1/audio/speech` endpoint and applies
the v1.1 German text normalization before synthesis. The shared
`german_text_rules.py` file is mounted from the repository root so the TTS
service and Wyoming bridge use the same abbreviation and sentence-boundary
rules.
