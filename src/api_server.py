import cgi
import json
import mimetypes
import os
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "dejaview.db"
DATA_PATH = ROOT / "data"

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from comparator import hamming_distance
from lsh_index import LSHIndex
from video_utils import extract_frames
from feature_extractor import video_feature_vector
from simhash import simhash


def connect():
    return sqlite3.connect(DB_PATH)


def init_db():
    DATA_PATH.mkdir(exist_ok=True)

    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_name TEXT UNIQUE,
                file_path TEXT,
                fingerprint TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS similarity_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_video TEXT,
                matched_video TEXT,
                distance INTEGER,
                label TEXT,
                UNIQUE (query_video, matched_video)
            )
        """)


def classify_distance(distance):
    if distance <= 3:
        return "Duplicate"
    if distance <= 5:
        return "Near-Duplicate"
    return "Unrelated"


def classify_frame_similarity(score):
    if score >= 0.80:
        return "Strong Match"
    if score >= 0.50:
        return "Possible Near-Duplicate"
    return "Weak Match"


def process_video(video_path):
    frames = extract_frames(video_path, interval_sec=1)
    features = video_feature_vector(frames)
    return simhash(features)


def save_video_fingerprint(video_name, file_path, fingerprint):
    fp_str = "".join(map(str, fingerprint))

    with connect() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO videos (video_name, file_path, fingerprint)
            VALUES (?, ?, ?)
        """, (video_name, file_path, fp_str))


def frame_level_hashes(video_path, interval_sec=1, max_frames=10):
    frames = extract_frames(video_path, interval_sec=interval_sec)
    frames = frames[:max_frames]

    hashes = []
    for frame in frames:
        features = video_feature_vector([frame])
        hashes.append(simhash(features))

    return hashes


def frame_vote_similarity(query_hashes, candidate_hashes, frame_threshold=5):
    if not query_hashes or not candidate_hashes:
        return 0

    matched_frames = 0

    for query_hash in query_hashes:
        for candidate_hash in candidate_hashes:
            if hamming_distance(query_hash, candidate_hash) <= frame_threshold:
                matched_frames += 1
                break

    return matched_frames / len(query_hashes)


def list_media_files():
    if not DATA_PATH.exists():
        return []

    return sorted(
        file.name
        for file in DATA_PATH.iterdir()
        if file.is_file() and file.suffix.lower() == ".mp4"
    )


def load_videos():
    init_db()
    files_on_disk = set(list_media_files())

    with connect() as conn:
        rows = conn.execute("""
            SELECT video_name, file_path, fingerprint
            FROM videos
            ORDER BY lower(video_name)
        """).fetchall()

    return [
        {
            "name": name,
            "path": path,
            "fingerprint": fingerprint,
            "fingerprintBits": len(fingerprint or ""),
            "available": name in files_on_disk or Path(path or "").name in files_on_disk,
            "mediaUrl": f"/media/{name}",
        }
        for name, path, fingerprint in rows
    ]


def load_fingerprints():
    videos = load_videos()

    return {
        video["name"]: [int(bit) for bit in video["fingerprint"]]
        for video in videos
        if video["fingerprint"]
    }


