from __future__ import annotations

import io
import os
import time
import wave
import re
import asyncio
import multiprocessing
import numpy as np
import onnxruntime as ort
from concurrent.futures import ProcessPoolExecutor
from fastapi import FastAPI, Request
from fastapi.responses import Response
from kokoro_onnx import Kokoro
from tts_normalizer import normalize_tts_text


# ====================== CONFIG ======================
MODEL_PATH = os.getenv("KOKORO_ONNX_MODEL", "/app/kokoro-martin.onnx")
VOICES_PATH = "/app/voices-martin.npz"
DEFAULT_VOICE = os.getenv("KOKORO_ONNX_VOICE", "martin")
DEFAULT_LANG = os.getenv("KOKORO_ONNX_LANG", "de")
DEFAULT_SPEED = float(os.getenv("KOKORO_ONNX_SPEED", "1.125"))
SAMPLE_RATE = 24000

# Pause aus Docker-Compose laden (Standard: 0.25 Sekunden)
PAUSE_DURATION = float(os.getenv("KOKORO_PAUSE_DURATION", "0.25"))
WORKERS = max(1, int(os.getenv("KOKORO_WORKERS", os.getenv("KOKORO_MAX_WORKERS", "1"))))
WARMUP_TEXT = os.getenv("KOKORO_WARMUP_TEXT", "Hallo.")
ORT_INTRA_OP_THREADS = max(1, int(os.getenv("KOKORO_ONNX_INTRA_OP_THREADS", os.getenv("KOKORO_ONNX_THREADS", "2"))))
ORT_INTER_OP_THREADS = max(1, int(os.getenv("KOKORO_ONNX_INTER_OP_THREADS", "1")))
ORT_EXECUTION_MODE = os.getenv("KOKORO_ONNX_EXECUTION_MODE", "sequential").lower()
ORT_GRAPH_OPT = os.getenv("KOKORO_ONNX_GRAPH_OPT", "all").lower()
ORT_ALLOW_SPINNING = os.getenv("KOKORO_ONNX_ALLOW_SPINNING", "0")

# ONNX / CPU Optimierung
os.environ.setdefault("OMP_NUM_THREADS", os.getenv("KOKORO_ONNX_THREADS", "1"))
os.environ.setdefault("OPENBLAS_NUM_THREADS", os.getenv("KOKORO_ONNX_THREADS", "1"))
os.environ.setdefault("MKL_NUM_THREADS", os.getenv("KOKORO_ONNX_THREADS", "1"))
os.environ.setdefault("NUMEXPR_NUM_THREADS", os.getenv("KOKORO_ONNX_THREADS", "1"))
os.environ.setdefault("ONNXRUNTIME_EXECUTION_MODE", "PARALLEL")


app = FastAPI()
kokoro: Kokoro | None = None
process_pool: ProcessPoolExecutor | None = None
worker_tts: Kokoro | None = None


# ==================== HELPER FUNKTIONEN ====================


def make_session_options() -> ort.SessionOptions:
    options = ort.SessionOptions()
    options.intra_op_num_threads = ORT_INTRA_OP_THREADS
    options.inter_op_num_threads = ORT_INTER_OP_THREADS

    if ORT_EXECUTION_MODE == "parallel":
        options.execution_mode = ort.ExecutionMode.ORT_PARALLEL
    else:
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

    graph_levels = {
        "disable": ort.GraphOptimizationLevel.ORT_DISABLE_ALL,
        "basic": ort.GraphOptimizationLevel.ORT_ENABLE_BASIC,
        "extended": ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED,
        "all": ort.GraphOptimizationLevel.ORT_ENABLE_ALL,
    }
    options.graph_optimization_level = graph_levels.get(ORT_GRAPH_OPT, ort.GraphOptimizationLevel.ORT_ENABLE_ALL)
    options.add_session_config_entry("session.intra_op.allow_spinning", ORT_ALLOW_SPINNING)
    options.add_session_config_entry("session.inter_op.allow_spinning", ORT_ALLOW_SPINNING)
    return options


def create_tts() -> Kokoro:
    session = ort.InferenceSession(
        MODEL_PATH,
        sess_options=make_session_options(),
        providers=["CPUExecutionProvider"],
    )
    return Kokoro.from_session(session, VOICES_PATH)


def wav_bytes(samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    samples = np.asarray(samples, dtype=np.float32)
    samples = np.clip(samples, -1.0, 1.0)
    pcm = (samples * 32767.0).astype(np.int16)
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())
    return output.getvalue()


def warm_tts(tts: Kokoro, label: str) -> None:
    if not WARMUP_TEXT:
        return

    warmup_started = time.perf_counter()
    try:
        tts.create(
            text=WARMUP_TEXT,
            voice=DEFAULT_VOICE,
            speed=1.0,
            lang=DEFAULT_LANG,
        )
        print(f"{label} warmed in {time.perf_counter() - warmup_started:.3f}s", flush=True)
    except Exception as err:
        print(f"{label} warm-up failed: {err!r}", flush=True)


