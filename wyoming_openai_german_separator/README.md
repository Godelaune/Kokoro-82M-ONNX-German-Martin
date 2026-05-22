# wyoming_openai_german_separator

Lightweight Docker overlay for [`ghcr.io/roryeckel/wyoming_openai`](https://github.com/roryeckel/wyoming-openai).

This image keeps the upstream project intact and applies a small German sentence-boundary patch during the Docker build. It is meant for German Home Assistant Assist / Wyoming TTS pipelines where streaming sentence chunking should not split at common abbreviations, dates, or ordinal numbers.

The sentence-boundary rules live in `german_text_rules.py`. The same file can also be mounted into a TTS backend such as a Kokoro service so pronunciation expansion and separator protection share one source of truth.

## What It Changes

The upstream bridge uses `pySBD` to detect sentence boundaries for incremental TTS streaming. In German text, dots inside abbreviations or ordinal numbers can look like sentence endings, for example:

- `z.B.`
- `d.h.`
- `u.a.`
- `Dr.`
- `Prof.`
- `etc.`
- `13.05.`
- `50. Geburtstag`
- `1000. Version`

This overlay masks those dots before `pySBD` segmentation and restores them immediately afterwards. The TTS backend still receives the original text; only sentence splitting is affected.

The protected abbreviation patterns are derived from `ABBREVIATIONS` in `german_text_rules.py`, plus extra date and ordinal patterns.

## Build

```bash
docker build -t wyoming_openai_german_separator:latest .
```

## Compose Example

```yaml
services:
  wyoming_openai_onnx:
    build: ./wyoming_openai_german_separator
    image: wyoming_openai_german_separator:latest
    container_name: wyoming_openai_onnx
    restart: unless-stopped
    volumes:
      - ./german_text_rules.py:/usr/local/lib/python3.12/site-packages/wyoming_openai/german_text_rules.py:ro
```

Keep the normal `wyoming_openai` command and environment settings from upstream.

## Scope

This is intentionally small:

- no forked package publishing
- no vendored upstream source
- no TTS text normalization
- only German sentence-boundary protection for streaming chunking

TTS pronunciation changes such as expanding `Hbf` or `etc.` belong in the TTS backend itself, but they can import the same `german_text_rules.py` file.
