from socket import *
import struct, random, time
from src.protocols import unpack_announce, pack_announce_ok

INITIAL_CONN_ID = 0x41727101980
CONNECT, ANNOUNCE = 0, 1

EVENT_NONE, EVENT_COMPLETED, EVENT_STARTED, EVENT_STOPPED = 0,1,2,3
DEFAULT_NUM_WANT = 50
MAX_NUM_WANT = 200

def validate_announce(buf, addr, connections):
    # Length
    if len(buf) < 98: return "short"
    # Action
    m = unpack_announce(buf)
    if m["action"] != 1: return "bad_action"
    # Connection id and expiration
    entry = connections.get(addr)
    if not entry: return "no_connect"
    conn_id, expire_at = entry
    if time.time() >= expire_at: return "conn_expired"
    if m["conn_id"] != conn_id:  return "bad_conn_id"
    # Info Hash
    if len(m["info_hash"]) != 20 or len(m["peer_id"]) != 20: return "bad_ids"

    if m["event"] not in {0,1,2,3}: return "bad_event"
    if m["event"] != EVENT_STOPPED and m["port"] == 0: return "bad_port"
    nw = m["num_want"]
    m["num_want"] = DEFAULT_NUM_WANT if nw == 0xFFFFFFFF else max(0, min(nw, MAX_NUM_WANT))
    m["ip"] = addr[0] if m["ip_hint"] == 0 else m["ip_hint"]
    return m

def main():
    server_socket = socket(AF_INET, SOCK_DGRAM)
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server_socket.bind(("127.0.0.1", 0))  # let OS pick a free port
    host, server_port = server_socket.getsockname()
    print(f"Server Ready on {host}:{server_port}")


    connections = {}  # {(ip,port): connection_id}
    peers = {}        # {info_hash: [(ip,port), ...]}

    while True:
        data, addr = server_socket.recvfrom(2048)
        if len(data) < 16:
            continue

        # ---- 16B header (BIG-ENDIAN!) ----
        conn_id_hdr, action, tx = struct.unpack(">QII", data[:16])

        # Handles CONNECT
        if action == CONNECT and len(data) == 16:
            if conn_id_hdr != INITIAL_CONN_ID:
                continue
            new_id = random.getrandbits(64)
            expire_at = time.time() + 60
            connections[addr] = (new_id, expire_at)
            resp = struct.pack(">IIQ", CONNECT, tx, new_id)
            server_socket.sendto(resp, addr)
            continue

        # Handles ANNOUNCE
        if action == ANNOUNCE and len(data) >= 98:
            m = validate_announce(data, addr, connections)
            if isinstance(m, str):
                continue
          
            # record this peer in the swarm
            ip, port = addr[0], m["port"]
            ih = m["info_hash"]
            lst = peers.setdefault(ih, [])
            if (ip, port) not in lst:
                lst.append((ip, port))

            # choose peers to return (don’t echo the caller)
            candidates = [p for p in lst if p != (ip, port)]
            

            # minimal stats + reannounce interval
            interval  = 3 # Decrease this value when testing reannounce
            leechers  = 0
            seeders   = 0

            # send ANNOUNCE_OK (action=1, tx id = header tx)
            resp = pack_announce_ok(transaction_id=m["tx_id"],
                                    interval=interval,
                                    peers_ipv4=candidates[:50],
                                    leechers=leechers,
                                    seeders=seeders)
            server_socket.sendto(resp, addr)
            continue

           

if __name__ == "__main__":
    main()