def get_tts() -> Kokoro:
    global kokoro
    if kokoro is None:
        started = time.perf_counter()
        print(
            "Loading Kokoro ONNX model: "
            f"intra={ORT_INTRA_OP_THREADS}, inter={ORT_INTER_OP_THREADS}, "
            f"spinning={ORT_ALLOW_SPINNING}...",
            flush=True,
        )
        kokoro = create_tts()
        warm_tts(kokoro, "Kokoro ONNX")
        print(
            f"Kokoro ONNX ready in {time.perf_counter() - started:.3f}s, voices={kokoro.get_voices()}",
            flush=True,
        )
    return kokoro


def init_process_worker() -> None:
    global worker_tts
    os.environ["OMP_NUM_THREADS"] = str(ORT_INTRA_OP_THREADS)
    os.environ["OPENBLAS_NUM_THREADS"] = str(ORT_INTRA_OP_THREADS)
    os.environ["MKL_NUM_THREADS"] = str(ORT_INTRA_OP_THREADS)
    os.environ["NUMEXPR_NUM_THREADS"] = str(ORT_INTRA_OP_THREADS)

    started = time.perf_counter()
    worker_tts = create_tts()
    warm_tts(worker_tts, f"Kokoro ONNX process {os.getpid()}")
    print(
        f"Kokoro ONNX process {os.getpid()} ready in {time.perf_counter() - started:.3f}s",
        flush=True,
    )


def process_worker_ping(_index: int) -> int:
    if worker_tts is None:
        raise RuntimeError("Kokoro worker was not initialized")
    return os.getpid()


def get_process_pool() -> ProcessPoolExecutor:
    global process_pool
    if process_pool is None:
        print(
            "Loading Kokoro ONNX process pool: "
            f"workers={WORKERS}, intra={ORT_INTRA_OP_THREADS}, inter={ORT_INTER_OP_THREADS}, "
            f"spinning={ORT_ALLOW_SPINNING}...",
            flush=True,
        )
        process_pool = ProcessPoolExecutor(
            max_workers=WORKERS,
            initializer=init_process_worker,
            mp_context=multiprocessing.get_context("fork"),
        )
        print("Kokoro ONNX process pool created; workers start on first request.", flush=True)
    return process_pool


def split_into_sentences(text: str):
    """Trennt den Text an echten Satzgrenzen (.  !  ?  Zeilenumbruch)."""
    # Mehrfache Leerzeilen normalisieren
    text = re.sub(r"\n\s*\n", "\n\n", text)

    # Splitte nur an echten Satzenden: . ! ? gefolgt von Leerzeichen + Nicht-Leerzeichen.
    # Doppelpunkt und " werden bewusst NICHT als Trenner verwendet.
    sentences = re.split(r"(?<=[.!?])\s+(?=\S)", text)

    # Zeilenumbrüche innerhalb der Segmente weiter aufteilen
    result = []
    for segment in sentences:
        for line in segment.split("\n"):
            line = line.strip()
            if line and len(line) > 1:
                result.append(line)

    return result


def process_sentence(item):
    """Wird im ThreadPool ausgeführt."""
    idx, sentence, voice, speed, lang = item
    tts_instance = worker_tts if worker_tts is not None else get_tts()

    # 1. Zeilenumbrüche entfernen, da diese intern bei kokoro-onnx
    #    zu "input=2" führen, wenn der Satz damit endet.
    sentence = sentence.replace("\n", " ").strip()

    # 2. Problematische typografische Sonderzeichen entschärfen.
    safe_sentence = re.sub(r'[«‹–""]', ",", sentence).strip()

    if not safe_sentence:
        return idx, None, None, "Satz leer oder nur Sonderzeichen"

    try:
        samples, sr = tts_instance.create(
            text=safe_sentence,
            voice=voice,
            speed=speed,
            lang=lang,
        )
        return idx, samples, sr, None

    except ValueError as e:
        err_str = str(e)
        if "number of lines in input and output must be equal" in err_str:
            # ROBUSTER FALLBACK: Wenn espeak abstürzt (z. B. bei unbekannten
            # Abkürzungen), entfernen wir exotische Zeichen, behalten aber
            # normale Satzzeichen für eine natürliche Aussprache.
            very_safe = re.sub(r"[^\w\säöüßÄÖÜ.,:;!?\"'\-]", " ", safe_sentence).strip()
            if very_safe:
                try:
                    samples, sr = tts_instance.create(
                        text=very_safe,
                        voice=voice,
                        speed=speed,
                        lang=lang,
                    )
                    return idx, samples, sr, None
                except Exception as e2:
                    return idx, None, None, f"Fallback fehlgeschlagen: {e2}"
        return idx, None, None, f"Fehler für Satz '{sentence}': {err_str}"

    except Exception as e:
        return idx, None, None, f"Fehler für Satz '{sentence}': {e}"


