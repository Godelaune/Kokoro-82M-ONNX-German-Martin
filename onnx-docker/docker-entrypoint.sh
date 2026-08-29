#!/usr/bin/env sh
set -eu

repo_url="https://huggingface.co/Godelaune/Kokoro-82M-ONNX-German-Martin/resolve/main"
model_dir="${KOKORO_MODEL_DIR:-/app/models}"

mkdir -p "$model_dir"

download() {
  file="$1"
  path="$model_dir/$file"
  url="$repo_url/$file"

  if [ -f "$path" ]; then
    echo "$path already exists, skipping download"
    return
  fi

  echo "Downloading $file to $path"
  if command -v curl >/dev/null 2>&1; then
    curl -L --fail -o "$path" "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$path" "$url"
  else
    echo "Need curl or wget to download $file" >&2
    exit 1
  fi
}

download kokoro-martin.onnx
download voices-martin.npz

exec "$@"
