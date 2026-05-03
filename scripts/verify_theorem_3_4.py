from __future__ import annotations

import argparse
import itertools
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.erasure.decoder import decode
from src.erasure.encoder import Fragment, encode
from src.verification.cross_checksum import FingerprintedCrossChecksum
from src.verification.verifier import VerificationResult, Verifier


@dataclass(frozen=True)
class Candidate:
    index: int
    data: bytes
    source: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Empirically search for a Theorem 3.4 counterexample in veri-store."
    )
    parser.add_argument("--trials", type=int, default=100, help="Number of independent blocks to test.")
    parser.add_argument("--payload-bytes", type=int, default=128, help="Original block size in bytes.")
    parser.add_argument("--n", type=int, default=5, help="Total fragments.")
    parser.add_argument("--m", type=int, default=3, help="Reconstruction threshold.")
    parser.add_argument(
        "--random-forgeries-per-index",
        type=int,
        default=200,
        help="Random forged fragment attempts per index per trial.",
    )
    parser.add_argument(
        "--max-decoding-combinations",
        type=int,
        default=5000,
        help="Safety cap on decoded verified candidate sets per trial.",
    )
    return parser.parse_args()


def make_fragment_like(honest: Fragment, data: bytes) -> Fragment:
    return Fragment(
        index=honest.index,
        data=data,
        block_id=honest.block_id,
        total_n=honest.total_n,
        threshold_m=honest.threshold_m,
        original_length=honest.original_length,
    )