def run_search(query_video):
    fingerprints = load_fingerprints()

    if query_video not in fingerprints:
        raise ValueError("Video not found in the fingerprint database.")

    index = LSHIndex(bands=4)

    for video, fingerprint in fingerprints.items():
        index.add(video, fingerprint)

    query_fp = fingerprints[query_video]
    raw_candidates = index.query_multiprobe(query_fp)

    stage_one = []
    final_results = []

    query_path = DATA_PATH / query_video
    query_frame_hashes = frame_level_hashes(str(query_path))

    with connect() as conn:
        for candidate in raw_candidates:
            if candidate == query_video:
                continue

            distance = hamming_distance(query_fp, fingerprints[candidate])
            label = classify_distance(distance)

            stage_one.append({
                "matchedVideo": candidate,
                "distance": distance,
                "label": label,
                "confidence": max(0, round((1 - distance / len(query_fp)) * 100)),
            })

            if distance > 5:
                continue

            candidate_path = DATA_PATH / candidate
            candidate_frame_hashes = frame_level_hashes(str(candidate_path))

            frame_score = frame_vote_similarity(
                query_frame_hashes,
                candidate_frame_hashes,
                frame_threshold=5
            )

            frame_label = classify_frame_similarity(frame_score)

            if frame_score < 0.50:
                continue

            confidence = round(frame_score * 100)

            final_results.append({
                "matchedVideo": candidate,
                "distance": distance,
                "label": label,
                "confidence": confidence,
                "frameSimilarity": round(frame_score, 2),
                "frameLabel": frame_label,
            })

            conn.execute("""
                INSERT OR REPLACE INTO similarity_results
                (query_video, matched_video, distance, label)
                VALUES (?, ?, ?, ?)
            """, (query_video, candidate, distance, label))

    stage_one.sort(key=lambda item: item["distance"])
    final_results.sort(key=lambda item: (-item["frameSimilarity"], item["distance"]))

    return {
        "queryVideo": query_video,
        "totalVideos": len(fingerprints),
        "rawCandidates": len(raw_candidates),
        "stageOneResults": stage_one,
        "candidates": len(final_results),
        "results": final_results,
    }


def index_videos():
    indexed = []

    for video in list_media_files():
        path = DATA_PATH / video
        fingerprint = process_video(str(path))
        save_video_fingerprint(video, str(path), fingerprint)
        indexed.append(video)

    return {"indexed": indexed, "count": len(indexed)}


def upload_video(handler):
    content_type = handler.headers.get("Content-Type", "")

    if "multipart/form-data" not in content_type:
        raise ValueError("Upload must use multipart/form-data.")

    form = cgi.FieldStorage(
        fp=handler.rfile,
        headers=handler.headers,
        environ={
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": content_type,
        },
    )

    if "video" not in form:
        raise ValueError("No video file found in upload.")

    file_item = form["video"]

    if not file_item.filename:
        raise ValueError("No selected file.")

    filename = Path(file_item.filename).name

    if not filename.lower().endswith(".mp4"):
        raise ValueError("Only .mp4 videos are supported.")

    DATA_PATH.mkdir(exist_ok=True)
    target_path = DATA_PATH / filename

    with target_path.open("wb") as target:
        target.write(file_item.file.read())

    fingerprint = process_video(str(target_path))
    save_video_fingerprint(filename, str(target_path), fingerprint)

    return {
        "uploaded": filename,
        "videos": load_videos(),
        "files": list_media_files(),
    }


class ApiHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            return self.send_json({"ok": True})

        if parsed.path == "/api/videos":
            return self.send_json({"videos": load_videos(), "files": list_media_files()})

        if parsed.path.startswith("/media/"):
            return self.send_media(parsed.path.removeprefix("/media/"))

        self.send_error(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)

        try:
            if parsed.path == "/api/search":
                body = self.read_json()
                return self.send_json(run_search(body.get("queryVideo", "")))

            if parsed.path == "/api/index":
                return self.send_json(index_videos())

            if parsed.path == "/api/upload":
                return self.send_json(upload_video(self))

        except (RuntimeError, ValueError) as exc:
            return self.send_json({"error": str(exc)}, status=400)

        except Exception as exc:
            return self.send_json({"error": str(exc)}, status=500)

        self.send_error(404, "Not found")

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def send_json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_media(self, raw_name):
        name = unquote(raw_name)
        target = (DATA_PATH / name).resolve()

        if not str(target).startswith(str(DATA_PATH.resolve())) or not target.exists():
            self.send_error(404, "Media not found")
            return

        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(target.stat().st_size))
        self.end_headers()

        with target.open("rb") as media:
            while chunk := media.read(1024 * 256):
                self.wfile.write(chunk)

    def log_message(self, format, *args):
        print(f"[api] {self.address_string()} - {format % args}")


def run(host="127.0.0.1", port=8000):
    init_db()
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"DejaView API running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run(
        host=os.environ.get("DEJAVIEW_HOST", "127.0.0.1"),
        port=int(os.environ.get("DEJAVIEW_PORT", "8000")),
    )