# ==================== API ENDPUNKTE ====================


@app.get("/v1/audio/voices")
async def list_voices():
    return {"voices": [DEFAULT_VOICE]}


async def warm_process_pool_background() -> None:
    if WORKERS <= 1:
        return

    try:
        await asyncio.sleep(0.1)
        pool = get_process_pool()
        loop = asyncio.get_running_loop()
        warm_sentence = WARMUP_TEXT or "Hallo."
        warm_tasks = [(-1, warm_sentence, DEFAULT_VOICE, 1.0, DEFAULT_LANG)] * WORKERS
        await asyncio.gather(*(loop.run_in_executor(pool, process_sentence, task) for task in warm_tasks))
        print("Kokoro ONNX process pool warmed in background.", flush=True)
    except Exception as err:
        print(f"Kokoro ONNX background warm-up failed: {err!r}", flush=True)


@app.on_event("startup")
async def start_background_warmup() -> None:
    if WORKERS > 1:
        asyncio.create_task(warm_process_pool_background())


@app.post("/v1/audio/speech")
async def generate_speech(request: Request):
    data = await request.json()
    raw_text = str(data.get("input") or "")
    text = normalize_tts_text(raw_text)
    voice = str(data.get("voice") or DEFAULT_VOICE)
    speed = float(data.get("speed") or DEFAULT_SPEED)
    lang = str(data.get("lang") or data.get("language") or DEFAULT_LANG)
    req_pause_duration = float(data.get("pause_duration", PAUSE_DURATION))

    if voice != DEFAULT_VOICE:
        voice = DEFAULT_VOICE

    if text != raw_text:
        print(f"TTS normalisiert: {raw_text[:80]} -> {text[:80]}", flush=True)
    print(f"Generiere ONNX: {text[:40]}... [{voice}, pause={req_pause_duration}s]", flush=True)

    try:
        started = time.perf_counter()
        sentences = split_into_sentences(text)

        if not sentences:
            return Response(status_code=400, content="Kein verarbeitbarer Text gefunden.")

        results = [None] * len(sentences)
        tasks = [(i, s, voice, speed, lang) for i, s in enumerate(sentences)]

        if WORKERS > 1:
            pool = get_process_pool()
            loop = asyncio.get_running_loop()
            sentence_results = await asyncio.gather(
                *(loop.run_in_executor(pool, process_sentence, task) for task in tasks)
            )
        else:
            sentence_results = [process_sentence(task) for task in tasks]

        for idx, samples, sr, error in sentence_results:
            if idx >= 0:
                if error:
                    print(f"Fehler in Satz {idx + 1}: {error}", flush=True)
                else:
                    results[idx] = samples

        # === PAUSEN-LOGIK ===
        all_audio = []

        # BUGFIX: Fehlgeschlagene Sätze werden nicht mehr komplett gedroppt,
        # sondern durch eine kurze Stille ersetzt. So bleibt die zeitliche
        # Struktur erhalten und kein Text wird "zusammengezogen".
        valid_samples = []
        for s in results:
            if s is not None:
                valid_samples.append(s)
            else:
                valid_samples.append(
                    np.zeros(int(SAMPLE_RATE * req_pause_duration), dtype=np.float32)
                )

        num_sentences = len(valid_samples)

        for i, samples in enumerate(valid_samples):
            all_audio.append(samples)
            if req_pause_duration > 0:
                if i < num_sentences - 1:
                    # Pause zwischen den Sätzen
                    pause = np.zeros(int(SAMPLE_RATE * req_pause_duration), dtype=np.float32)
                    all_audio.append(pause)
                elif i == num_sentences - 1:
                    # Diese Pause hilft dem I2S-Puffer des Speakers (z. B. ESPHome)
                    # zu leeren und die Status-LED geht aus.
                    pause = np.zeros(int(SAMPLE_RATE * req_pause_duration), dtype=np.float32)
                    all_audio.append(pause)

        if not all_audio:
            raise ValueError("Ich hab alles gegeben, aber es konnte kein Audio generiert werden.")

        final_audio = np.concatenate(all_audio)

        elapsed = time.perf_counter() - started
        print(
            f"Kokoro ONNX fertig in {elapsed:.3f}s, samples={len(final_audio)}, Sätze={num_sentences}",
            flush=True,
        )

        return Response(content=wav_bytes(final_audio, SAMPLE_RATE), media_type="audio/wav")

    except Exception as err:
        print(f"Kokoro ONNX Fehler: {err!r}", flush=True)
        return Response(status_code=500, content=str(err))


print("Initialisiere Kokoro-ONNX-Service...", flush=True)
if WORKERS > 1:
    print(
        f"Kokoro ONNX process pool configured: workers={WORKERS}, "
        f"intra={ORT_INTRA_OP_THREADS}, inter={ORT_INTER_OP_THREADS}, spinning={ORT_ALLOW_SPINNING}",
        flush=True,
    )
else:
    get_tts()
