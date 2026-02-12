"""
protocol.py -- Pydantic models for the veri-store HTTP API.

These models define the JSON wire format exchanged between client and server.
Pydantic handles validation and serialization automatically.

Endpoints:
    PUT  /fragments/{block_id}/{index}
         Request:  StoreFragmentRequest
         Response: StoreFragmentResponse

    GET  /fragments/{block_id}/{index}
         Response: GetFragmentResponse

    DELETE /fragments/{block_id}/{index}
         Response: DeleteFragmentResponse

    GET  /health
         Response: HealthResponse

All fragment data is transmitted as base64-encoded strings because JSON cannot
natively represent arbitrary bytes.
"""

from __future__ import annotations
from pydantic import BaseModel, Field


class StoreFragmentRequest(BaseModel):
    """Body for PUT /fragments/{block_id}/{index}.

    Attributes:
        fragment_data (str):     Base64-encoded fragment bytes.
        total_n (int):           Total number of fragments in the coding scheme.
        threshold_m (int):       Reconstruction threshold.
        original_length (int):   Byte length of the original unpadded data.
        fpcc_json (str):         JSON string of the FingerprintedCrossChecksum.
    """

    fragment_data: str = Field(..., description="Base64-encoded fragment bytes")
    total_n: int = Field(..., ge=1, description="Total number of fragments (n)")
    threshold_m: int = Field(..., ge=1, description="Reconstruction threshold (m)")
    original_length: int = Field(..., ge=0, description="Original data byte length")
    fpcc_json: str = Field(..., description="Serialized FingerprintedCrossChecksum")


class StoreFragmentResponse(BaseModel):
    """Response body for a successful PUT /fragments/{block_id}/{index}.

    Attributes:
        block_id (str):              Echo of the stored block identifier.
        index (int):                 Echo of the stored fragment index.
        verification_status (str):   Result of the consistency check on receipt.
        message (str):               Human-readable status message.
    """

    block_id: str
    index: int
    verification_status: str
    message: str


class GetFragmentResponse(BaseModel):
    """Response body for GET /fragments/{block_id}/{index}.

    Attributes:
        block_id (str):          Identifier for the data block.
        index (int):             Fragment index.
        fragment_data (str):     Base64-encoded fragment bytes.
        total_n (int):           Total coded fragments.
        threshold_m (int):       Reconstruction threshold.
        original_length (int):   Original data byte length.
        fpcc_json (str):         Serialized FingerprintedCrossChecksum.
        verification_status (str): Most recent verification result for this fragment.
    """

    block_id: str
    index: int
    fragment_data: str
    total_n: int
    threshold_m: int
    original_length: int
    fpcc_json: str
    verification_status: str


class DeleteFragmentResponse(BaseModel):
    """Response body for DELETE /fragments/{block_id}/{index}.

    Attributes:
        block_id (str): Identifier for the deleted block.
        index (int):    Fragment index deleted.
        message (str):  Human-readable confirmation.
    """

    block_id: str
    index: int
    message: str


class HealthResponse(BaseModel):
    """Response body for GET /health.

    Attributes:
        server_id (int):       This server's index (1–n).
        status (str):          "ok" if healthy.
        fragment_count (int):  Number of fragments currently stored.
    """

    server_id: int
    status: str
    fragment_count: int


class ErrorResponse(BaseModel):
    """Generic error envelope returned on 4xx/5xx responses.

    Attributes:
        error (str):   Short machine-readable error code.
        detail (str):  Human-readable explanation.
    """

    error: str
    detail: str
