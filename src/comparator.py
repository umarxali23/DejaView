def hamming_distance(hash1, hash2):
    return sum(h1 != h2 for h1, h2 in zip(hash1, hash2))