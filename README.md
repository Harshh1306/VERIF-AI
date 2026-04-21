# VerifAI Django Web App

This project includes a local Django interface for the deepfake detection system.

## Features

- Login and signup with Django authentication
- Image deepfake detection using `models/verifai_model_final.h5`
- Video deepfake detection using frame extraction and K-Means keyframe voting
- Saved detection history per user
- Django admin support

## Run locally

```powershell
venv\Scripts\python.exe manage.py migrate
venv\Scripts\python.exe manage.py createsuperuser
venv\Scripts\python.exe manage.py runserver
```

Then open `http://127.0.0.1:8000/`

## Retrain the image model

The upgraded trainer uses `TensorFlow + EfficientNetV2B0`, validation-calibrated thresholds, and metadata consumed by the Django app.

```powershell
venv\Scripts\python.exe train_model_final.py
```

Optional smoke run:

```powershell
venv\Scripts\python.exe train_model_final.py --sample-limit 2048 --train-head-epochs 1 --train-full-epochs 1
```

Outputs:

- `models/verifai_model_final.h5`
- `models/verifai_model_meta.json`
- `models/verifai_training_report.txt`

## GPU note

The project is on TensorFlow for training and inference. TensorFlow GPU support may still be limited in this native Windows environment.

## Google Colab option

If you want GPU training without local CUDA setup, use:

- `colab_train_verifai.ipynb`
- `COLAB_TRAINING.md`

This is the easiest path to retrain the upgraded model on a cloud GPU and bring the new `.h5` file back into the Django app.
