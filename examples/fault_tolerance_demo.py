"""
fault_tolerance_demo.py -- Demonstrate crash fault tolerance.

Shows that the system can reconstruct a stored object even when f=1 servers
are unavailable (crash fault).  With n=5, m=3, f=1:
    - Store an object across all 5 servers.
    - Simulate 2 server crashes (stop responding).
    - Retrieve the object using only the 3 remaining servers.

Prerequisites:
    Start all 5 servers (see basic_store_retrieve.py header).

Usage:
    python examples/fault_tolerance_demo.py

Expected output:
    [PUT]   Stored 'fault_test' on all 5 servers.
    [CRASH] Simulating crash: servers 4 and 5 are now unreachable.
    [GET]   Attempting retrieval with only 3 of 5 servers...
    [GET]   Successfully reconstructed data from 3 fragments.
    [OK]    Fault tolerance confirmed: 2-server crash tolerated.
"""

# TODO: Import VeriStoreClient, ServerAddress from src.network.client
# TODO: Import subprocess / signal for killing server processes (or mock)

# TODO: def simulate_crash(server_ids: list[int]) -> None:
#     """Stop the servers with the given IDs by sending SIGTERM."""
#     # TODO: Use psutil or subprocess to find and kill the server processes.
#     ...

# TODO: def main() -> None:
#     """Run the fault tolerance demonstration."""
#     all_servers = [ServerAddress(i+1, port=5001+i) for i in range(5)]
#     client = VeriStoreClient(servers=all_servers, m=3)
#
#     data = b"This data should survive server crashes."
#     key = "fault_test"
#
#     print("[PUT]   Storing data on all 5 servers...")
#     client.put(key, data)
#     print("[PUT]   Stored 'fault_test' on all 5 servers.")
#
#     print("[CRASH] Simulating crash: servers 4 and 5 are now unreachable.")
#     simulate_crash([4, 5])
#
#     print("[GET]   Attempting retrieval with only 3 of 5 servers...")
#     retrieved = client.get(key)
#     assert retrieved == data
#     print("[GET]   Successfully reconstructed data from 3 fragments.")
#     print("[OK]    Fault tolerance confirmed: 2-server crash tolerated.")

# TODO: if __name__ == "__main__": main()
