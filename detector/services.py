import json
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np

_cv2 = None
_tf = None
_MiniBatchKMeans = None


def _get_cv2():
    global _cv2
    if _cv2 is None:
        import cv2
        _cv2 = cv2
    return _cv2


def _get_tf():
    global _tf
    if _tf is None:
        import tensorflow as tf
        _original_depthwise_init = tf.keras.layers.DepthwiseConv2D.__init__

        def _patched_depthwise_init(self, *args, **kwargs):
            kwargs.pop('groups', None)
            _original_depthwise_init(self, *args, **kwargs)

        tf.keras.layers.DepthwiseConv2D.__init__ = _patched_depthwise_init
        _tf = tf
    return _tf


def _get_kmeans_cls():
    global _MiniBatchKMeans
    if _MiniBatchKMeans is None:
        from sklearn.cluster import MiniBatchKMeans
        _MiniBatchKMeans = MiniBatchKMeans
    return _MiniBatchKMeans


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / 'models' / 'verifai_model_final.h5'
METADATA_PATH = BASE_DIR / 'models' / 'verifai_model_meta.json'
DEFAULT_IMAGE_SIZE = (224, 224)

_MODEL = None
_FEATURE_MODEL = None
_INFERENCE_MODEL = None
_METADATA = None


def _default_metadata():
    return {
        'threshold': 0.5,
        'real_threshold': 0.8,
        'fake_threshold': 0.8,
        'uncertain_margin': 0.15,
        'video_sampling_fps': 1.0,
        'video_max_frames': 48,
        'video_max_keyframes': 6,
        'image_size': list(DEFAULT_IMAGE_SIZE),
        'input_rescale_in_model': False,
    }


def get_metadata():
    global _METADATA
    if _METADATA is None:
        if METADATA_PATH.exists():
            with open(METADATA_PATH, 'r', encoding='utf-8') as metadata_file:
                _METADATA = {**_default_metadata(), **json.load(metadata_file)}
        else:
            _METADATA = _default_metadata()
    return _METADATA


def get_image_size():
    size = get_metadata().get('image_size', list(DEFAULT_IMAGE_SIZE))
    return int(size[0]), int(size[1])


def get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = _get_tf().keras.models.load_model(MODEL_PATH)
    return _MODEL


def get_feature_model():
    global _FEATURE_MODEL
    model = get_model()
    if _FEATURE_MODEL is None:
        try:
            embedding_layer = model.get_layer('embedding')
        except ValueError:
            embedding_layer = model.layers[-2]
        _FEATURE_MODEL = _get_tf().keras.Model(model.input, embedding_layer.output)
    return _FEATURE_MODEL


def get_inference_model():
    global _INFERENCE_MODEL
    model = get_model()
    if _INFERENCE_MODEL is None:
        try:
            embedding_layer = model.get_layer('embedding')
        except ValueError:
            embedding_layer = model.layers[-2]
        _INFERENCE_MODEL = _get_tf().keras.Model(
            model.input,
            [model.output, embedding_layer.output],
        )
    return _INFERENCE_MODEL


def _prepare_image_array(frames):
    image_size = get_image_size()
    cv2 = _get_cv2()
    processed = [cv2.resize(frame, image_size) for frame in frames]
    batch = np.asarray(processed, dtype=np.float32)
    if not get_metadata().get('input_rescale_in_model', False):
        batch = batch / 255.0
    return batch


def _read_uploaded_image(uploaded_file):
    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)
    if not file_bytes:
        return None
    buffer = np.frombuffer(file_bytes, dtype=np.uint8)
    cv2 = _get_cv2()
    return cv2.imdecode(buffer, cv2.IMREAD_COLOR)


def _save_upload_temporarily(uploaded_file):
    suffix = Path(uploaded_file.name).suffix
    temp_file = NamedTemporaryFile(delete=False, suffix=suffix)
    for chunk in uploaded_file.chunks():
        temp_file.write(chunk)
    temp_file.flush()
    temp_file.close()
    return Path(temp_file.name)


def _predict_probabilities_and_embeddings(batch_array):
    outputs = get_inference_model().predict(batch_array, verbose=0)
    predictions, embeddings = outputs[0], outputs[1]
    if isinstance(predictions, list):
        predictions = predictions[0]
    if isinstance(embeddings, list):
        embeddings = embeddings[0]
    return np.asarray(predictions).reshape(-1), np.asarray(embeddings)


