import os, socket, time, signal, sys
from src.tracker_server import announce, reannounce_due, do_connect, connection_id_expired
from src.protocols import EVENT_STARTED, EVENT_NONE, EVENT_STOPPED, EVENT_COMPLETED


TRACKER_ADDR = (os.getenv("TRACKER_HOST","127.0.0.1"), int(os.getenv("TRACKER_PORT","9000")))
_sent_completed = False

def maybe_send_completed(sock, tracker_addr, conn_id, info_hash, peer_id, downloaded, left, uploaded, listen_port):
    global _sent_completed
    if _sent_completed:
        return
    if left <= 0:
        try:
            announce(sock, tracker_addr[0], tracker_addr[1], conn_id,
                     info_hash, peer_id, downloaded, 0, uploaded,
                     event=EVENT_COMPLETED, num_want=0, port=listen_port, timeout=0.5)
        finally:
            _sent_completed = True

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    print(f"local UDP bound at {sock.getsockname()}")

    conn_id = do_connect(sock, TRACKER_ADDR)
    info_hash  = os.urandom(20)
    peer_id    = b"-PC0001-" + os.urandom(12)   # 20 bytes total if you slice [:20]
    downloaded = 0
    left       = 12345
    uploaded   = 0
    listen_port = 6881

    # one-shot announce 
    state = announce(
        sock, TRACKER_ADDR[0], TRACKER_ADDR[1], conn_id,
        info_hash, peer_id, downloaded, left, uploaded,
        event=EVENT_STARTED, num_want=50, port=listen_port, timeout=1.0
    )
    print("first reply:", {k: state[k] for k in ("interval", "peers", "next_reannounce_at")})

    # Graceful Exit
    def graceful_exit(signum, frame):
        try:
            announce(sock, TRACKER_ADDR[0], TRACKER_ADDR[1], conn_id,
                     info_hash, peer_id, downloaded, left, uploaded,
                     event=EVENT_STOPPED, num_want=0, port=listen_port, timeout=0.5)
        finally:
            sock.close()
            sys.exit(0)

    signal.signal(signal.SIGINT, graceful_exit)   # Ctrl+C
    signal.signal(signal.SIGTERM, graceful_exit)  # kill

    # tiny heartbeat loop
    while True:
        if connection_id_expired():
            conn_id = do_connect(sock, TRACKER_ADDR)

        maybe_send_completed(sock, TRACKER_ADDR, conn_id, info_hash, peer_id, downloaded, left, uploaded, listen_port)


        if reannounce_due(state):
            state = announce(
                sock, TRACKER_ADDR[0], TRACKER_ADDR[1], conn_id,
                info_hash, peer_id, downloaded, left, uploaded,
                event=EVENT_NONE, num_want=50, port=listen_port, timeout=1.0
            )
            print("re-announce:", {k: state[k] for k in ("interval", "peers", "next_reannounce_at")})
        time.sleep(0.05)


if __name__ == "__main__":
    main()
