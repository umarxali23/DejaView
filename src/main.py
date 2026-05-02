import os
import pandas as pd
from video_utils import extract_frames
from feature_extractor import video_feature_vector
from simhash import simhash
from comparator import hamming_distance
from lsh_index import LSHIndex
from db import get_connection

DATASET_PATH = "data"
RESULTS_PATH = "results"


# ---------- PROCESS ----------
def process_video(video_path):
    frames = extract_frames(video_path)
    features = video_feature_vector(frames)
    fingerprint = simhash(features)
    return fingerprint


# ---------- DB ----------
def save_to_db(video, path, fingerprint):
    conn = get_connection()
    cur = conn.cursor()

    fp_str = ''.join(map(str, fingerprint))

    cur.execute("""
        INSERT INTO videos (video_name, file_path, fingerprint)
        VALUES (%s, %s, %s)
        ON CONFLICT (video_name) DO NOTHING
    """, (video, path, fp_str))

    conn.commit()
    cur.close()
    conn.close()


def load_from_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT video_name, fingerprint FROM videos")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    data = {}
    for name, fp in rows:
        data[name] = [int(b) for b in fp]

    return data


def save_similarity(query, matched_video, distance, label):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO similarity_results (query_video, matched_video, distance, label)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (query_video, matched_video)
        DO UPDATE SET
            distance = EXCLUDED.distance,
            label = EXCLUDED.label
    """, (query, matched_video, distance, label))

    conn.commit()
    cur.close()
    conn.close()


# ---------- HELPERS ----------
def classify_distance(distance):
    if distance <= 5:
        return "Duplicate"
    elif distance <= 15:
        return "Near-Duplicate"
    else:
        return "Different"


def ensure_results_folder():
    os.makedirs(RESULTS_PATH, exist_ok=True)


# ---------- MAIN ----------
def main():
    ensure_results_folder()

    videos = [f for f in os.listdir(DATASET_PATH) if f.lower().endswith(".mp4")]

    if not videos:
        print("No .mp4 videos found in data folder.")
        return

    # -------- INDEXING --------
    print("\nIndexing videos...\n")

    for video in videos:
        path = os.path.join(DATASET_PATH, video)
        print(f"Processing: {video}")
        fingerprint = process_video(path)
        save_to_db(video, path, fingerprint)

    # -------- LOAD FROM DB --------
    fingerprints = load_from_db()

    # -------- PANDAS EXPORT --------
    df = pd.DataFrame([
        {"video": name, "fingerprint": ''.join(map(str, fp))}
        for name, fp in fingerprints.items()
    ])

    df.to_csv(os.path.join(RESULTS_PATH, "fingerprints.csv"), index=False)
    df.to_parquet(os.path.join(RESULTS_PATH, "fingerprints.parquet"))

    print("\nStored fingerprints:")
    print(df.head())

    # -------- LSH INDEX --------
    index = LSHIndex(bands=4)

    for video, fp in fingerprints.items():
        index.add(video, fp)

    # -------- SEARCH SYSTEM --------
    print("\nAvailable videos:")
    for video in fingerprints.keys():
        print("-", video)

    query_video = input("\nEnter exact video name to search: ").strip()

    if query_video not in fingerprints:
        print("\nError: Video not found in database.")
        return

    print(f"\nQuery Video: {query_video}")

    query_fp = fingerprints[query_video]
    candidates = index.query(query_fp)

    print(f"\nTotal videos in database: {len(fingerprints)}")
    print(f"Candidates found by LSH: {len(candidates)}")

    results = []

    for candidate in candidates:
        if candidate != query_video:
            distance = hamming_distance(query_fp, fingerprints[candidate])
            label = classify_distance(distance)

            results.append((candidate, distance, label))
            save_similarity(query_video, candidate, distance, label)

    results.sort(key=lambda x: x[1])

    print("\nTop Matches:")
    if not results:
        print("No candidates found.")
    else:
        for video, distance, label in results:
            print(f"{video} -> {distance} ({label})")

    # -------- SAVE SEARCH RESULTS --------
    res_df = pd.DataFrame(results, columns=["matched_video", "distance", "label"])
    res_df.insert(0, "query_video", query_video)

    res_df.to_csv(os.path.join(RESULTS_PATH, "search_results.csv"), index=False)

    print("\nSearch results saved to:")
    print("- results/search_results.csv")
    print("- PostgreSQL similarity_results table")


if __name__ == "__main__":
    main()