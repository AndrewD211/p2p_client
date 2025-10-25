# P2P Client (in progress)

Small Python P2P **client** with a tiny UDP **tracker server**.  
Implements BitTorrent‑style **connect/announce** (big‑endian) with basic timeouts/retry and a simple re‑announce loop.  
Tests include a one‑shot **golden bytes** parser check, a **smoke** round‑trip, and a **timeout/retry** case.  
*Educational; not production.*

---

## Repo Layout
```
src/
  app_client.py        # runnable client (CLI) that announces to a tracker
  client_tracker.py    # client logic used by app_client (announce, retry, etc.)
  protocols.py         # pack/unpack helpers (big-endian wire format)
  tracker_server.py    # minimal UDP tracker (connect/announce -> reply)
  __init__.py
tests/
  conftest.py           # adds project root to PYTHONPATH for imports
  test_announce_ok.py   # (Smoke Test) happy-path: reply parsed -> interval/peers asserted
  test_completed_once.py# event order: STARTED -> COMPLETED -> NONE (once)
  test_golden_bytes.py  # parser-only: build fixed reply with struct.pack -> expect exact dict; no network
  test_timeout_retry.py # blackhole -> expect timeout/failure after retries
LICENSE
```

---

## Quick Start

### 1) Set up a virtual environment & install deps
**Windows (PowerShell)**
```powershell
py -m venv .venv
.\.venv\Scripts\Activate
py -m pip install --upgrade pip
py -m pip install -r requirements.txt   # or: py -m pip install pytest flake8
```

**macOS/Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt   # or: python -m pip install pytest flake8
```

### 2) Run a local demo (two terminals)
Terminal A — start the tracker:
```bash
python -m src.tracker_server      # binds 127.0.0.1:9000 by default
```
Terminal B — run the client:
```bash
python -m src.app_client --announce 127.0.0.1:9000
```

---

## Tests

Run the whole suite:
```bash
pytest -q
```

Run a specific test:
```bash
pytest -q tests/test_announce_ok.py
pytest -q tests/test_timeout_retry.py
pytest -q tests/test_completed_once.py
pytest -q tests/test_golden_bytes.py
```

### What the tests cover
- **Golden bytes (parser‑only)** — builds one canonical ANNOUNCE_OK reply with `struct.pack` and asserts parsing (deterministic; no network).
- **Smoke** — starts a tiny one‑shot responder and asserts parsed **interval** and **peers**.
- **Timeout/Retry** — blackhole socket eats a packet; client must **timeout/fail after retries** (short timeouts keep CI fast).
- **Completed‑once** — verifies event progression: **STARTED → COMPLETED → NONE**, with **COMPLETED exactly once**.

---

## Notes
- Imports work because `src/__init__.py` marks a package and `tests/conftest.py` adds the repo root to `PYTHONPATH`.
- Default bind is `127.0.0.1:9000`; if the port is busy, start the server with another port and pass it to `--announce`.
- “Golden bytes” = a fixed, known‑good reply buffer used to validate the parser deterministically (locks format & endianness).

---

## License
MIT — see `LICENSE`.

> Academic integrity: this public repo contains only my own code and self‑contained helpers; no partner/instructor scaffolding.
