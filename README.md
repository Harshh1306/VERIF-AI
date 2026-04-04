# VerifAI Django Web App

This project now includes a deployable Django interface for the existing deepfake detection model.

## Features

- Login and signup with Django authentication
- Image deepfake detection using `models/verifai_model_final.h5`
- Video deepfake detection using frame extraction and K-Means keyframe voting
- Saved detection history per user
- Django admin support
- Production-ready Render deployment files

## Run locally

```powershell
venv\Scripts\python.exe manage.py migrate
venv\Scripts\python.exe manage.py createsuperuser
venv\Scripts\python.exe manage.py runserver
```

Then open `http://127.0.0.1:8000/`

## Deploy on Render

This project is prepared for deployment on Render with:

- `gunicorn`
- `whitenoise`
- `PostgreSQL`
- environment-based Django settings
- `render.yaml`

Files added for deployment:

- `requirements.txt`
- `build.sh`
- `render.yaml`
- `.env.example`

Basic deployment flow:

1. Push the repo to GitHub
2. Create a new Render Blueprint or Web Service from the repo
3. Render will create the web app and PostgreSQL database from `render.yaml`
4. After first deploy, create an admin user:

```powershell
python manage.py createsuperuser
```

Important note:

Uploaded media files are currently stored on the app filesystem. On platforms like Render, that storage is not ideal for long-term public production use. For a truly durable public app, the next step would be moving uploads to Cloudinary, S3, or another object storage service.

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

The project is back on TensorFlow for training and inference. TensorFlow GPU support may still be limited in this native Windows environment.

## Google Colab option

If you want GPU training without local CUDA setup, use:

- `colab_train_verifai.ipynb`
- `COLAB_TRAINING.md`

This is the easiest path to retrain the upgraded model on a cloud GPU and bring the new `.h5` file back into the Django app.
