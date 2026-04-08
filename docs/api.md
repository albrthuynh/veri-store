# veri-store HTTP API

Each server exposes the same REST API on its own port (default: 5001–5005).

Base URL: `http://localhost:{port}`

---

## Authentication

`PUT /fragments/{block_id}/{index}`, `GET /fragments/{block_id}/{index}`, and
`DELETE /fragments/{block_id}/{index}` require a bearer token:
```http
Authorization: Bearer <token>
```

Protected fragment endpoints are rate-limited per client. When the limit is
exceeded, the server returns `429 Too Many Requests` and includes a
`Retry-After` header indicating when the client may retry.

`GET /health` is publicly accessible and does not require authentication


## Endpoints

### `PUT /fragments/{block_id}/{index}`

Store a single encoded fragment on this server. The server first validates 
the request structure, then verifies the fragment against the supplied fpcc, 
and finally stores or rejects it accordingly.

**Authentication required**: send a bearer token in the `Authorization` header.

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

**Validation rules**
- `fragment_data` must be a non-empty `base64` string
- `total_n >= 1`
- `threshold_m >= 1`
- `threshold_m <= total_n`
- `original_length >= 0`
- `fpcc_json` must be non-empty and parse as valid `FingerprintedCrossChecksum`
- Unexpected extra fields will be rejected

**Response 200** — fragment stored successfully

```json
{
  "block_id":            "abc123",
  "index":               0,
  "verification_status": "valid",
  "message":             "Fragment index 0 is consistent with the fpcc."
}
```

**Response 422** - verification failure after a well-formed payload is accepted

```json
{
  "detail": "Hash mismatch for fragment index 0."
}
```

**Response 422** - invalid request payload

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body"],
      "msg": "Value error, threshold_m 4 cannot be greater than total_n 3",
      "input": {
        "fragment_data": "Zm9v",
        "total_n": 3,
        "threshold_m": 4,
        "original_length": 3,
        "fpcc_json": "{\"hashes\": [], \"fingerprints\": [], \"r\": 5, \"n\": 3, \"m\": 4}"
      }
    }
  ]
}
```

**Response 409** — fragment already exists for this `(block_id, index)`

```json
{
  "detail": "Fragment (block1, 0) already exists with different data"
}

```

**Response 429** - rate limit exceeded
```json
{
  "detail": "Rate limit exceeded. Please retry later."
}
```

---

### `GET /fragments/{block_id}/{index}`

Retrieve a stored fragment.

**Authentication required**: send a bearer token in the `Authorization` header.

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

**Response 429** - rate limit exceeded
```json
{
  "detail": "Rate limit exceeded. Please retry later."
}
```

---

### `DELETE /fragments/{block_id}/{index}`

Remove a stored fragment.

**Authentication required**: send a bearer token in the `Authorization` header.

**Response 200**

```json
{
  "block_id": "abc123",
  "index":    0,
  "message":  "Fragment deleted."
}
```

**Response 404** — fragment not found

**Response 429** - rate limit exceeded
```json
{
  "detail": "Rate limit exceeded. Please retry later."
}
```

---

### `GET /health`

Liveness and readiness probe.

Authentication not required.

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

Error responses are not wrapped in a single custom envelope.

Most application-level errors raised by the server use FastAPI's standard `HTTPException`
shape:

```json
{
  "detail": "<human-readable explanation>"
}
```

**Examples**
```json
{
  "detail": "Invalid or missing token"
}
```

```json
{
  "detail": "Fragment (block1, 0) already exists with different data"
}
```

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body"],
      "msg": "<validation error message>",
      "input": { "...": "..." }
    }
  ]
}
```

```json
{
  "detail": "Rate limit exceeded. Please retry later."
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
