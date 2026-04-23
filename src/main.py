import os
from video_utils import extract_frames
from feature_extractor import video_feature_vector
from simhash import simhash
from comparator import hamming_distance

DATASET_PATH = "data"

def process_video(video_path):
    frames = extract_frames(video_path)
    features = video_feature_vector(frames)
    fingerprint = simhash(features)
    return fingerprint

def main():
    videos = [f for f in os.listdir(DATASET_PATH) if f.lower().endswith(".mp4")]

    fingerprints = {}

    # Generate fingerprints
    for video in videos:
        path = os.path.join(DATASET_PATH, video)
        print(f"Processing {video}...")
        fingerprints[video] = process_video(path)

    # Compare all pairs
    print("\n--- Similarity Matrix ---")
    for v1 in videos:
        for v2 in videos:
            dist = hamming_distance(fingerprints[v1], fingerprints[v2])
            print(f"{v1} vs {v2} = {dist}")
        print()

if __name__ == "__main__":
    main()