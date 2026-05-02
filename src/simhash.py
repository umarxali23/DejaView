import hashlib
import numpy as np

def hash_feature(feature_name, hash_bits=64):
    h = hashlib.md5(feature_name.encode()).hexdigest()
    bin_str = bin(int(h, 16))[2:].zfill(hash_bits)
    return [int(b) for b in bin_str[:hash_bits]]

def simhash(features, hash_bits=64):
    vector = np.zeros(hash_bits)

    for i, weight in enumerate(features):
        feature_name = f"bin_{i}"
        hashed = hash_feature(feature_name, hash_bits)

        for j in range(hash_bits):
            if hashed[j] == 1:
                vector[j] += weight
            else:
                vector[j] -= weight

    fingerprint = [1 if v > 0 else 0 for v in vector]
    return fingerprint