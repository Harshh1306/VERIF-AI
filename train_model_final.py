import argparse
import json
import math
import os
from pathlib import Path

import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_curve
from tensorflow import keras


BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset" / "image"
MODELS_DIR = BASE_DIR / "models"
MODEL_PATH = MODELS_DIR / "verifai_model_final.h5"
METADATA_PATH = MODELS_DIR / "verifai_model_meta.json"
REPORT_PATH = MODELS_DIR / "verifai_training_report.txt"
IMAGE_SIZE = (224, 224)
AUTOTUNE = tf.data.AUTOTUNE


def parse_args():
    parser = argparse.ArgumentParser(description="Train the VerifAI image deepfake detector.")
    parser.add_argument("--dataset", default=str(DATASET_DIR))
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--validation-split", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--fine-tune-learning-rate", type=float, default=5e-5)
    parser.add_argument("--fine-tune-at", type=int, default=40)
    parser.add_argument("--weights", default="imagenet", choices=["imagenet", "none"])
    parser.add_argument("--train-head-epochs", type=int, default=4)
    parser.add_argument("--train-full-epochs", type=int, default=8)
    parser.add_argument("--sample-limit", type=int, default=0)
    parser.add_argument("--steps-per-epoch", type=int, default=0)
    parser.add_argument("--validation-steps", type=int, default=0)
    return parser.parse_args()


def configure_runtime():
    tf.keras.utils.set_random_seed(42)
    tf.config.optimizer.set_jit(True)

    gpus = tf.config.list_physical_devices("GPU")
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)

    if gpus:
        keras.mixed_precision.set_global_policy("mixed_float16")
        print(f"Using GPU(s): {gpus}")
    else:
        print(
            "No TensorFlow GPU detected. On native Windows, modern TensorFlow often falls back to CPU. "
            "Use WSL2 with CUDA-enabled TensorFlow if you want GPU training."
        )


def build_datasets(dataset_dir, batch_size, validation_split, seed):
    train_ds = keras.utils.image_dataset_from_directory(
        dataset_dir,
        labels="inferred",
        label_mode="binary",
        validation_split=validation_split,
        subset="training",
        seed=seed,
        image_size=IMAGE_SIZE,
        batch_size=batch_size,
        shuffle=True,
    )
    val_ds = keras.utils.image_dataset_from_directory(
        dataset_dir,
        labels="inferred",
        label_mode="binary",
        validation_split=validation_split,
        subset="validation",
        seed=seed,
        image_size=IMAGE_SIZE,
        batch_size=batch_size,
        shuffle=False,
    )
    return train_ds.prefetch(AUTOTUNE), val_ds.prefetch(AUTOTUNE), train_ds.class_names


def maybe_limit_dataset(dataset, batch_size, sample_limit):
    if sample_limit <= 0:
        return dataset, None
    batches = max(1, math.ceil(sample_limit / batch_size))
    return dataset.take(batches), batches


def augmentation_layers():
    return keras.Sequential(
        [
            keras.layers.RandomFlip("horizontal"),
            keras.layers.RandomRotation(0.08),
            keras.layers.RandomZoom(0.12),
            keras.layers.RandomContrast(0.1),
        ],
        name="augmentation",
    )


def build_model(weights):
    inputs = keras.Input(shape=(*IMAGE_SIZE, 3), name="image")
    x = keras.layers.Rescaling(1.0 / 255)(inputs)
    x = augmentation_layers()(x)

    base_model = keras.applications.EfficientNetV2B0(
        include_top=False,
        weights=None if weights == "none" else weights,
        input_shape=(*IMAGE_SIZE, 3),
        pooling="avg",
    )
    base_model.trainable = False

    x = base_model(x, training=False)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Dropout(0.35)(x)
    x = keras.layers.Dense(256, activation="swish")(x)
    x = keras.layers.Dropout(0.25)(x)
    embedding = keras.layers.Dense(128, activation="relu", name="embedding")(x)
    outputs = keras.layers.Dense(1, activation="sigmoid", dtype="float32", name="prediction")(embedding)
    return keras.Model(inputs, outputs, name="verifai_efficientnetv2"), base_model


