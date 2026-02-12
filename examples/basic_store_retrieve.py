"""
basic_store_retrieve.py -- Minimal end-to-end demo: PUT then GET.

Prerequisites:
    Start all 5 servers before running this script:
        python -m veri_store.server --id 1 --port 5001
        python -m veri_store.server --id 2 --port 5002
        python -m veri_store.server --id 3 --port 5003
        python -m veri_store.server --id 4 --port 5004
        python -m veri_store.server --id 5 --port 5005

Usage:
    python examples/basic_store_retrieve.py

Expected output:
    [PUT]  Dispersing 'hello_world' (11 bytes) to 5 servers...
    [PUT]  Stored block: <block_id>
    [GET]  Retrieving 'hello_world' ...
    [GET]  Reconstructed: b'Hello, world!'
    [OK]   Retrieved data matches original.
"""

# TODO: Import VeriStoreClient and ServerAddress from src.network.client

# TODO: Define DEFAULT_SERVERS = [ServerAddress(i+1, port=5001+i) for i in range(5)]

# TODO: def main() -> None:
#     client = VeriStoreClient(servers=DEFAULT_SERVERS, m=3)
#
#     data = b"Hello, world!"
#     key = "hello_world"
#
#     print(f"[PUT]  Dispersing '{key}' ({len(data)} bytes) to 5 servers...")
#     block_id = client.put(key, data)
#     print(f"[PUT]  Stored block: {block_id}")
#
#     print(f"[GET]  Retrieving '{key}' ...")
#     retrieved = client.get(key)
#     print(f"[GET]  Reconstructed: {retrieved!r}")
#
#     assert retrieved == data, "Retrieved data does not match original!"
#     print("[OK]   Retrieved data matches original.")

# TODO: if __name__ == "__main__": main()