def candidate_generators(
    honest_fragments: list[Fragment],
    other_fragments: list[Fragment],
    index: int,
    random_forgeries_per_index: int,
) -> list[Candidate]:
    honest = honest_fragments[index]
    chunk_len = len(honest.data)

    candidates: list[Candidate] = [
        Candidate(index=index, data=honest.data, source="honest"),
        Candidate(index=index, data=bytes(chunk_len), source="all-zero"),
        Candidate(index=index, data=b"\xFF" * chunk_len, source="all-ff"),
        Candidate(index=index, data=other_fragments[index].data, source="foreign-same-index"),
    ]

    if index + 1 < len(honest_fragments):
        candidates.append(
            Candidate(index=index, data=honest_fragments[index + 1].data, source="swap-next-index")
        )
    if index > 0:
        candidates.append(
            Candidate(index=index, data=honest_fragments[index - 1].data, source="swap-prev-index")
        )

    # A few structured single-byte corruptions.
    for pos in {0, chunk_len // 2, chunk_len - 1}:
        mutated = bytearray(honest.data)
        mutated[pos] ^= 0x01
        candidates.append(Candidate(index=index, data=bytes(mutated), source=f"bitflip-{pos}-01"))

        mutated = bytearray(honest.data)
        mutated[pos] ^= 0xFF
        candidates.append(Candidate(index=index, data=bytes(mutated), source=f"bitflip-{pos}-ff"))

    # Truncation/extension attacks.
    if chunk_len > 1:
        candidates.append(Candidate(index=index, data=honest.data[:-1], source="truncated"))
    candidates.append(Candidate(index=index, data=honest.data + b"\x00", source="extended"))

    # Random forged fragments.
    for j in range(random_forgeries_per_index):
        candidates.append(
            Candidate(index=index, data=secrets.token_bytes(chunk_len), source=f"random-{j}")
        )

    # Deduplicate by bytes while preserving first source label.
    dedup: dict[bytes, Candidate] = {}
    for candidate in candidates:
        dedup.setdefault(candidate.data, candidate)
    return list(dedup.values())


def verified_candidates_for_trial(
    fragments: list[Fragment],
    fpcc: FingerprintedCrossChecksum,
    random_forgeries_per_index: int,
) -> dict[int, list[Candidate]]:
    other_payload = secrets.token_bytes(fragments[0].original_length)
    other_fragments = encode(
        other_payload,
        n=fragments[0].total_n,
        m=fragments[0].threshold_m,
        block_id="other-block",
    )

    verified: dict[int, list[Candidate]] = {}
    for index, honest in enumerate(fragments):
        verified[index] = []
        for candidate in candidate_generators(
            fragments,
            other_fragments,
            index,
            random_forgeries_per_index,
        ):
            report = Verifier.check(index, candidate.data, fpcc)
            if report.result == VerificationResult.CONSISTENT:
                verified[index].append(candidate)

        # Make sure the honest fragment is always present.
        if not any(candidate.data == honest.data for candidate in verified[index]):
            raise RuntimeError(f"Honest fragment at index {index} did not verify.")
    return verified


def decode_verified_sets(
    fragments: list[Fragment],
    verified: dict[int, list[Candidate]],
    max_decoding_combinations: int,
) -> tuple[set[bytes], int, list[str], int]:
    n = fragments[0].total_n
    m = fragments[0].threshold_m
    decoded_outputs: set[bytes] = set()
    examples: list[str] = []
    total_sets = 0

    for index_subset in itertools.combinations(range(n), m):
        pools = [verified[i] for i in index_subset]
        for candidate_tuple in itertools.product(*pools):
            total_sets += 1
            if total_sets > max_decoding_combinations:
                return decoded_outputs, total_sets, examples, 1

            chosen: list[Fragment] = []
            labels: list[str] = []
            for candidate in candidate_tuple:
                honest = fragments[candidate.index]
                chosen.append(make_fragment_like(honest, candidate.data))
                labels.append(f"{candidate.index}:{candidate.source}")

            try:
                decoded = decode(chosen)
            except Exception as exc:
                examples.append(f"decode-error subset={labels} exc={type(exc).__name__}: {exc}")
                continue

            decoded_outputs.add(decoded)
            if len(examples) < 8:
                examples.append(f"decoded subset={labels} len={len(decoded)}")

    return decoded_outputs, total_sets, examples, 0


def main() -> int:
    args = parse_args()

    if args.m <= 0 or args.n <= 0 or args.m > args.n:
        raise ValueError("Require 1 <= m <= n")
    if args.payload_bytes <= 0:
        raise ValueError("--payload-bytes must be > 0")
    if args.trials <= 0:
        raise ValueError("--trials must be > 0")

    forged_consistent = 0
    total_verified_sets = 0
    capped_trials = 0

    for trial in range(args.trials):
        payload = secrets.token_bytes(args.payload_bytes)
        block_id = f"theorem-3-4-trial-{trial:04d}"
        fragments = encode(payload, n=args.n, m=args.m, block_id=block_id)
        fpcc = FingerprintedCrossChecksum.generate(fragments)

        verified = verified_candidates_for_trial(
            fragments,
            fpcc,
            args.random_forgeries_per_index,
        )

        for index, candidates in verified.items():
            forged_consistent += sum(
                1 for candidate in candidates if candidate.data != fragments[index].data
            )

        decoded_outputs, set_count, examples, capped = decode_verified_sets(
            fragments,
            verified,
            args.max_decoding_combinations,
        )
        total_verified_sets += min(set_count, args.max_decoding_combinations)
        capped_trials += capped

        if len(decoded_outputs) == 0:
            print(f"[FAIL] trial={trial} no verified fragment sets could be decoded")
            for line in examples:
                print(f"  {line}")
            return 1

        if len(decoded_outputs) > 1:
            print(f"[COUNTEREXAMPLE] trial={trial} multiple decoded outputs under one FPCC")
            print(f"  distinct_outputs={len(decoded_outputs)}")
            for line in examples:
                print(f"  {line}")
            return 2

        only_output = next(iter(decoded_outputs))
        if only_output != payload:
            print(f"[COUNTEREXAMPLE] trial={trial} unique decoded output != original payload")
            print(f"  original_len={len(payload)} decoded_len={len(only_output)}")
            for line in examples:
                print(f"  {line}")
            return 3

        print(
            f"[PASS] trial={trial} "
            f"forged_consistent_so_far={forged_consistent} "
            f"decoded_sets_this_trial={min(set_count, args.max_decoding_combinations)}"
        )

    print()
    print("=== Theorem 3.4 Empirical Search Summary ===")
    print(f"trials:                    {args.trials}")
    print(f"n, m:                      {args.n}, {args.m}")
    print(f"payload_bytes:             {args.payload_bytes}")
    print(f"random_forgeries_per_idx:  {args.random_forgeries_per_index}")
    print(f"decoded_verified_sets:     {total_verified_sets}")
    print(f"forged_consistent_fragments_found: {forged_consistent}")
    print(f"capped_trials:             {capped_trials}")
    print()
    print("Result:")
    print("  No counterexample was found.")
    print("  Every verified m-fragment set decoded to the same original payload.")
    print("  This is empirical support for Theorem 3.4, not a formal proof.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
