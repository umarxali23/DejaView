CREATE DATABASE videodb;

CREATE TABLE videos (
    id SERIAL PRIMARY KEY,
    video_name TEXT UNIQUE,
    file_path TEXT,
    fingerprint TEXT
);

CREATE TABLE similarity_results (
    id SERIAL PRIMARY KEY,
    query_video TEXT,
    matched_video TEXT,
    distance INT,
    label TEXT,
    UNIQUE (query_video, matched_video)
);