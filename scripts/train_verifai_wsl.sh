#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$HOME/verifai_project}"
SAMPLE_LIMIT="${SAMPLE_LIMIT:-0}"

cd "$PROJECT_ROOT"
source .venv-wsl/bin/activate

python - <<'PY'
import tensorflow as tf
gpus = tf.config.list_physical_devices("GPU")
print("Visible GPUs:", gpus)
if not gpus:
    raise SystemExit("No GPU visible to TensorFlow inside WSL. Stop here and fix WSL/CUDA first.")
PY

if [ "$SAMPLE_LIMIT" -gt 0 ]; then
  python train_model_final.py --sample-limit "$SAMPLE_LIMIT"
else
  python train_model_final.py
fi
