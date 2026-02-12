"""
byzantine_detection_demo.py -- Demonstrate Byzantine fault detection.

Shows that the homomorphic fingerprint verification catches a server that
returns a corrupt (Byzantine-modified) fragment.

Scenario:
    - Store an object across 5 servers.
    - One server (server 2) is "Byzantine": it modifies the fragment it returns.
    - The client verifies all received fragments against the fpcc.
    - The corrupt fragment from server 2 is detected and discarded.
    - The client recovers the original data using the 4 honest servers.

Prerequisites:
    Start all 5 servers (see basic_store_retrieve.py header).
    Server 2 should be running in "Byzantine mode" (inject corruption):
        python -m veri_store.server --id 2 --port 5002 --byzantine

Usage:
    python examples/byzantine_detection_demo.py

Expected output:
    [PUT]   Stored 'byzantine_test' on all 5 servers.
    [GET]   Requesting fragments from all 5 servers...
    [WARN]  Fragment 1 (server 2) failed verification: HASH_MISMATCH
    [GET]   Discarded 1 corrupt fragment(s); reconstructing from 4 honest servers.
    [GET]   Successfully reconstructed data.
    [OK]    Byzantine fault detected and tolerated.
"""

# TODO: Import VeriStoreClient, ServerAddress from src.network.client
# TODO: Import Verifier, VerificationResult from src.verification.verifier

# TODO: def main() -> None:
#     """Run the Byzantine detection demonstration."""
#     servers = [ServerAddress(i+1, port=5001+i) for i in range(5)]
#     client = VeriStoreClient(servers=servers, m=3)
#
#     data = b"Integrity test: this must not be altered."
#     key = "byzantine_test"
#
#     print("[PUT]   Storing data on all 5 servers...")
#     client.put(key, data)
#     print("[PUT]   Stored 'byzantine_test' on all 5 servers.")
#
#     print("[GET]   Requesting fragments from all 5 servers...")
#     # The client automatically verifies each fragment; corrupt ones are discarded.
#     retrieved = client.get(key)
#
#     assert retrieved == data
#     print("[OK]    Byzantine fault detected and tolerated.")

# TODO: if __name__ == "__main__": main()
