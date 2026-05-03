import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  Database,
  Fingerprint,
  Gauge,
  Play,
  RefreshCw,
  ScanSearch,
  Server,
  Upload,
  Video,
  Zap,
} from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

const labelTone = {
  Duplicate: "hot",
  "Near-Duplicate": "warm",
  Unrelated: "cool",
};

function App() {
  const [videos, setVideos] = useState([]);
  const [files, setFiles] = useState([]);
  const [queryVideo, setQueryVideo] = useState("");
  const [search, setSearch] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [uploadMessage, setUploadMessage] = useState("");

  const availableVideos = useMemo(
    () => videos.filter((video) => video.available),
    [videos],
  );

  const verifiedResults = search?.results || [];
  const stageOneResults = search?.stageOneResults || [];
  const topMatch = verifiedResults[0];

  async function request(path, options) {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Request failed");
    }

    return data;
  }

  async function loadVideos() {
    setError("");
    const data = await request("/api/videos");
    setVideos(data.videos);
    setFiles(data.files);
    setQueryVideo((current) => current || data.videos[0]?.name || "");
  }

  async function searchVideo(name = queryVideo) {
    if (!name) return;

    setLoading(true);
    setError("");
    setUploadMessage("");

    try {
      const data = await request("/api/search", {
        method: "POST",
        body: JSON.stringify({ queryVideo: name }),
      });

      setSearch(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function uploadVideo(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".mp4")) {
      setError("Only .mp4 videos are supported.");
      return;
    }

    setUploading(true);
    setError("");
    setUploadMessage("");

    try {
      const formData = new FormData();
      formData.append("video", file);

      const response = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Upload failed");
      }

      setVideos(data.videos);
      setFiles(data.files);
      setQueryVideo(data.uploaded);
      setSearch(null);
      setUploadMessage(`${data.uploaded} uploaded and indexed successfully.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  useEffect(() => {
    loadVideos().catch((err) => setError(err.message));
  }, []);

  const selectedVideo = videos.find((video) => video.name === queryVideo);

  return (
    <main className="app-shell">
      <section className="hero-band">
        <div className="hero-copy">
    

          <h1>DejaView</h1>

          <p>
            A video similarity system using SimHash, LSH candidate retrieval,
            and frame-level verification.
          </p>

          <div className="hero-actions">
            <button className="primary-button" onClick={() => searchVideo()}>
              {loading ? <RefreshCw className="spin" /> : <ScanSearch />}
              <span>{loading ? "Scanning" : "Run scan"}</span>
            </button>

            <label className="upload-button">
              {uploading ? <RefreshCw className="spin" /> : <Upload />}
              <span>{uploading ? "Uploading" : "Upload video"}</span>
              <input type="file" accept="video/mp4" onChange={uploadVideo} />
            </label>
          </div>

          {uploadMessage && <div className="success-strip">{uploadMessage}</div>}
        </div>

        <div className="signal-panel calm-panel">
          <div className="hero-card-title">
            <Fingerprint size={42} />
            <h2>DataView</h2>
            <p></p>
          </div>

          <div className="signal-readouts">
            <Metric icon={<Video />} label="Fingerprints" value={videos.length} />
            <Metric icon={<Play />} label="Playable files" value={availableVideos.length} />
            <Metric icon={<Zap />} label="Verified matches" value={verifiedResults.length} />
          </div>
        </div>
      </section>

      {error && (
        <div className="error-strip">
          <Server size={18} />
          <span>{error}</span>
        </div>
      )}

      <section className="workspace-grid">
        <div className="panel query-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Query video</span>
              <h2>Choose or upload a video</h2>
            </div>
            <Activity />
          </div>

          <select
            value={queryVideo}
            onChange={(event) => {
              setQueryVideo(event.target.value);
              setSearch(null);
            }}
          >
            {videos.map((video) => (
              <option key={video.name} value={video.name}>
                {video.name}
              </option>
            ))}
          </select>

          {selectedVideo?.available ? (
            <video
              className="video-preview"
              src={`${API_BASE}${selectedVideo.mediaUrl}`}
              controls
            />
          ) : (
            <div className="missing-preview">
              <Video size={38} />
              <span>Video file is indexed but missing from /data.</span>
            </div>
          )}

          <div className="fingerprint-strip full-fingerprint" aria-label="fingerprint bits">
            {(selectedVideo?.fingerprint || "").split("").map((bit, index) => (
              <span key={`${bit}-${index}`} className={bit === "1" ? "on" : ""} />
            ))}
          </div>
        </div>

        <div className="panel results-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Final result</span>
              <h2>Verified matches</h2>
            </div>
            <Gauge />
          </div>

          <div className="summary-grid two-metrics">
            <Metric icon={<Database />} label="Database" value={search?.totalVideos ?? videos.length} />
            <Metric icon={<ScanSearch />} label="Raw LSH candidates" value={search?.rawCandidates ?? 0} />
          </div>

          <div className="match-stage clean-stage">
            {topMatch ? (
              <>
                <div className="best-match-copy">
                  <span className="eyebrow">Best verified match</span>
                  <h3>{topMatch.matchedVideo}</h3>
                  <p>
                    Frame similarity: {topMatch.frameSimilarity} | Hamming distance:{" "}
                    {topMatch.distance}
                  </p>
                </div>

                <div className={`score-ring ${labelTone[topMatch.label]}`}>
                  <span>{topMatch.confidence}%</span>
                  <small>{topMatch.frameLabel}</small>
                </div>
              </>
            ) : search ? (
              <div className="empty-state">
                <ScanSearch size={34} />
                <span>No duplicates or near-duplicates found.</span>
              </div>
            ) : (
              <div className="empty-state">
                <ScanSearch size={34} />
                <span>Run a scan to find verified matches.</span>
              </div>
            )}
          </div>

          <div className="results-list">
            {verifiedResults.map((result, index) => (
              <article
                className="match-row"
                key={result.matchedVideo}
                style={{ "--match-delay": `${index * 70}ms` }}
              >
                <div
                  className={`confidence-bar ${labelTone[result.label]}`}
                  style={{ "--confidence": `${result.confidence}%` }}
                />

                <div>
                  <h3>{result.matchedVideo}</h3>
                  <p>
                    Stage 1 distance: {result.distance} | Stage 2 frame score:{" "}
                    {result.frameSimilarity}
                  </p>
                </div>

                <span className={`pill ${labelTone[result.label]}`}>
                  {result.label}
                </span>
              </article>
            ))}
          </div>
        </div>
      </section>

      {search && (
        <section className="process-band">
          <div className="section-title">
            <span className="eyebrow">Detection process</span>
            <h2>Two-stage matching pipeline</h2>
          </div>

          <div className="process-grid">
            <div className="panel process-panel">
              <span className="eyebrow">Stage 1</span>
              <h3>Global SimHash + LSH</h3>
              <p>
                LSH retrieved {search.rawCandidates} raw candidates. Hamming
                distance was then used to filter possible duplicates.
              </p>

              <div className="results-list compact-list">
                {stageOneResults.slice(0, 6).map((result) => (
                  <article className="match-row" key={`stage-one-${result.matchedVideo}`}>
                    <div>
                      <h3>{result.matchedVideo}</h3>
                      <p>Distance {result.distance}</p>
                    </div>
                    <span className={`pill ${labelTone[result.label]}`}>
                      {result.label}
                    </span>
                  </article>
                ))}
              </div>
            </div>

            <div className="panel process-panel">
              <span className="eyebrow">Stage 2</span>
              <h3>Frame-level verification</h3>
              <p>
                Final results are kept only when frame-level voting confirms
                visual similarity.
              </p>

              <div className="results-list compact-list">
                {verifiedResults.length ? (
                  verifiedResults.map((result) => (
                    <article className="match-row" key={`verified-${result.matchedVideo}`}>
                      <div>
                        <h3>{result.matchedVideo}</h3>
                        <p>Frame similarity {result.frameSimilarity}</p>
                      </div>
                      <span className={`pill ${labelTone[result.label]}`}>
                        {result.frameLabel}
                      </span>
                    </article>
                  ))
                ) : (
                  <div className="empty-state small-empty">
                    No verified duplicate matches.
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>
      )}

      <section className="library-band">
        <div className="section-title">
          <span className="eyebrow">Dataset library</span>
          <h2>{files.length} MP4 files found on disk</h2>
        </div>

        <div className="video-grid">
          {videos.map((video) => (
            <article className="video-card" key={video.name}>
              <div className="video-card-top">
                <Video size={20} />
                <span className={video.available ? "status live" : "status"}>
                  {video.available ? "Live" : "Missing"}
                </span>
              </div>

              <h3>{video.name}</h3>
              <p>{video.fingerprintBits} bit SimHash fingerprint</p>

              <div className="mini-fingerprint full-mini-fingerprint" aria-hidden="true">
                {(video.fingerprint || "").split("").map((bit, index) => (
                  <span
                    key={`${video.name}-${index}`}
                    className={bit === "1" ? "on" : ""}
                  />
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

function Metric({ icon, label, value }) {
  return (
    <div className="metric">
      {React.cloneElement(icon, { size: 18 })}
      <div>
        <strong>{value}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);