import cv2
import numpy as np

def extract_frames(video_path, interval_sec=1):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)

    frames = []
    frame_interval = int(fps * interval_sec)
    count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if count % frame_interval == 0:
            frames.append(frame)

        count += 1

    cap.release()
    return frames

# Extract keyframes smartly for initial fingerprint generation.
def extract_keyframes(video_path, interval_sec=1, diff_threshold=30.0):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    frame_interval = int(fps * interval_sec)
    count = 0
    prev_gray = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if count % frame_interval == 0:
            # Convert to grayscale for fast comparison
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Always keep the very first frame
            if prev_gray is None:
                frames.append(frame)
                prev_gray = gray
            else:
                # Calculate the mathematical difference between this frame and the last one
                diff = cv2.absdiff(gray, prev_gray)
                mean_diff = np.mean(diff)

                # Only save the frame if the difference proves the scene actually changed
                if mean_diff > diff_threshold:
                    frames.append(frame)
                    prev_gray = gray # Update the baseline to the new scene
        count += 1
    cap.release()
    return frames