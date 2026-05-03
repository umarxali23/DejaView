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


def connect():
    return sqlite3.connect(DB_PATH)


def init_db():
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_name TEXT UNIQUE,
                file_path TEXT,
                fingerprint TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS similarity_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_video TEXT,
                matched_video TEXT,
                distance INTEGER,
                label TEXT,
                UNIQUE (query_video, matched_video)
            )
            """
        )


def classify_distance(distance):
    if distance <= 3:
        return "Duplicate"
    if distance <= 5:
        return "Near-Duplicate"
    return "Unrelated"


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
        rows = conn.execute(
            """
            SELECT video_name, file_path, fingerprint
            FROM videos
            ORDER BY lower(video_name)
            """
        ).fetchall()

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
    candidates = index.query_multiprobe(query_fp)
    results = []

    with connect() as conn:
        for candidate in candidates:
            if candidate == query_video:
                continue

            distance = hamming_distance(query_fp, fingerprints[candidate])
            label = classify_distance(distance)
            results.append(
                {
                    "matchedVideo": candidate,
                    "distance": distance,
                    "label": label,
                    "confidence": max(0, round((1 - distance / len(query_fp)) * 100)),
                }
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO similarity_results
                (query_video, matched_video, distance, label)
                VALUES (?, ?, ?, ?)
                """,
                (query_video, candidate, distance, label),
            )

    results.sort(key=lambda item: item["distance"])
    return {
        "queryVideo": query_video,
        "totalVideos": len(fingerprints),
        "candidates": len(candidates),
        "results": results,
    }


def index_videos():
    try:
        from main import process_video, save_to_db
    except ModuleNotFoundError as exc:
        missing = exc.name or "a Python package"
        raise RuntimeError(
            f"Indexing needs the missing Python package '{missing}'. "
            "Install project dependencies, then try again."
        ) from exc

    indexed = []
    for video in list_media_files():
        path = DATA_PATH / video
        fingerprint = process_video(str(path))
        save_to_db(video, str(path), fingerprint)
        indexed.append(video)

    return {"indexed": indexed, "count": len(indexed)}


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

    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/media/"):
            return self.send_media(parsed.path.removeprefix("/media/"), head_only=True)
        if parsed.path in {"/api/health", "/api/videos"}:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            return
        self.send_error(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/search":
                body = self.read_json()
                return self.send_json(run_search(body.get("queryVideo", "")))
            if parsed.path == "/api/index":
                return self.send_json(index_videos())
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

    def send_media(self, raw_name, head_only=False):
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
        if head_only:
            return

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
