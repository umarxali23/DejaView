import cv2
import numpy as np

def extract_features(frame, bins=32):
    resized = cv2.resize(frame, (64, 64))

    # Grayscale with brightness normalization
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    gray_equalized = cv2.equalizeHist(gray)

    # Grayscale histogram
    gray_hist = cv2.calcHist([gray_equalized], [0], None, [bins], [0, 256])
    gray_hist = cv2.normalize(gray_hist, gray_hist).flatten()

    # Edge histogram
    edges = cv2.Canny(gray_equalized, 100, 200)
    edge_hist = cv2.calcHist([edges], [0], None, [bins], [0, 256])
    edge_hist = cv2.normalize(edge_hist, edge_hist).flatten()

    # Color histograms: B, G, R
    color_features = []
    for channel in range(3):
        hist = cv2.calcHist([resized], [channel], None, [bins], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        color_features.extend(hist)

    # Combine all visual features
    return np.concatenate([
        gray_hist,
        edge_hist,
        np.array(color_features)
    ])


def video_feature_vector(frames):
    if len(frames) == 0:
        raise ValueError("No frames extracted from video.")

    all_features = [extract_features(frame) for frame in frames]
    return np.mean(all_features, axis=0)