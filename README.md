# Kokoro ONNX German Martin

Docker and Home Assistant Assist setup for the German Kokoro voice **Martin**, using the ONNX export published on Hugging Face:

[huggingFresse/Kokoro-82M-ONNX-German-Martin](https://huggingface.co/huggingFresse/Kokoro-82M-ONNX-German-Martin)

This GitHub repository contains the service code, German text normalization rules, Docker setup and Wyoming bridge overlay. The large model files and audio samples stay on Hugging Face, which is the better home for model artifacts.

## What Is Included

- `onnx-docker/`: a FastAPI service exposing an OpenAI-compatible `/v1/audio/speech` endpoint for Kokoro ONNX.
- `wyoming_openai_german_separator/`: a Docker overlay for `wyoming_openai` that protects German dotted abbreviations during streaming sentence segmentation.
- `german_text_rules.py`: the shared German abbreviation, unit and sentence-boundary rule file used by both services.
- `docker-compose.yml`: a two-container Home Assistant Assist setup for Kokoro ONNX plus Wyoming.
- `scripts/download-model-files.sh`: downloads `kokoro-martin.onnx` and `voices-martin.npz` from Hugging Face.

## Relationship To Upstream Projects

This is not a fork of `semidark/kikiri-tts` or `hexgrad/kokoro`. It is a deployment and normalization repository built around the German Martin ONNX export.

Related projects:

- German Martin voice: [kikiri-tts/kikiri-german-martin](https://huggingface.co/kikiri-tts/kikiri-german-martin)
- Kokoro architecture: [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) and [hexgrad/kokoro](https://github.com/hexgrad/kokoro)
- ONNX runtime package used by the service: [thewh1teagle/kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx)
- Kikiri TTS tooling: [semidark/kikiri-tts](https://github.com/semidark/kikiri-tts)
- Wyoming OpenAI bridge base image: [roryeckel/wyoming_openai](https://github.com/roryeckel/wyoming_openai)

## Quick Start

Clone this repository:

```bash
git clone https://github.com/Godelaune/Kokoro-82M-ONNX-German-Martin.git
cd Kokoro-82M-ONNX-German-Martin
```

Download the model artifacts from Hugging Face:

```bash
sh scripts/download-model-files.sh
```

Start the ONNX TTS service and Wyoming bridge:

```bash
docker compose up -d --build
```

Check the TTS service:

```bash
curl http://localhost:8881/v1/audio/voices
```

For Home Assistant, add the Wyoming integration and point it to the Docker host:

```text
Host: <your-docker-host>
Port: 10203
```

## German Text Normalization

The service normalizes common German forms before synthesis, including:

- decimal numbers with units, for example `2,5 kWh`
- singular/plural unit forms, for example `1 kWh` vs. `2 kWh`
- dotted units and abbreviations such as `Min.`, `Stck.`, `ltr.`, `zzgl.` and `ggf.`
- Euro amounts such as `42,80 EUR`
- ordinal/cardinal contexts such as dates, quarters, tracks and numbered labels

The same `german_text_rules.py` file is mounted into both containers, so the FastAPI service and Wyoming bridge use the same abbreviation and sentence-boundary rules.

## Process-Isolated Parallel Workers

Version 1.2 replaces thread-shared Kokoro synthesis with process-isolated workers. Each worker owns its own Kokoro/ONNX session, which avoids sharing Kokoro, espeak and tokenizer state across threads while still allowing parallel sentence synthesis.

The included compose file uses this Intel NUC-oriented profile:

```text
KOKORO_WORKERS=2
KOKORO_ONNX_INTRA_OP_THREADS=2
KOKORO_ONNX_INTER_OP_THREADS=1
KOKORO_ONNX_ALLOW_SPINNING=0
OMP_NUM_THREADS=2
OPENBLAS_NUM_THREADS=2
MKL_NUM_THREADS=2
NUMEXPR_NUM_THREADS=2
```

For very small systems, set `KOKORO_WORKERS=1`. For larger CPUs, benchmark higher worker and thread counts carefully; each worker also uses ONNX Runtime threads.

## Audio Sample

The main v1.1/v1.2 German normalization sample is hosted on Hugging Face:

[martin-onnx-beispiel-v1.1.mp3](https://huggingface.co/huggingFresse/Kokoro-82M-ONNX-German-Martin/resolve/main/martin-onnx-beispiel-v1.1.mp3)

Spoken text:

> Zum 14.05.2026 um 18:20 Uhr ist das Abendessen geplant. Für den Auflauf brauchen wir 1,5 kg Kartoffeln, 500 g Quark, 2 Eier, 1 ltr. Milch und ggf. 3 cm mehr Backpapier. Prof. Klein sagt: "Bitte stelle die Form auf die 2. Schiene, backe alles für 45 Min. und lass es danach 1 Min. oder auch 2 Min. ruhen." Die Kosten liegen bei ca. 12,80 EUR zzgl. Pfand.

## Changelog

### v1.2 (May 2026)

- Replaced thread-based parallel sentence synthesis with process-isolated Kokoro workers.
- Avoids sharing Kokoro, espeak and tokenizer state across worker threads, addressing possible word-order corruption under parallel synthesis.
- Added ONNX Runtime session tuning via `KOKORO_ONNX_INTRA_OP_THREADS`, `KOKORO_ONNX_INTER_OP_THREADS`, `KOKORO_ONNX_EXECUTION_MODE`, `KOKORO_ONNX_GRAPH_OPT` and `KOKORO_ONNX_ALLOW_SPINNING`.
- Added background warm-up for process workers.
- Added `KOKORO_WORKERS` as the public knob for parallel synthesis workers.

### v1.1 (May 2026)

- Added German text normalization before synthesis.
- Added decimal units, singular/plural unit handling, Euro amount handling and improved abbreviation support.
- Added better ordinal/cardinal handling in contexts such as dates, quarters, tracks, chapters and numbered labels.
- Fixed sentence pauses around common German abbreviations and dotted unit abbreviations.

### v1.0

- Initial ONNX conversion and Docker/FastAPI service setup.

## License And Credits

The model is published under Apache 2.0 on Hugging Face. Please credit the original model authors and upstream projects when using this setup:

- [kikiri-tts/kikiri-german-martin](https://huggingface.co/kikiri-tts/kikiri-german-martin)
- [dida-80b/kokoro-german-hui-multispeaker-base](https://huggingface.co/dida-80b/kokoro-german-hui-multispeaker-base)
- [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)
- [huggingFresse/Kokoro-82M-ONNX-German-Martin](https://huggingface.co/huggingFresse/Kokoro-82M-ONNX-German-Martin)
