#!/usr/bin/env sh
set -eu

repo_url="https://huggingface.co/Godelaune/Kokoro-82M-ONNX-German-Martin/resolve/main"

download() {
  file="$1"
  url="$repo_url/$file"
  if [ -f "$file" ]; then
    echo "$file already exists, skipping"
    return
  fi

  echo "Downloading $file"
  if command -v curl >/dev/null 2>&1; then
    curl -L --fail -o "$file" "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$file" "$url"
  else
    echo "Need curl or wget to download $file" >&2
    exit 1
  fi
}

download kokoro-martin.onnx
download voices-martin.npz
