import tensorflow as tf
import numpy as np
import cv2

model = tf.keras.models.load_model("models/verifai_model_final.h5")

img = cv2.imread("test.jpg")

img = cv2.resize(img, (224,224))
img = img / 255.0
img = np.reshape(img, (1,224,224,3))

prediction = model.predict(img)

score = prediction[0][0]

fake_prob = 1 - score
real_prob = score

print("Fake:", fake_prob)
print("Real:", real_prob)

if fake_prob > real_prob:
    print("FAKE IMAGE")
else:
    print("REAL IMAGE")