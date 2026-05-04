from __future__ import annotations

import argparse
import csv
import gc
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.erasure.encoder import Fragment, encode
from src.verification.cross_checksum import FingerprintedCrossChecksum
from src.verification.verifier import VerificationResult, Verifier


DEFAULT_SIZES = [256, 1024, 4096, 16384, 65536, 262144]


@dataclass(frozen=True)
class Measurement:
    label: str
    verification_path: str
    object_size_bytes: int
    fragment_size_bytes: int
    fragment_index: int
    repetitions: int
    warmup: int
    avg_us: float
    p50_us: float
    p95_us: float
    min_us: float
    max_us: float
    note: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Measure per-fragment verification time for veri-store's "
            "Verifier.check(...) microbenchmark."
        )
    )
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=DEFAULT_SIZES,
        help="Original object sizes in bytes to benchmark.",
    )
    parser.add_argument("--n", type=int, default=5, help="Total coded fragments.")
    parser.add_argument("--m", type=int, default=3, help="Reconstruction threshold.")
    parser.add_argument(
        "--repetitions",
        type=int,
        default=5000,
        help="Timed verification calls per fragment type and object size.",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=500,
        help="Warmup verification calls before timing begins.",
    )
    parser.add_argument(
        "--block-id",
        type=str,
        default="verification-benchmark",
        help="Block identifier used when constructing test fragments.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Optional CSV path for normalized benchmark rows.",
    )
    parser.add_argument(
        "--md",
        type=Path,
        default=None,
        help=(
            "Optional Markdown report path for a human-readable table export. "
            "If omitted but --csv is set, a sibling .md file is written automatically."
        ),
    )
    return parser.parse_args()


def make_payload(size_bytes: int) -> bytes:
    if size_bytes <= 0:
        raise ValueError("size_bytes must be > 0")
    return bytes(i % 251 for i in range(size_bytes))


def percentile(samples_ns: list[int], p: float) -> float:
    if not samples_ns:
        return 0.0
    ordered = sorted(samples_ns)
    if len(ordered) == 1:
        return ordered[0] / 1000.0

    rank = (p / 100.0) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    value_ns = ordered[low] + (ordered[high] - ordered[low]) * weight
    return value_ns / 1000.0


def benchmark_fragment(
    label: str,
    verification_path: str,
    object_size_bytes: int,
    fragment: Fragment,
    fpcc: FingerprintedCrossChecksum,
    repetitions: int,
    warmup: int,
    note: str,
) -> Measurement:
    if repetitions <= 0:
        raise ValueError("repetitions must be > 0")
    if warmup < 0:
        raise ValueError("warmup must be >= 0")

    for _ in range(warmup):
        report = Verifier.check(fragment.index, fragment.data, fpcc)
        if report.result != VerificationResult.CONSISTENT:
            raise RuntimeError(f"Warmup verification failed for fragment {fragment.index}")

    samples_ns: list[int] = []
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(repetitions):
            start_ns = time.perf_counter_ns()
            report = Verifier.check(fragment.index, fragment.data, fpcc)
            elapsed_ns = time.perf_counter_ns() - start_ns
            if report.result != VerificationResult.CONSISTENT:
                raise RuntimeError(f"Timed verification failed for fragment {fragment.index}")
            samples_ns.append(elapsed_ns)
    finally:
        if gc_was_enabled:
            gc.enable()

    avg_us = statistics.fmean(samples_ns) / 1000.0
    return Measurement(
        label=label,
        verification_path=verification_path,
        object_size_bytes=object_size_bytes,
        fragment_size_bytes=len(fragment.data),
        fragment_index=fragment.index,
        repetitions=repetitions,
        warmup=warmup,
        avg_us=avg_us,
        p50_us=percentile(samples_ns, 50.0),
        p95_us=percentile(samples_ns, 95.0),
        min_us=min(samples_ns) / 1000.0,
        max_us=max(samples_ns) / 1000.0,
        note=note,
    )


