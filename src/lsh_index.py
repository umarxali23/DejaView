from collections import defaultdict

class LSHIndex:
    def __init__(self, bands=4):
        self.bands = bands
        self.buckets = defaultdict(list)

    def _get_bands(self, fingerprint):
        band_size = len(fingerprint) // self.bands
        result = []

        for i in range(self.bands):
            start = i * band_size
            end = start + band_size
            band = tuple(fingerprint[start:end])
            result.append((i, band))

        return result

    def add(self, video_name, fingerprint):
        for band_id, band in self._get_bands(fingerprint):
            self.buckets[(band_id, band)].append(video_name)

    def query(self, fingerprint):
        candidates = set()

        for band_id, band in self._get_bands(fingerprint):
            candidates.update(self.buckets.get((band_id, band), []))

        return candidates