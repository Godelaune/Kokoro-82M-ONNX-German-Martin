from __future__ import annotations

from pathlib import Path
import site

HELPERS = '''

def _protect_german_separator_dots(text: str) -> str:
    """Hide dots in German abbreviations, dates and ordinals before pySBD segmentation."""
    protected = text
    for pattern in GERMAN_SEPARATOR_DOT_PATTERNS:
        protected = re.sub(
            pattern,
            lambda match: match.group(0).replace(".", GERMAN_SEPARATOR_DOT_PLACEHOLDER),
            protected,
            flags=re.IGNORECASE,
        )
    return protected


def _restore_german_separator_dots(text: str) -> str:
    """Restore dots hidden before sentence segmentation."""
    return text.replace(GERMAN_SEPARATOR_DOT_PLACEHOLDER, ".")
'''

SEGMENT_METHOD = '''

    def _segment_text(self, segmenter, text: str) -> list[str]:
        """Segment text while keeping common German abbreviations intact."""
        protected_text = _protect_german_separator_dots(text)
        return [_restore_german_separator_dots(sentence) for sentence in segmenter.segment(protected_text)]
'''


def find_handler() -> Path:
    candidates: list[Path] = []
    for package_dir in site.getsitepackages():
        candidates.append(Path(package_dir) / "wyoming_openai" / "handler.py")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    joined = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Could not find wyoming_openai/handler.py in: {joined}")


def replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(
            f"Patch anchor not found:\n--- LOOKING FOR ---\n{old[:120]}"
            f"\n--- IN SOURCE (first 3000 chars) ---\n{text[:3000]}"
        )
    return text.replace(old, new, 1)


handler_path = find_handler()
source = handler_path.read_text(encoding="utf-8")
print(f"handler.py found at: {handler_path}")
print(f"handler.py first 200 chars:\n{source[:200]}")

if "GERMAN_SEPARATOR_DOT_PLACEHOLDER" in source:
    print("Patch already applied, skipping.")
else:
    source = replace_once(source, "import logging\n", "import logging\nimport re\n")

    import_line = "from german_text_rules import GERMAN_SEPARATOR_DOT_PATTERNS, GERMAN_SEPARATOR_DOT_PLACEHOLDER\n"
    if "from . import __version__\n" in source:
        source = replace_once(source, "from . import __version__\n", "from . import __version__\n" + import_line)
    else:
        source = replace_once(
            source,
            "from .compatibility import CustomAsyncOpenAI, OpenAIBackend, TtsVoiceModel\n",
            "from .compatibility import CustomAsyncOpenAI, OpenAIBackend, TtsVoiceModel\n" + import_line,
        )

    source = replace_once(
        source,
        "\nclass OpenAIEventHandler",
        HELPERS + "\nclass OpenAIEventHandler",
    )

    if "\n    async def handle(" in source:
        source = replace_once(source, "\n    async def handle(", SEGMENT_METHOD + "\n    async def handle(")
    else:
        source = replace_once(source, "\n    async def handle_event(", SEGMENT_METHOD + "\n    async def handle_event(")

    patched = source.replace(
        "segmenter.segment(text)",
        "self._segment_text(segmenter, text)",
    ).replace(
        "segmenter.segment(self._text_accumulator)",
        "self._segment_text(segmenter, self._text_accumulator)",
    )

    if patched == source:
        print("WARNING: No segmenter.segment() calls found to patch - the bridge may not use pySBD.")
        print("Patch applied partially (helpers + imports only).")
    else:
        source = patched

    handler_path.write_text(source, encoding="utf-8")
    print(f"Applied German sentence separator patch to {handler_path}")

source = handler_path.read_text(encoding="utf-8")
if "WYOMING_TTS_CONCURRENT_REQUESTS" in source:
    print("German TTS concurrency patch already applied, skipping.")
else:
    if "import os\n" not in source:
        source = replace_once(source, "import logging\n", "import logging\nimport os\n")

    source = replace_once(
        source,
        "TTS_CONCURRENT_REQUESTS = 3  # Number of concurrent OpenAI TTS requests when streaming sentences\n",
        "TTS_CONCURRENT_REQUESTS = int(os.getenv(\"WYOMING_TTS_CONCURRENT_REQUESTS\", \"3\"))  # Number of concurrent OpenAI TTS requests when streaming sentences\n",
    )

    handler_path.write_text(source, encoding="utf-8")
    print(f"Applied German TTS concurrency patch to {handler_path}")
