from __future__ import annotations
import json
from dataclasses import dataclass

from ..fingerprint.field import GF256
from ..fingerprint.fingerprint import fingerprint, random_point
from ..erasure.encoder import Fragment
from .oracle import RandomOracle


@dataclass
class FingerprintedCrossChecksum:
    hashes: list[bytes]
    fingerprints: list[GF256]
    r: GF256
    n: int
    m: int

    @classmethod
    def generate(cls, fragments: list[Fragment]) -> FingerprintedCrossChecksum:
        if not fragments:
            raise ValueError("fragments cannot be empty")
        for i, f in enumerate(fragments):
            if f.index != i:
                raise ValueError(f"fragments must be in index order with no gaps. Fragment at position {i} has index {f.index}.")

        hashes = [RandomOracle.hash_fragment(f.data) for f in fragments]
        r = RandomOracle.derive(hashes)
        n = len(fragments)
        m = fragments[0].threshold_m
        fingerprints = [fingerprint(r, fragments[j].data) for j in range(0, m)]

        return FingerprintedCrossChecksum(hashes, fingerprints, r, n, m)
        

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_json(self) -> str:
        hashes_json = [h.hex() for h in self.hashes]
        fingerprints_json = [fp.value for fp in self.fingerprints]
        r_json = self.r.value

        json_dict = {
            "hashes": hashes_json,
            "fingerprints": fingerprints_json,
            "r": r_json,
            "n": self.n,
            "m": self.m
        }

        return json.dumps(json_dict)

    @classmethod
    def from_json(cls, json_str: str) -> FingerprintedCrossChecksum:
        json_dict = json.loads(json_str)
        hashes = [bytes.fromhex(h) for h in json_dict["hashes"]]
        fingerprints = [GF256(fp) for fp in json_dict["fingerprints"]]
        r = GF256(json_dict["r"])
        n = json_dict["n"]
        m = json_dict["m"]

        return cls(hashes, fingerprints, r, n, m)

    def digest(self) -> str:
        return RandomOracle.hash_fragment(self.to_json().encode()).hex()