def build_measurements(
    size_bytes: int,
    n: int,
    m: int,
    repetitions: int,
    warmup: int,
    block_id: str,
) -> list[Measurement]:
    data = make_payload(size_bytes)
    fragments = encode(data, n=n, m=m, block_id=block_id)
    fpcc = FingerprintedCrossChecksum.generate(fragments)

    rows: list[Measurement] = []

    data_fragment = fragments[0]
    rows.append(
        benchmark_fragment(
            label="verification-data-fragment",
            verification_path="hash+fingerprint",
            object_size_bytes=size_bytes,
            fragment=data_fragment,
            fpcc=fpcc,
            repetitions=repetitions,
            warmup=warmup,
            note=f"Representative data fragment with index {data_fragment.index}; indices < m perform both checks.",
        )
    )

    if n > m:
        parity_fragment = fragments[m]
        rows.append(
            benchmark_fragment(
                label="verification-parity-fragment",
                verification_path="hash-only",
                object_size_bytes=size_bytes,
                fragment=parity_fragment,
                fpcc=fpcc,
                repetitions=repetitions,
                warmup=warmup,
                note=f"Representative parity fragment with index {parity_fragment.index}; indices >= m skip the fingerprint check.",
            )
        )

    return rows


def format_int(value: int) -> str:
    return f"{value:,}"


def format_us(value: float) -> str:
    return f"{value:.2f}"


def print_summary_table(rows: list[Measurement]) -> None:
    print("Per-fragment verification time (microseconds)")
    header = [
        "size",
        "frag_size",
        "path",
        "avg_us",
        "p50_us",
        "p95_us",
        "min_us",
        "max_us",
    ]
    print("  ".join(f"{col:>16}" for col in header))

    for row in rows:
        print(
            "  ".join(
                [
                    f"{format_int(row.object_size_bytes):>16}",
                    f"{format_int(row.fragment_size_bytes):>16}",
                    f"{row.verification_path:>16}",
                    f"{format_us(row.avg_us):>16}",
                    f"{format_us(row.p50_us):>16}",
                    f"{format_us(row.p95_us):>16}",
                    f"{format_us(row.min_us):>16}",
                    f"{format_us(row.max_us):>16}",
                ]
            )
        )


def write_delimited(path: Path, rows: list[Measurement], delimiter: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(asdict(rows[0]).keys()),
            delimiter=delimiter,
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def default_md_path(csv_path: Path) -> Path:
    return csv_path.with_suffix(".md")


def markdown_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def write_markdown(path: Path, rows: list[Measurement]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = list(asdict(rows[0]).keys())

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Verification Time Benchmark Results\n\n")
        handle.write("| " + " | ".join(headers) + " |\n")
        handle.write("| " + " | ".join("---" for _ in headers) + " |\n")

        for row in rows:
            row_dict = asdict(row)
            values = [markdown_escape(str(row_dict[header])) for header in headers]
            handle.write("| " + " | ".join(values) + " |\n")


def main() -> int:
    args = parse_args()
    if args.m > args.n:
        raise ValueError("--m cannot be greater than --n")

    all_rows: list[Measurement] = []
    for size in args.sizes:
        all_rows.extend(
            build_measurements(
                size_bytes=size,
                n=args.n,
                m=args.m,
                repetitions=args.repetitions,
                warmup=args.warmup,
                block_id=args.block_id,
            )
        )

    print("Verification benchmark assumptions")
    print(
        f"- Each row times only Verifier.check(...) for a valid fragment with n={args.n}, m={args.m}."
    )
    print(
        "- Data fragments (index < m) execute both the SHA-256 hash check and the "
        "GF(256) fingerprint check."
    )
    print(
        "- Parity fragments (index >= m) execute the SHA-256 hash check only."
    )
    print(
        f"- Each measurement uses {args.warmup} warmup iterations and {args.repetitions} timed iterations."
    )
    print()

    print_summary_table(all_rows)

    if args.csv is not None:
        write_delimited(args.csv, all_rows, delimiter=",")
        print(f"\nWrote CSV: {args.csv}")

    md_path = args.md
    if md_path is None and args.csv is not None:
        md_path = default_md_path(args.csv)

    if md_path is not None:
        write_markdown(md_path, all_rows)
        print(f"Wrote Markdown: {md_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
