from __future__ import annotations
import hashlib

from ..fingerprint.field import GF256

class RandomOracle:
    @staticmethod
    def derive(fragment_hashes: list[bytes]) -> GF256:
        if not fragment_hashes:
            raise ValueError("fragment_hashes cannot be empty")

        counter = 0
        concatenated = b''.join(fragment_hashes)
        
        while True:
            digest = RandomOracle.hash_fragment(concatenated + counter.to_bytes(4, 'big'))
            r = GF256(digest[0])  # Take the first byte as the candidate point
            if r.value != 0: 
                return r
            counter += 1

    @staticmethod
    def hash_fragment(fragment_data: bytes) -> bytes:
        return hashlib.sha256(fragment_data).digest()
