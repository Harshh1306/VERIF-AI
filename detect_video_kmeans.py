import cv2
import numpy as np
import tensorflow as tf
from sklearn.cluster import KMeans

model = tf.keras.models.load_model("models/verifai_model_final.h5")

video_path = "test_video.mp4"
cap = cv2.VideoCapture(video_path)

frames = []

print("Extracting frames...")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (224,224))
    frames.append(frame)

cap.release()

print("Total frames:", len(frames))

# embeddings
embeddings = []

print("Generating embeddings...")

for frame in frames:
    img = frame / 255.0
    img = np.reshape(img, (1,224,224,3))

    embedding = model.predict(img, verbose=0)
    embeddings.append(embedding.flatten())

embeddings = np.array(embeddings)

# K-Means
k = min(10, len(frames))

print("Applying K-Means...")

kmeans = KMeans(n_clusters=k, random_state=42)
kmeans.fit(embeddings)

centers = kmeans.cluster_centers_
keyframes = []

for center in centers:
    distances = np.linalg.norm(embeddings - center, axis=1)
    index = np.argmin(distances)
    keyframes.append(frames[index])

print("Keyframes extracted:", len(keyframes))

# detection
fake_count = 0
real_count = 0

for frame in keyframes:
    img = frame / 255.0
    img = np.reshape(img, (1,224,224,3))

    prediction = model.predict(img, verbose=0)
    score = prediction[0][0]

    if score < 0.5:
        fake_count += 1
    else:
        real_count += 1

print("Fake frames:", fake_count)
print("Real frames:", real_count)

if fake_count > real_count:
    print("FAKE VIDEO")
else:
    print("REAL VIDEO")