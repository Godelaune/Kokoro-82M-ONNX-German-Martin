FROM ghcr.io/roryeckel/wyoming_openai:latest

COPY apply_german_separator_patch.py /tmp/apply_german_separator_patch.py
RUN python3 /tmp/apply_german_separator_patch.py \
    && rm /tmp/apply_german_separator_patch.py
