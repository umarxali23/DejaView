# DejaView

DejaView fingerprints local MP4 files with visual features and SimHash, then
uses LSH to find duplicate and near-duplicate videos.

## Run the API

```bash
python src/api_server.py
```

The API runs at `http://127.0.0.1:8000`.

## Run the React UI

```bash
npm install
npm run dev
```

The UI expects the API above to be running and opens at the Vite URL printed in
the terminal.

## Indexing note

Indexing new videos needs OpenCV for Python:

```bash
python -m pip install opencv-python
```
