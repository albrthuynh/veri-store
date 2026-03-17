import base64
import json
import httpx
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.erasure.encoder import encode
from src.verification.cross_checksum import FingerprintedCrossChecksum

block_id = "test-block-1"
data = b"hello veri-store"
frags = encode(data, n=5, m=3)
fpcc = FingerprintedCrossChecksum.generate(frags)

frag0 = frags[0]
body = {
    "fragment_data": base64.b64encode(frag0.data).decode("ascii"),
    "total_n": frag0.total_n,
    "threshold_m": frag0.threshold_m,
    "original_length": len(data),
    "fpcc_json": fpcc.to_json(),
}

url_put = f"http://127.0.0.1:5001/fragments/{block_id}/{frag0.index}"
url_get = f"http://127.0.0.1:5001/fragments/{block_id}/{frag0.index}"

with httpx.Client(timeout=5.0) as client:
    r_put = client.put(url_put, json=body)
    print("PUT status:", r_put.status_code, r_put.text)

    r_get = client.get(url_get)
    print("GET status:", r_get.status_code, r_get.text)