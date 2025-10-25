import socket, time, threading
from src.client_tracker import announce
from src.protocols import unpack_announce, pack_announce_ok, EVENT_STARTED, EVENT_NONE, EVENT_COMPLETED

def _tracker_capture_events(interval=2):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(("127.0.0.1", 0))
    host, port = s.getsockname(); events = []
    def serve():
        try:
            while True:
                data, addr = s.recvfrom(4096)
                m = unpack_announce(data); events.append(m["event"])
                s.sendto(pack_announce_ok(m["tx_id"], interval, [], 0, 0), addr)
        except OSError:
            pass
    threading.Thread(target=serve, daemon=True).start()
    return s, (host, port), events

def test_completed_once_flow():
    srv_sock, addr, events = _tracker_capture_events(interval=2)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        conn_id = 0xBEEF; ih = b"x"*20; pid = b"-PY0001-abcdefghij12"; port = 6881
        announce(sock, addr[0], addr[1], conn_id, ih, pid, 0, 123, 0, event=EVENT_STARTED,   num_want=20, port=port, timeout=0.5)
        announce(sock, addr[0], addr[1], conn_id, ih, pid, 123, 0,   0, event=EVENT_COMPLETED,num_want=0,  port=port, timeout=0.5)
        announce(sock, addr[0], addr[1], conn_id, ih, pid, 123, 0,   0, event=EVENT_NONE,     num_want=20, port=port, timeout=0.5)
    time.sleep(0.05); srv_sock.close()
    assert events.count(EVENT_COMPLETED) == 1
    assert events[0]  == EVENT_STARTED
    assert events[-1] == EVENT_NONE
