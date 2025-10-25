import struct, os, socket, random, time

CONNECT, ANNOUNCE, SCRAPE, ERROR = 0, 1, 2, 3

# ANNOUNCE 

FMT = ">QII20s20sQQQIIIiH"   # 13 fields, 98 bytes total

def pack_announce(conn_id, tx_id, info_hash, peer_id,
                  downloaded, left, uploaded,
                  event, ip_hint, key, num_want, port):
    fields = (
        int(conn_id),       # Q
        1,                  # I  (action = ANNOUNCE)
        int(tx_id),         # I
        bytes(info_hash),   # 20s
        bytes(peer_id),     # 20s
        int(downloaded),    # Q
        int(left),          # Q
        int(uploaded),      # Q
        int(event),         # I
        int(ip_hint),       # I
        int(key),           # I
        int(num_want),      # i (signed)
        int(port),          # H
    )

    return struct.pack(FMT, *fields)

def unpack_announce(buf):
    (conn_id, action, tx_id, info_hash, peer_id,
     downloaded, left, uploaded, event, ip_hint, key, num_want, port) = struct.unpack(FMT, buf[:98])
    return {
        "conn_id": conn_id, "action": action, "tx_id": tx_id,
        "info_hash": info_hash, "peer_id": peer_id,
        "downloaded": downloaded, "left": left, "uploaded": uploaded,
        "event": event, "ip_hint": ip_hint, "key": key,
        "num_want": num_want, "port": port
    }

# ANNOUNCE OK

def _pack_compact_ipv4(peers_ipv4):
    # peers_ipv4 = [(ip_str, port), ...]
    out = bytearray()
    for ip, port in peers_ipv4:
        out += socket.inet_aton(ip)           # 4 bytes
        out += struct.pack(">H", int(port))    # 2 bytes
    return bytes(out)

def pack_announce_ok(transaction_id: int, interval: int,
                     peers_ipv4: list[tuple[str,int]],
                     leechers: int = 0, seeders: int = 0):
    header = struct.pack(">IIIII", ANNOUNCE, transaction_id, interval, leechers, seeders)
    return header + _pack_compact_ipv4(peers_ipv4)


HEADER_FMT = ">IIIII"   # action, tx_id, interval, leechers, seeders
PEER_SIZE  = 6          # 4 bytes IPv4 + 2 bytes port

def unpack_announce_ok(buf):
    if len(buf) < 20:
        raise ValueError("short announce_ok header")
    action, tx_id, interval, leechers, seeders = struct.unpack_from(HEADER_FMT, buf, 0)

    # Expect the OK to carry action=ANNOUNCE
    if action != ANNOUNCE:
        raise ValueError(f"bad action {action}")

    peers_raw = buf[20:]
    if len(peers_raw) % PEER_SIZE != 0:
        raise ValueError("bad peers length")

    peers = []
    for i in range(0, len(peers_raw), PEER_SIZE):
        ip4 = peers_raw[i:i+4]
        port = struct.unpack(">H", peers_raw[i+4:i+6])[0]
        peers.append((socket.inet_ntoa(ip4), port))

    return {
        "action": action,
        "tx_id": tx_id,
        "interval": interval,
        "leechers": leechers,
        "seeders": seeders,
        "peers": peers,
    }


# Reannounce
EVENT_NONE      = 0
EVENT_COMPLETED = 1
EVENT_STARTED   = 2
EVENT_STOPPED   = 3


