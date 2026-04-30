from __future__ import annotations

import argparse
import math
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.fingerprint.field import GF256
from src.fingerprint.fingerprint import fingerprint
from src.verification.oracle import RandomOracle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Empirically estimate collision probabilities for veri-store primitives."
    )
    parser.add_argument(
        "--fingerprint-trials",
        type=int,
        default=100_000,
        help="Number of distinct fragment-pair trials for fingerprint collisions.",
    )
    parser.add_argument(
        "--oracle-trials",
        type=int,
        default=100_000,
        help="Number of distinct hash-vector pair trials for RandomOracle collisions.",
    )
    parser.add_argument(
        "--sha-samples",
        type=int,
        default=100_000,
        help="Number of random fragments to hash when searching for SHA-256 duplicates.",
    )
    parser.add_argument(
        "--fragment-bytes",
        type=int,
        default=64,
        help="Length of random test fragments in bytes.",
    )
    parser.add_argument(
        "--hash-vector-length",
        type=int,
        default=5,
        help="Number of digests in each RandomOracle input vector.",
    )
    return parser.parse_args()


def random_nonzero_gf256() -> GF256:
    return GF256(secrets.randbelow(255) + 1)


def distinct_fragment_pair(length: int) -> tuple[bytes, bytes]:
    left = secrets.token_bytes(length)
    right = secrets.token_bytes(length)

    while right == left:
        right = secrets.token_bytes(length)

    return left, right


def random_hash_vector(vector_length: int, fragment_bytes: int) -> list[bytes]:
    return [
        RandomOracle.hash_fragment(secrets.token_bytes(fragment_bytes))
        for _ in range(vector_length)
    ]


def distinct_hash_vector_pair(vector_length: int, fragment_bytes: int) -> tuple[list[bytes], list[bytes]]:
    left = random_hash_vector(vector_length, fragment_bytes)
    right = random_hash_vector(vector_length, fragment_bytes)

    if left == right:
        mutated = bytearray(right[0])
        mutated[0] ^= 0x01
        right[0] = bytes(mutated)

    return left, right


def standard_error(p: float, n: int) -> float:
    if n <= 0:
        return 0.0
    return math.sqrt(p * (1.0 - p) / n)


def fingerprint_collision_experiment(trials: int, fragment_bytes: int) -> dict[str, float | int]:
    collisions = 0

    for _ in range(trials):
        r = random_nonzero_gf256()
        left, right = distinct_fragment_pair(fragment_bytes)

        if fingerprint(r, left) == fingerprint(r, right):
            collisions += 1

    empirical = collisions / trials
    expected = 1.0 / 256.0
    return {
        "trials": trials,
        "collisions": collisions,
        "empirical": empirical,
        "expected": expected,
        "stderr": standard_error(empirical, trials),
    }


def oracle_collision_experiment(
    trials: int, vector_length: int, fragment_bytes: int
) -> dict[str, float | int]:
    collisions = 0

    for _ in range(trials):
        left, right = distinct_hash_vector_pair(vector_length, fragment_bytes)

        if RandomOracle.derive(left) == RandomOracle.derive(right):
            collisions += 1

    empirical = collisions / trials
    expected = 1.0 / 255.0
    return {
        "trials": trials,
        "collisions": collisions,
        "empirical": empirical,
        "expected": expected,
        "stderr": standard_error(empirical, trials),
    }


def sha_duplicate_experiment(samples: int, fragment_bytes: int) -> dict[str, int]:
    seen: set[bytes] = set()
    duplicates = 0

    for _ in range(samples):
        digest = RandomOracle.hash_fragment(secrets.token_bytes(fragment_bytes))
        if digest in seen:
            duplicates += 1
        else:
            seen.add(digest)

    return {
        "samples": samples,
        "duplicates": duplicates,
        "unique": len(seen),
    }


def print_rate_result(title: str, result: dict[str, float | int]) -> None:
    empirical = float(result["empirical"])
    expected = float(result["expected"])
    stderr = float(result["stderr"])

    print(title)
    print(f"  trials:       {result['trials']}")
    print(f"  collisions:   {result['collisions']}")
    print(f"  empirical:    {empirical:.8f}")
    print(f"  expected:     {expected:.8f}")
    print(f"  abs_error:    {abs(empirical - expected):.8f}")
    print(f"  std_error:    {stderr:.8f}")
    print()


def print_sha_result(title: str, result: dict[str, int]) -> None:
    print(title)
    print(f"  samples:      {result['samples']}")
    print(f"  duplicates:   {result['duplicates']}")
    print(f"  unique:       {result['unique']}")
    print()


def main() -> int:
    args = parse_args()

    if args.fingerprint_trials <= 0:
        raise ValueError("--fingerprint-trials must be > 0")
    if args.oracle_trials <= 0:
        raise ValueError("--oracle-trials must be > 0")
    if args.sha_samples <= 0:
        raise ValueError("--sha-samples must be > 0")
    if args.fragment_bytes <= 0:
        raise ValueError("--fragment-bytes must be > 0")
    if args.hash_vector_length <= 0:
        raise ValueError("--hash-vector-length must be > 0")

    print("=== Collision Probability Experiment ===")
    print(f"fragment_bytes={args.fragment_bytes}")
    print(f"hash_vector_length={args.hash_vector_length}")
    print()

    fp_result = fingerprint_collision_experiment(
        trials=args.fingerprint_trials,
        fragment_bytes=args.fragment_bytes,
    )
    print_rate_result("Fingerprint collisions", fp_result)

    oracle_result = oracle_collision_experiment(
        trials=args.oracle_trials,
        vector_length=args.hash_vector_length,
        fragment_bytes=args.fragment_bytes,
    )
    print_rate_result("RandomOracle output collisions", oracle_result)

    sha_result = sha_duplicate_experiment(
        samples=args.sha_samples,
        fragment_bytes=args.fragment_bytes,
    )
    print_sha_result("SHA-256 duplicate search", sha_result)

    print("Notes:")
    print("  - Fingerprint collisions are expected to occur with probability about 1/256.")
    print("  - RandomOracle.derive() outputs one of 255 nonzero GF(2^8) values, so")
    print("    pairwise output collisions should be about 1/255.")
    print("  - SHA-256 duplicates are expected to be 0 at these sample sizes; this is")
    print("    only a sanity check, not evidence of practical collision resistance.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
