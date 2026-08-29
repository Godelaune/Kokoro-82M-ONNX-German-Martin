FROM ghcr.io/roryeckel/wyoming_openai:latest

COPY german_text_rules.py /tmp/german_text_rules.py
COPY wyoming_openai_german_separator/apply_german_separator_patch.py /tmp/apply_german_separator_patch.py
RUN python3 /tmp/apply_german_separator_patch.py \
    && rm /tmp/apply_german_separator_patch.py /tmp/german_text_rules.py