def _classify_score(real_probability):
    metadata = get_metadata()
    fake_probability = 1.0 - real_probability
    confidence = max(real_probability, fake_probability)
    if real_probability >= metadata['real_threshold']:
        return 'real', confidence
    if fake_probability >= metadata['fake_threshold']:
        return 'fake', confidence
    return 'uncertain', confidence


def predict_image(uploaded_file):
    frame = _read_uploaded_image(uploaded_file)
    if frame is None:
        raise ValueError(
            'Unable to decode the uploaded image. Please use a standard JPG, JPEG, or PNG file.'
        )

    batch = _prepare_image_array([frame])
    raw_prediction = get_model().predict(batch, verbose=0)
    if isinstance(raw_prediction, list):
        raw_prediction = raw_prediction[0]
    real_probability = float(np.asarray(raw_prediction).reshape(-1)[0])
    fake_probability = float(1.0 - real_probability)
    label, confidence = _classify_score(real_probability)

    if label == 'uncertain':
        summary = (
            f'Image confidence is too low for a safe automatic decision. '
            f'Real probability: {real_probability * 100:.2f}%, fake probability: {fake_probability * 100:.2f}%.'
        )
    else:
        summary = (
            f"Image classified as {label.upper()} with {confidence * 100:.2f}% confidence. "
            f"Real probability: {real_probability * 100:.2f}%, fake probability: {fake_probability * 100:.2f}%."
        )

    return {
        'label': label,
        'confidence': confidence,
        'real_probability': real_probability,
        'fake_probability': fake_probability,
        'summary': summary,
    }


def _extract_video_frames(file_path):
    metadata = get_metadata()
    cv2 = _get_cv2()
    cap = cv2.VideoCapture(str(file_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    sample_every = max(1, int(round(fps / metadata['video_sampling_fps']))) if fps > 0 else 12
    max_frames = int(metadata['video_max_frames'])

    frames = []
    frame_index = 0
    while len(frames) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_index % sample_every == 0:
            frames.append(frame)
        frame_index += 1

    cap.release()
    return frames


def predict_video(uploaded_file):
    temp_path = _save_upload_temporarily(uploaded_file)
    try:
        frames = _extract_video_frames(temp_path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)

    if not frames:
        raise ValueError('Unable to extract frames from the uploaded video.')

    batch = _prepare_image_array(frames)
    probabilities, embeddings = _predict_probabilities_and_embeddings(batch)

    max_keyframes = min(int(get_metadata()['video_max_keyframes']), len(frames))
    if len(frames) <= max_keyframes:
        selected_indices = list(range(len(frames)))
    else:
        kmeans = _get_kmeans_cls()(
            n_clusters=max_keyframes,
            random_state=42,
            batch_size=min(1024, len(frames)),
        )
        kmeans.fit(embeddings)
        selected_indices = []
        for center in kmeans.cluster_centers_:
            distances = np.linalg.norm(embeddings - center, axis=1)
            selected_indices.append(int(np.argmin(distances)))
        selected_indices = sorted(set(selected_indices))

    selected_probabilities = probabilities[selected_indices]
    mean_real_probability = float(np.mean(selected_probabilities))
    mean_fake_probability = float(1.0 - mean_real_probability)
    real_votes = int(np.sum(selected_probabilities >= 0.5))
    fake_votes = int(len(selected_probabilities) - real_votes)
    label, confidence = _classify_score(mean_real_probability)

    if label == 'uncertain':
        summary = (
            f'Video review is inconclusive. Real keyframes: {real_votes}, fake keyframes: {fake_votes}, '
            f'average real probability: {mean_real_probability * 100:.2f}%.'
        )
    else:
        summary = (
            f"Video classified as {label.upper()} after batched keyframe analysis. "
            f"Real keyframes: {real_votes}, fake keyframes: {fake_votes}, "
            f"average confidence: {confidence * 100:.2f}%."
        )

    return {
        'label': label,
        'confidence': confidence,
        'real_probability': mean_real_probability,
        'fake_probability': mean_fake_probability,
        'real_frames': real_votes,
        'fake_frames': fake_votes,
        'keyframes_used': len(selected_probabilities),
        'summary': summary,
    }
