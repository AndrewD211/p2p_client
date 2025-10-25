import os, random, socket, struct, time
from src.protocols import pack_announce, ANNOUNCE, unpack_announce_ok, ERROR,FMT, CONNECT

# Timeout/Backoff Constants for ANNOUNCE attempts
ANNOUNCE_RETRY_TIMEOUT    = 2.0   # initial timeout in second
ANNOUNCE_RETRY_MAX        = 5     # maximum number of tries
ANNOUNCE_RETRY_BACKOFF    = 2.0   # multiply wait by this factor on each retry
ANNOUNCE_RETRY_JITTER_PERCENT     = 0.10  # randomize wait time to avoid "thundering herd" (percentage)

# Client ANNOUNCE
def announce_once(sock, tracker_addr,
    conn_id: int,
    info_hash: bytes, peer_id: bytes,
    downloaded: int, left: int, uploaded: int,
    event: int = 0, num_want: int = -1, port: int = 6881,
    timeout: float = 3.0,
):
    sock.settimeout(timeout)
    tx_id = random.randint(0, 0xFFFFFFFF)

    pkt = pack_announce(
        conn_id=conn_id,
        tx_id=tx_id,
        info_hash=info_hash,
        peer_id=peer_id,
        downloaded=downloaded,
        left=left,
        uploaded=uploaded,
        event=event,
        ip_hint=0,          # let tracker infer
        key=random.getrandbits(32),      # auto-random in pack_announce
        num_want=num_want,
        port=port,
    )

    
       
    sock.sendto(pkt, tracker_addr)
    resp, _ = sock.recvfrom(4096)
    return parse_announce_reply(tx_id, resp)

# ANNOUNCE retry
def announce_retry_delay(attempt, T_base):
    p = ANNOUNCE_RETRY_JITTER_PERCENT
    return T_base * (ANNOUNCE_RETRY_BACKOFF ** attempt) * (1.0 + random.uniform(-p, p))

# Schedule helpers
def _clamp_interval(x, lo=10, hi=3600):
    return max(lo, min(int(x), hi))

def schedule_next(state, jitter_p=0.10):
    iv = _clamp_interval(state["interval"])
    jitter = 1.0 + random.uniform(-jitter_p, jitter_p)
    state["next_reannounce_at"] = time.time() + iv * jitter

def reannounce_due(state, now=None):
    if now is None: now = time.time()
    return now >= state.get("next_reannounce_at", 0)

# Parse Announce Reply
def parse_announce_reply(expected_tx: int, resp: bytes) -> dict:
    if len(resp) < 8:
        raise ValueError("short tracker reply")
    action, rx_tx = struct.unpack_from(">II", resp, 0)
    if rx_tx != expected_tx:
        raise ValueError("transaction_id mismatch")

    if action == ANNOUNCE:
        ok = unpack_announce_ok(resp)
        ok["interval"] = _clamp_interval(ok["interval"])
        schedule_next(ok)  # sets ok["next_reannounce_at"]
        return ok

    if action == ERROR:
        # bytes after header is a UTF-8 error string (by convention)
        msg = resp[8:].decode("utf-8", "replace")
        raise RuntimeError(f"tracker error: {msg}")

    raise ValueError(f"unexpected action {action}")

# ANNOUNCE Wrapper 
def announce(sock, tracker_host, tracker_port, conn_id,
             info_hash, peer_id, downloaded, left, uploaded,
             event=0, num_want=-1, port=6881, timeout=3.0):
    addr = (tracker_host, tracker_port)
    for attempt in range(ANNOUNCE_RETRY_MAX):
        try:
            return announce_once(sock, addr, conn_id,
                                 info_hash, peer_id, downloaded, left, uploaded,
                                 event=event, num_want=num_want, port=port, timeout=timeout)
        except (socket.timeout, OSError, ValueError) as e:
            if attempt == ANNOUNCE_RETRY_MAX - 1:
                raise
            d = announce_retry_delay(attempt, timeout)
            print(f"[announce] retry {attempt+1}/{ANNOUNCE_RETRY_MAX-1} in {d:.2f}s "
                  f"after {type(e).__name__}: {e}")
            time.sleep(d)

# CONNECT

INITIAL_CONN_ID = 0x41727101980  # must match server

_conn_expire_at = 0.0
def connection_id_expired() -> bool:
    return time.time() >= _conn_expire_at

def do_connect(sock, tracker_addr, ttl=60) -> int:
    global _conn_expire_at
    tx = random.randint(1, 2**31 - 1)
    req = struct.pack(">QII", INITIAL_CONN_ID, CONNECT, tx)
    sock.sendto(req, tracker_addr)

    buf, _ = sock.recvfrom(1024)
    action, rx_tx, conn_id = struct.unpack_from(">IIQ", buf, 0)
    if action != CONNECT or rx_tx != tx:
        raise ValueError("bad CONNECT reply")

    _conn_expire_at = time.time() + ttl
    return conn_id

# TEST
if __name__ == "__main__":
    import socket

    DEAD_PORT = 65099  # nothing should be listening here

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", 0))
            print(f"[smoke] local UDP bound at {sock.getsockname()}")

            announce(
                sock,
                "127.0.0.1", DEAD_PORT,          # force timeouts
                conn_id=0x1234,
                info_hash=b"x" * 20,             # 20 bytes
                peer_id=b"-PY0001-abcdefghij12", # 20 bytes
                downloaded=0, left=123, uploaded=0,
                event=0, num_want=-1, port=6881, timeout=0.5
            )
    except Exception as e:
        print("[smoke] final error:", type(e).__name__, e)




