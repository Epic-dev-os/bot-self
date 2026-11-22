#!/usr/bin/env bash
set -euo pipefail

if [ -z "${HOST_TOKEN:-}" ]; then
  echo "[FATAL] HOST_TOKEN is missing. Add it in Railway -> Variables."
  exit 1
fi

if [ -z "${DATA_DIR:-}" ]; then
  echo "[WARN] DATA_DIR is not set. Accounts will be lost on every redeploy."
fi

export PYTHONUNBUFFERED=1
export HOST_TOKEN
export OWNER_ID="${OWNER_ID:-}"
export HOST_PREFIX="${HOST_PREFIX:-.}"
export DATA_DIR="${DATA_DIR:-./data}"

mkdir -p "$DATA_DIR"

exec python main.py
