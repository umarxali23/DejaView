import cv2
import numpy as np

def extract_histogram(frame, bins=16):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (64, 64))

    hist = cv2.calcHist([resized], [0], None, [bins], [0, 256])
    hist = cv2.normalize(hist, hist).flatten()

    return hist

def video_feature_vector(frames):
    all_features = [extract_histogram(f) for f in frames]
    return np.mean(all_features, axis=0)