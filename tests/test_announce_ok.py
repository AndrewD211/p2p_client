import socket
from src.client_tracker import announce
from src.protocols import EVENT_STARTED
from src.tracker_server import main as run_server  # optional if you prefer the real server
# Alternatively, import your one-shot stub from the test itself.

def test_announce_ok_smoke(monkeypatch):
    # Start a minimal one-shot tracker in-thread or use your server bound to :0.
    # Quick version: inline your _start_fake_tracker_once helper from the old file.
    from socket import SOL_SOCKET, SO_REUSEADDR, AF_INET, SOCK_DGRAM
    import struct, threading

    def start_once(interval=12):
        s = socket.socket(AF_INET, SOCK_DGRAM); s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1); s.bind(("127.0.0.1", 0))
        host, port = s.getsockname()
        def serve():
            data, addr = s.recvfrom(4096)
            _conn_id, action, tx = struct.unpack(">QII", data[:16])
            # build minimal announce_ok
            from src.protocols import pack_announce_ok
            s.sendto(pack_announce_ok(tx, interval, [], 0, 0), addr); s.close()
        threading.Thread(target=serve, daemon=True).start()
        return host, port

    host, port = start_once(interval=12)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        state = announce(sock, host, port, conn_id=0xBEEF,
                         info_hash=b"x"*20, peer_id=b"-PY0001-abcdefghij12",
                         downloaded=0, left=123, uploaded=0,
                         event=EVENT_STARTED, num_want=50, port=6881, timeout=0.5)
        assert state["interval"] == 12
        assert state["peers"] == []
