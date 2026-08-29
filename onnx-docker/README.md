# Kokoro ONNX FastAPI service

This folder contains the FastAPI wrapper for the German Martin ONNX model.

The service exposes an OpenAI-compatible `/v1/audio/speech` endpoint and applies
the v1.1 German text normalization before synthesis. The shared
`german_text_rules.py` file from the repository root is copied into the image
at build time, so the TTS service and Wyoming bridge use the same abbreviation
and sentence-boundary rules.

On startup, the container downloads `kokoro-martin.onnx` and `voices-martin.npz`
from Hugging Face into `KOKORO_MODEL_DIR` (default `/app/models`) if they are
not already present there, so mount a persistent volume at that path to avoid
re-downloading on every restart.
