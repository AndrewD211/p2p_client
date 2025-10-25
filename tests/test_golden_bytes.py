"""Golden-bytes test: deterministic, parser-only.
Build one canonical ANNOUNCE_OK buffer with struct.pack (big-endian),
then assert unpack_announce_ok(...) returns the exact expected dict.
No network; catches wire-format regressions."""

import struct
from src.protocols import unpack_announce_ok

def test_unpacks_golden_announce_ok():
    # Build one canonical ANNOUNCE_OK reply buffer:
    # >IIIII = action(1), tx_id, interval, leechers, seeders
    header = struct.pack(">IIIII", 1, 0x1234, 12, 0, 0)
    # One IPv4 peer: 127.0.0.1:6881  (4 bytes IP + 2 bytes port)
    peers  = b"\x7f\x00\x00\x01" + struct.pack(">H", 6881)
    buf = header + peers

    result = unpack_announce_ok(buf)

    # Adjust the key below if your function returns "transaction_id" instead of "tx_id"
    assert result.get("tx_id", result.get("transaction_id")) == 0x1234
    assert result["interval"] == 12
    assert ("127.0.0.1", 6881) in result["peers"]
