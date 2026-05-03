import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  Database,
  Fingerprint,
  Gauge,
  Play,
  Radar,
  RefreshCw,
  ScanSearch,
  Server,
  Sparkles,
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

const radarDotPositions = [
  { left: "24%", top: "34%" },
  { left: "67%", top: "28%" },
  { left: "76%", top: "66%" },
  { left: "38%", top: "72%" },
  { left: "52%", top: "48%" },
];

const particlePositions = [
  { left: "9%", top: "18%" },
  { left: "24%", top: "72%" },
  { left: "37%", top: "31%" },
  { left: "48%", top: "86%" },
  { left: "58%", top: "16%" },
  { left: "69%", top: "58%" },
  { left: "78%", top: "35%" },
  { left: "86%", top: "80%" },
  { left: "14%", top: "48%" },
  { left: "92%", top: "22%" },
];

function App() {
  const [videos, setVideos] = useState([]);
  const [files, setFiles] = useState([]);
  const [queryVideo, setQueryVideo] = useState("");
  const [search, setSearch] = useState(null);
  const [loading, setLoading] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [error, setError] = useState("");

  const availableVideos = useMemo(
    () => videos.filter((video) => video.available),
    [videos],
  );

  const duplicateCount = search?.results?.filter(
    (result) => result.label === "Duplicate",
  ).length;

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
    try {
      setSearch(
        await request("/api/search", {
          method: "POST",
          body: JSON.stringify({ queryVideo: name }),
        }),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function indexDataset() {
    setIndexing(true);
    setError("");
    try {
      await request("/api/index", { method: "POST" });
      await loadVideos();
    } catch (err) {
      setError(err.message);
    } finally {
      setIndexing(false);
    }
  }

  useEffect(() => {
    loadVideos().catch((err) => setError(err.message));
  }, []);

  const selectedVideo = videos.find((video) => video.name === queryVideo);
  const topMatch = search?.results?.[0];

  return (
    <main className="app-shell">
      <div className="ambient-scene" aria-hidden="true">
        <div className="scanline-field" />
        <div className="signal-particles">
          {particlePositions.map((particle, index) => (
            <span
              key={index}
              style={{
                "--particle-index": index,
                left: particle.left,
                top: particle.top,
              }}
            />
          ))}
        </div>
        <div className="wave-layer wave-one" />
        <div className="wave-layer wave-two" />
      </div>

      <section className="hero-band">
        <div className="hero-copy">
          <div className="brand-mark">
            <Radar size={20} />
            <span>DejaView</span>
          </div>
          <h1>DejaView</h1>
          <p>
            Find duplicate and near-duplicate videos by comparing visual
            fingerprints from your local dataset.
          </p>
          <div className="hero-actions">
            <button className="primary-button" onClick={() => searchVideo()}>
              {loading ? <RefreshCw className="spin" /> : <ScanSearch />}
              <span>{loading ? "Scanning" : "Run scan"}</span>
            </button>
            <button className="ghost-button" onClick={indexDataset}>
              {indexing ? <RefreshCw className="spin" /> : <Database />}
              <span>{indexing ? "Indexing" : "Index dataset"}</span>
            </button>
          </div>
        </div>

        <div className="signal-panel">
          <div className="orbital-ring">
            <div className="pulse-core">
              <Fingerprint size={54} />
            </div>
          </div>
          <div className="signal-readouts">
            <Metric icon={<Video />} label="Fingerprints" value={videos.length} />
            <Metric icon={<Play />} label="Playable files" value={availableVideos.length} />
            <Metric icon={<Zap />} label="Matches" value={search?.results?.length ?? 0} />
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
              <h2>Choose a fingerprint</h2>
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
          <div className="select-glow" />

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

          <div className="fingerprint-strip" aria-label="fingerprint bits">
            <div className="fingerprint-scan" />
            {(selectedVideo?.fingerprint || "").split("").map((bit, index) => (
              <span key={`${bit}-${index}`} className={bit === "1" ? "on" : ""} />
            ))}
          </div>
        </div>

        <div className="panel results-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">LSH results</span>
              <h2>Similarity radar</h2>
            </div>
            <Gauge />
          </div>

          <div className="summary-grid">
            <Metric icon={<Database />} label="Database" value={search?.totalVideos ?? videos.length} />
            <Metric icon={<Radar />} label="Candidates" value={search?.candidates ?? 0} />
            <Metric icon={<Sparkles />} label="Duplicates" value={duplicateCount ?? 0} />
          </div>

          <div className="match-stage">
            <div className={`radar-surface ${search ? "active" : ""}`}>
              {radarDotPositions.map((dot, index) => (
                <span
                  className="radar-dot"
                  key={index}
                  style={{
                    left: dot.left,
                    top: dot.top,
                    animationDelay: `${index * 180}ms`,
                  }}
                />
              ))}
            </div>
            {topMatch ? (
              <>
                <div className="best-match-copy">
                  <span className="eyebrow">Best match</span>
                  <h3>{topMatch.matchedVideo}</h3>
                </div>
                <div className={`score-ring ${labelTone[topMatch.label]}`}>
                  <span>{topMatch.confidence}%</span>
                  <small>{topMatch.label}</small>
                </div>
              </>
            ) : (
              <div className="empty-state">
                <ScanSearch size={34} />
                <span>Run a scan to light up candidate matches.</span>
              </div>
            )}
          </div>

          <div className="results-list">
            {(search?.results || []).map((result, index) => (
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
                  <p>Hamming distance {result.distance}</p>
                </div>
                <span className={`pill ${labelTone[result.label]}`}>
                  {result.label}
                </span>
              </article>
            ))}
          </div>
        </div>
      </section>

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
              <div className="mini-fingerprint" aria-hidden="true">
                {(video.fingerprint || "").slice(0, 32).split("").map((bit, index) => (
                  <span key={`${video.name}-${index}`} className={bit === "1" ? "on" : ""} />
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
