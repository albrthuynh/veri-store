"""
network -- HTTP server and client for the veri-store dispersal/retrieval protocol.

The network layer connects the storage, erasure, and verification modules into
a distributed system.  Five server processes run on ports 5001–5005; the client
talks to all of them via HTTP/REST.

Sub-modules:
    protocol.py -- Pydantic request/response models (the API contract).
    server.py   -- FastAPI application: PUT /fragment, GET /fragment, health check.
    client.py   -- HTTP client: dispersal (PUT all fragments) and retrieval (GET m).

Typical flow:
    Client                             Server_i
      |  PUT /fragments/{block_id}/{i}   |
      |  body: StoreFragmentRequest      |
      |--------------------------------->|
      |  200 StoreFragmentResponse       |
      |<---------------------------------|
      ...
      |  GET /fragments/{block_id}/{i}   |
      |--------------------------------->|
      |  200 GetFragmentResponse         |
      |<---------------------------------|
"""

from .protocol import StoreFragmentRequest, StoreFragmentResponse, GetFragmentResponse
from .client import VeriStoreClient
