import tensorflow as tf
import numpy as np
import cv2

# load your FINAL model
model = tf.keras.models.load_model("models/verifai_model_final.h5")

# image path
image_path = "test.jpg"

# read image
img = cv2.imread(image_path)

if img is None:
    print("❌ Image not found!")
    exit()

# resize
img = cv2.resize(img, (224,224))

# normalize
img = img / 255.0

# reshape
img = np.reshape(img, (1,224,224,3))

# predict
prediction = model.predict(img)

score = prediction[0][0]

# probabilities
fake_prob = 1 - score
real_prob = score

print(f"Fake Probability: {fake_prob:.2f}")
print(f"Real Probability: {real_prob:.2f}")

# final decision
if fake_prob > real_prob:
    print("⚠️ FAKE IMAGE DETECTED")
else:
    print("✅ REAL IMAGE")