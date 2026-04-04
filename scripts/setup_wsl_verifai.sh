#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$HOME/verifai_project}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[1/6] Updating apt packages"
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip build-essential git ffmpeg libgl1 libglib2.0-0

echo "[2/6] Creating project virtual environment"
cd "$PROJECT_ROOT"
$PYTHON_BIN -m venv .venv-wsl
source .venv-wsl/bin/activate

echo "[3/6] Upgrading pip tooling"
python -m pip install --upgrade pip setuptools wheel

echo "[4/6] Installing TensorFlow with CUDA support for WSL2"
python -m pip install "tensorflow[and-cuda]"

echo "[5/6] Installing project dependencies"
python -m pip install django scikit-learn opencv-python-headless numpy

echo "[6/6] Verifying TensorFlow GPU visibility"
python - <<'PY'
import tensorflow as tf
print("TensorFlow version:", tf.__version__)
print("Visible GPUs:", tf.config.list_physical_devices("GPU"))
PY

echo
echo "WSL environment ready."
echo "Activate it later with:"
echo "  source $PROJECT_ROOT/.venv-wsl/bin/activate"