def compile_model(model, learning_rate):
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="binary_crossentropy",
        metrics=[
            keras.metrics.BinaryAccuracy(name="accuracy"),
            keras.metrics.Precision(name="precision"),
            keras.metrics.Recall(name="recall"),
            keras.metrics.AUC(name="auc"),
        ],
    )


def build_callbacks():
    MODELS_DIR.mkdir(exist_ok=True)
    return [
        keras.callbacks.EarlyStopping(monitor="val_auc", mode="max", patience=3, restore_best_weights=True),
        keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, min_lr=1e-6),
        keras.callbacks.ModelCheckpoint(MODEL_PATH, monitor="val_auc", mode="max", save_best_only=True),
        keras.callbacks.CSVLogger(MODELS_DIR / "verifai_training_log.csv"),
    ]


def collect_predictions(model, dataset):
    labels = []
    preds = []
    for batch_images, batch_labels in dataset:
        batch_preds = model.predict(batch_images, verbose=0).reshape(-1)
        preds.extend(batch_preds.tolist())
        labels.extend(batch_labels.numpy().reshape(-1).tolist())
    return np.array(labels, dtype=np.int32), np.array(preds, dtype=np.float32)


def choose_threshold(y_true, y_pred):
    precision, recall, thresholds = precision_recall_curve(y_true, y_pred)
    if len(thresholds) == 0:
        return 0.5
    f1 = (2 * precision[:-1] * recall[:-1]) / np.clip(precision[:-1] + recall[:-1], 1e-8, None)
    return float(thresholds[int(np.argmax(f1))])


def write_reports(y_true, y_pred, threshold, class_names, args):
    hard_preds = (y_pred >= threshold).astype(int)
    report = classification_report(y_true, hard_preds, target_names=class_names, digits=4)
    matrix = confusion_matrix(y_true, hard_preds)

    metadata = {
        "model_path": MODEL_PATH.name,
        "architecture": "EfficientNetV2B0",
        "image_size": list(IMAGE_SIZE),
        "input_rescale_in_model": True,
        "class_names": class_names,
        "threshold": threshold,
        "real_threshold": max(threshold, 0.8),
        "fake_threshold": max(1.0 - threshold, 0.8),
        "uncertain_margin": 0.15,
        "video_sampling_fps": 2.0,
        "video_max_frames": 120,
        "video_max_keyframes": 12,
        "train_args": vars(args),
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as metadata_file:
        json.dump(metadata, metadata_file, indent=2)

    with open(REPORT_PATH, "w", encoding="utf-8") as report_file:
        report_file.write("Classification report\n")
        report_file.write(report)
        report_file.write("\n\nConfusion matrix\n")
        report_file.write(np.array2string(matrix))

    print(report)
    print("\nConfusion matrix")
    print(matrix)


def main():
    args = parse_args()
    configure_runtime()

    train_ds, val_ds, class_names = build_datasets(
        dataset_dir=args.dataset,
        batch_size=args.batch_size,
        validation_split=args.validation_split,
        seed=args.seed,
    )
    train_ds, limited_train_steps = maybe_limit_dataset(train_ds, args.batch_size, args.sample_limit)
    val_ds, limited_val_steps = maybe_limit_dataset(val_ds, args.batch_size, args.sample_limit)

    model, base_model = build_model(args.weights)
    callbacks = build_callbacks()

    compile_model(model, args.learning_rate)
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.train_head_epochs,
        callbacks=callbacks,
        steps_per_epoch=args.steps_per_epoch or limited_train_steps,
        validation_steps=args.validation_steps or limited_val_steps,
    )

    base_model.trainable = True
    for layer in base_model.layers[:-args.fine_tune_at]:
        layer.trainable = False

    compile_model(model, args.fine_tune_learning_rate)
    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=args.train_head_epochs + args.train_full_epochs,
        initial_epoch=args.train_head_epochs,
        callbacks=callbacks,
        steps_per_epoch=args.steps_per_epoch or limited_train_steps,
        validation_steps=args.validation_steps or limited_val_steps,
    )

    best_model = keras.models.load_model(MODEL_PATH)
    y_true, y_pred = collect_predictions(best_model, val_ds)
    threshold = choose_threshold(y_true, y_pred)
    write_reports(y_true, y_pred, threshold, class_names, args)


if __name__ == "__main__":
    os.makedirs(MODELS_DIR, exist_ok=True)
    main()
