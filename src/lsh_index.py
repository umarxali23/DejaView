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
    
    # -------- NEW MULTI-PROBE LSH METHODS --------

    def _generate_neighbors(self, band):
        """Generates the original band, plus all variations with exactly 1 bit flipped."""
        neighbors = [band] # Always check the original exact match first
        
        # Loop through the 16 bits. Flip one bit at a time to create a "neighbor"
        for i in range(len(band)):
            neighbor = list(band)
            neighbor[i] = 1 if neighbor[i] == 0 else 0 # Flip 1 to 0, or 0 to 1
            neighbors.append(tuple(neighbor))
            
        return neighbors

    def query_multiprobe(self, fingerprint):
        """Searches the exact bucket AND neighboring buckets for candidates."""
        candidates = set()
        for band_id, band in self._get_bands(fingerprint):
            # Instead of checking just one bucket, we check 17 buckets (1 exact + 16 neighbors)
            for probe_band in self._generate_neighbors(band):
                candidates.update(self.buckets.get((band_id, probe_band), []))
        return candidates