from __future__ import annotations

import argparse
import base64
import csv
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.erasure.encoder import encode
from src.network.protocol import (
    GetFragmentResponse,
    StoreFragmentRequest,
    StoreFragmentResponse,
)
from src.verification.cross_checksum import FingerprintedCrossChecksum
from src.verification.verifier import Verifier


DEFAULT_SIZES = [64, 256, 1024, 4096, 16384, 65536, 262144, 1048576]


@dataclass(frozen=True)
class Measurement:
    label: str
    object_size_bytes: int
    client_to_servers_bytes: int
    servers_to_client_bytes: int
    total_bytes: int
    overhead_vs_object: float
    note: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Measure veri-store application-layer bandwidth overhead and compare "
            "it against simple replication baselines."
        )
    )
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=DEFAULT_SIZES,
        help="Object sizes in bytes to benchmark.",
    )
    parser.add_argument("--n", type=int, default=5, help="Total coded fragments.")
    parser.add_argument("--m", type=int, default=3, help="Reconstruction threshold.")
    parser.add_argument(
        "--replicas",
        type=int,
        nargs="+",
        default=[3, 5],
        help="Replication factors to compare against.",
    )
    parser.add_argument(
        "--replication-get-replicas",
        type=int,
        default=1,
        help="Healthy-case replicas contacted during replication GET.",
    )
    parser.add_argument(
        "--block-id",
        type=str,
        default="bandwidth-benchmark",
        help="Block identifier used when constructing wire payloads.",
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


def json_request_size(method: str, url: str, payload: dict) -> int:
    request = httpx.Request(method, url, json=payload)
    return len(request.content)


def json_response_size(payload: dict) -> int:
    return len(JSONResponse(content=payload).body)


def measure_veri_store(
    size_bytes: int,
    n: int,
    m: int,
    block_id: str,
) -> list[Measurement]:
    data = make_payload(size_bytes)
    fragments = encode(data, n=n, m=m, block_id=block_id)
    fpcc = FingerprintedCrossChecksum.generate(fragments)
    fpcc_json = fpcc.to_json()

    put_request_total = 0
    put_response_total = 0
    get_response_sizes: list[int] = []

    for fragment in fragments:
        request_model = StoreFragmentRequest(
            fragment_data=base64.b64encode(fragment.data).decode(),
            total_n=fragment.total_n,
            threshold_m=fragment.threshold_m,
            original_length=fragment.original_length,
            fpcc_json=fpcc_json,
        )
        put_request_total += json_request_size(
            "PUT",
            f"http://benchmark/fragments/{fragment.block_id}/{fragment.index}",
            request_model.model_dump(),
        )

        report = Verifier.check(fragment.index, fragment.data, fpcc)
        response_model = StoreFragmentResponse(
            block_id=fragment.block_id,
            index=fragment.index,
            verification_status="valid",
            message=report.detail,
        )
        put_response_total += json_response_size(response_model.model_dump())

        get_response_model = GetFragmentResponse(
            block_id=fragment.block_id,
            index=fragment.index,
            fragment_data=base64.b64encode(fragment.data).decode(),
            total_n=fragment.total_n,
            threshold_m=fragment.threshold_m,
            original_length=fragment.original_length,
            fpcc_json=fpcc_json,
            verification_status="valid",
        )
        get_response_sizes.append(json_response_size(get_response_model.model_dump()))

    put_total = put_request_total + put_response_total
    get_current_responses = sum(get_response_sizes)
    get_minimum_responses = sum(get_response_sizes[:m])

    return [
        Measurement(
            label="veri-store-put",
            object_size_bytes=size_bytes,
            client_to_servers_bytes=put_request_total,
            servers_to_client_bytes=put_response_total,
            total_bytes=put_total,
            overhead_vs_object=put_total / size_bytes,
            note=f"Actual PUT fan-out to n={n} servers.",
        ),
        Measurement(
            label="veri-store-get-current",
            object_size_bytes=size_bytes,
            client_to_servers_bytes=0,
            servers_to_client_bytes=get_current_responses,
            total_bytes=get_current_responses,
            overhead_vs_object=get_current_responses / size_bytes,
            note=f"Current client requests and parses all {n} fragment responses.",
        ),
        Measurement(
            label="veri-store-get-minimum",
            object_size_bytes=size_bytes,
            client_to_servers_bytes=0,
            servers_to_client_bytes=get_minimum_responses,
            total_bytes=get_minimum_responses,
            overhead_vs_object=get_minimum_responses / size_bytes,
            note=f"Lower bound if GET stopped after the first m={m} valid fragments.",
        ),
    ]


def replication_put_request_payload(data: bytes) -> dict[str, str | int]:
    return {
        "data": base64.b64encode(data).decode(),
        "original_length": len(data),
    }


def replication_put_response_payload(block_id: str) -> dict[str, str]:
    return {
        "block_id": block_id,
        "message": "stored",
    }


def replication_get_response_payload(block_id: str, data: bytes) -> dict[str, str | int]:
    return {
        "block_id": block_id,
        "data": base64.b64encode(data).decode(),
        "original_length": len(data),
        "status": "ok",
    }


def measure_replication(
    size_bytes: int,
    replicas: int,
    healthy_get_replicas: int,
    block_id: str,
) -> list[Measurement]:
    if replicas <= 0:
        raise ValueError("replicas must be > 0")
    if healthy_get_replicas <= 0:
        raise ValueError("healthy_get_replicas must be > 0")

    data = make_payload(size_bytes)
    put_request_size = json_request_size(
        "PUT",
        f"http://benchmark/objects/{block_id}",
        replication_put_request_payload(data),
    )
    put_response_size = json_response_size(replication_put_response_payload(block_id))
    get_response_size = json_response_size(replication_get_response_payload(block_id, data))

    put_total = replicas * (put_request_size + put_response_size)
    get_total = healthy_get_replicas * get_response_size

    return [
        Measurement(
            label=f"replication-{replicas}x-put",
            object_size_bytes=size_bytes,
            client_to_servers_bytes=replicas * put_request_size,
            servers_to_client_bytes=replicas * put_response_size,
            total_bytes=put_total,
            overhead_vs_object=put_total / size_bytes,
            note=(
                f"Baseline assumes full-object PUT to {replicas} replicas using "
                "the same JSON+base64 transport style."
            ),
        ),
        Measurement(
            label=f"replication-{replicas}x-get",
            object_size_bytes=size_bytes,
            client_to_servers_bytes=0,
            servers_to_client_bytes=get_total,
            total_bytes=get_total,
            overhead_vs_object=get_total / size_bytes,
            note=(
                f"Healthy-case GET contacting {healthy_get_replicas} replica(s); "
                f"replication factor is {replicas}."
            ),
        ),
    ]


def format_int(value: int) -> str:
    return f"{value:,}"


def format_ratio(value: float) -> str:
    return f"{value:.2f}x"


def format_relative(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{numerator / denominator:.2f}x"


def print_put_table(rows_by_label: dict[str, dict[int, Measurement]], replicas: list[int]) -> None:
    print("PUT totals (request + response bodies, bytes)")
    header = ["size"]
    for label in ["veri-store-put", *[f"replication-{r}x-put" for r in replicas]]:
        header.append(label)
    for r in replicas:
        header.append(f"veri/rep-{r}x")
    print("  ".join(f"{col:>18}" for col in header))

    for size in sorted(rows_by_label["veri-store-put"]):
        veri = rows_by_label["veri-store-put"][size]
        cells = [f"{format_int(size):>18}", f"{format_int(veri.total_bytes):>18}"]
        for r in replicas:
            cells.append(f"{format_int(rows_by_label[f'replication-{r}x-put'][size].total_bytes):>18}")
        for r in replicas:
            rep = rows_by_label[f"replication-{r}x-put"][size]
            cells.append(f"{format_relative(veri.total_bytes, rep.total_bytes):>18}")
        print("  ".join(cells))


def print_get_table(rows_by_label: dict[str, dict[int, Measurement]], replicas: list[int]) -> None:
    print("\nGET totals (response bodies only, bytes)")
    header = [
        "size",
        "veri-get-current",
        "veri-get-min",
    ]
    header.extend(f"replication-{r}x-get" for r in replicas)
    header.extend(f"current/rep-{r}x" for r in replicas)
    print("  ".join(f"{col:>18}" for col in header))

    for size in sorted(rows_by_label["veri-store-get-current"]):
        current = rows_by_label["veri-store-get-current"][size]
        minimum = rows_by_label["veri-store-get-minimum"][size]
        cells = [
            f"{format_int(size):>18}",
            f"{format_int(current.total_bytes):>18}",
            f"{format_int(minimum.total_bytes):>18}",
        ]
        for r in replicas:
            cells.append(f"{format_int(rows_by_label[f'replication-{r}x-get'][size].total_bytes):>18}")
        for r in replicas:
            rep = rows_by_label[f"replication-{r}x-get"][size]
            cells.append(f"{format_relative(current.total_bytes, rep.total_bytes):>18}")
        print("  ".join(cells))


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
        handle.write("# Bandwidth Benchmark Results\n\n")
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
        all_rows.extend(measure_veri_store(size, args.n, args.m, args.block_id))
        for replicas in args.replicas:
            all_rows.extend(
                measure_replication(
                    size,
                    replicas,
                    args.replication_get_replicas,
                    args.block_id,
                )
            )

    rows_by_label: dict[str, dict[int, Measurement]] = {}
    for row in all_rows:
        rows_by_label.setdefault(row.label, {})[row.object_size_bytes] = row

    print("Bandwidth model assumptions")
    print(f"- veri-store PUT uses the real StoreFragmentRequest/StoreFragmentResponse wire shapes with n={args.n}, m={args.m}.")
    print(f"- veri-store GET current models the existing client behavior: request all {args.n} fragments and count every successful response.")
    print(f"- veri-store GET minimum is a lower bound that stops after {args.m} valid fragment responses.")
    print(
        "- replication baseline assumes the same JSON+base64 transport style, "
        "but sends the full object to each replica."
    )
    print(
        f"- replication GET assumes a healthy-case read from {args.replication_get_replicas} "
        "replica(s); request bodies are empty, so the table counts response bodies."
    )
    print()

    print_put_table(rows_by_label, args.replicas)
    print_get_table(rows_by_label, args.replicas)

    print("\nPer-object overhead relative to original object size")
    for label in ["veri-store-put", "veri-store-get-current", "veri-store-get-minimum"]:
        ratios = ", ".join(
            f"{format_int(size)}B={format_ratio(rows_by_label[label][size].overhead_vs_object)}"
            for size in sorted(rows_by_label[label])
        )
        print(f"- {label}: {ratios}")

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
