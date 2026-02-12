# veri-store HTTP API

Each server exposes the same REST API on its own port (default: 5001–5005).

Base URL: `http://localhost:{port}`

---

## Endpoints

### `PUT /fragments/{block_id}/{index}`

Store a single encoded fragment on this server.  The server immediately
verifies the fragment against the supplied fpcc and persists it.

**Path parameters**

| Parameter  | Type   | Description                                 |
|------------|--------|---------------------------------------------|
| `block_id` | string | Unique identifier for the data block        |
| `index`    | int    | Fragment index in `[0, n)`                  |

**Request body** (`application/json`)

```json
{
  "fragment_data":   "<base64-encoded fragment bytes>",
  "total_n":         5,
  "threshold_m":     3,
  "original_length": 1024,
  "fpcc_json":       "{\"hashes\": [...], \"fingerprints\": [...], ...}"
}
```

**Response 200** — fragment stored successfully

```json
{
  "block_id":            "abc123",
  "index":               0,
  "verification_status": "consistent",
  "message":             "Fragment stored."
}
```

**Response 422** — fpcc verification failed (fragment is inconsistent)

```json
{
  "error":  "verification_failed",
  "detail": "Fragment index 0 failed hash check."
}
```

**Response 409** — fragment already exists for this (block_id, index)

---

### `GET /fragments/{block_id}/{index}`

Retrieve a stored fragment.

**Path parameters** — same as PUT.

**Response 200**

```json
{
  "block_id":            "abc123",
  "index":               0,
  "fragment_data":       "<base64-encoded bytes>",
  "total_n":             5,
  "threshold_m":         3,
  "original_length":     1024,
  "fpcc_json":           "{...}",
  "verification_status": "consistent"
}
```

**Response 404** — fragment not found

---

### `DELETE /fragments/{block_id}/{index}`

Remove a stored fragment.

**Response 200**

```json
{
  "block_id": "abc123",
  "index":    0,
  "message":  "Fragment deleted."
}
```

**Response 404** — fragment not found

---

### `GET /health`

Liveness and readiness probe.

**Response 200**

```json
{
  "server_id":      1,
  "status":         "ok",
  "fragment_count": 42
}
```

---

## Error Format

All 4xx and 5xx responses use this envelope:

```json
{
  "error":  "<machine-readable code>",
  "detail": "<human-readable explanation>"
}
```

---

## Client API (Python)

```python
from src.network.client import VeriStoreClient, ServerAddress

servers = [ServerAddress(server_id=i+1, port=5001+i) for i in range(5)]
client = VeriStoreClient(servers=servers, m=3)

# Store an object
block_id = client.put("my_key", b"Hello, distributed world!")

# Retrieve it
data = client.get("my_key")

# Delete it
client.delete("my_key")

# Check server health
status = client.health_check()  # {1: True, 2: True, 3: False, ...}
```
