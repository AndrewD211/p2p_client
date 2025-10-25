import socket
from src.client_tracker import announce
from src.protocols import EVENT_STARTED

def test_timeout_retry():
    # Bind a socket that drops the packet to force timeout
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(("127.0.0.1", 0))
    host, port = s.getsockname()
    def drop(): s.recvfrom(4096)  # read and drop
    import threading; threading.Thread(target=drop, daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        try:
            announce(sock, host, port, 0xBEEF, b"x"*20, b"-PY0001-abcdefghij12",
                     0, 123, 0, event=EVENT_STARTED, num_want=50, port=6881, timeout=0.2)
            assert False, "expected timeout"
        except (socket.timeout, OSError):
            pass
