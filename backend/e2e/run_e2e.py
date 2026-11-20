"""End-to-end smoke test: a real PyJOAL server (uvicorn) against a local fake tracker.

Checks the behaviours that unit tests with mocks cannot prove:
- 'started' reports session counters (uploaded=0 / downloaded=0) even with
  persisted all-time stats, and no 'completed' for a complete torrent (BEP 3)
- /health answers fast (the event loop is never blocked)
- Stop sends 'stopped' with session-relative counters, Start is immediate
- the file watcher still loads new torrents after Stop/Start
- a torrent refused by its tracker ('Unregistered torrent') is stopped,
  flagged and not re-announced
- no ERROR / traceback in the server log

Usage (from anywhere):  python backend/e2e/run_e2e.py
Exit code 0 = passed.
"""
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import bencodepy

E2E_DIR = Path(__file__).resolve().parent
BACKEND = E2E_DIR.parent
REPO = BACKEND.parent
PY = sys.executable
TOKEN = "e2e-token-0123456789"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def make_torrent(path: Path, name: bytes, tracker_port: int) -> str:
    info = {b"name": name, b"length": 700 * 1024 ** 2, b"piece length": 262144, b"pieces": b"\x00" * 20}
    path.write_bytes(bencodepy.encode({b"announce": f"http://127.0.0.1:{tracker_port}/announce".encode(),
                                       b"info": info}))
    return hashlib.sha1(bencodepy.encode(info)).hexdigest()


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="pyjoal-e2e-"))
    for d in ("config", "torrents", "clients"):
        (work / d).mkdir()
    for c in (REPO / "clients").glob("*.client"):
        shutil.copy(c, work / "clients")
    log = work / "announces.log"
    tracker_port, app_port = free_port(), free_port()

    main_hash = make_torrent(work / "torrents" / "main.torrent", b"e2e-main.bin", tracker_port)
    # hash of the torrent the tracker will refuse (added later)
    rejected_info = {b"name": b"e2e-rejected.bin", b"length": 1024 ** 2, b"piece length": 262144,
                     b"pieces": b"\x00" * 20}
    rejected_hash = hashlib.sha1(bencodepy.encode(rejected_info)).hexdigest()

    # Persisted stats from a "previous run": 2 GiB already uploaded
    (work / "config" / "torrent_stats.json").write_text(json.dumps({main_hash: {
        "uploaded": 2 * 1024 ** 3, "seeding_time": 3600, "added_at": "2026-11-01T00:00:00+00:00",
        "torrent_name": "e2e-main.bin"}}))
    clients = sorted(p.name for p in (work / "clients").glob("qbittorrent*.client")) or \
        sorted(p.name for p in (work / "clients").glob("*.client"))
    (work / "config" / "config.json").write_text(json.dumps({"client": clients[0]}))

    env = dict(os.environ, SECRET_TOKEN=TOKEN, UI_PATH_PREFIX="e2e", CONFIG_DIR=str(work / "config"),
               TORRENTS_DIR=str(work / "torrents"), CLIENTS_DIR=str(work / "clients"),
               DOCKER_CONTAINER="1", PYTHONIOENCODING="utf-8")
    tracker = subprocess.Popen([PY, str(E2E_DIR / "fake_tracker.py"), str(tracker_port), str(log), rejected_hash])
    app_log = open(work / "app.log", "w", encoding="utf-8")
    app = subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(app_port)],
                           cwd=BACKEND, env=env, stdout=app_log, stderr=subprocess.STDOUT)

    def call(method, path, timeout=10):
        req = urllib.request.Request(f"http://127.0.0.1:{app_port}{path}", method=method,
                                     headers={"X-API-Token": TOKEN})
        start = time.perf_counter()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"null"), time.perf_counter() - start

    def announces(info_hash=None):
        if not log.exists():
            return []
        rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
        return [r for r in rows if info_hash is None or r["info_hash"] == info_hash]

    def wait_for(pred, timeout=30):
        end = time.time() + timeout
        while time.time() < end:
            try:
                if pred():
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    failures = []

    def check(cond, label):
        print(("  OK   " if cond else "  FAIL ") + label)
        if not cond:
            failures.append(label)

    try:
        if not wait_for(lambda: announces(main_hash), 40):
            check(False, "server started and sent a first announce")
            return 1
        first = announces(main_hash)[0]
        print("first announce:", first)
        check(first["event"] == "started", "first announce is 'started'")
        check(first["uploaded"] == "0" and first["downloaded"] == "0",
              "'started' reports session counters (persisted 2 GiB not re-sent)")
        time.sleep(2)
        check(not any(a["event"] == "completed" for a in announces(main_hash)),
              "no 'completed' for a torrent complete at start (BEP 3)")

        worst = max(call("GET", "/health")[1] for _ in range(3))
        check(worst < 0.5, f"/health responsive (worst {worst * 1000:.0f} ms)")

        torrents, _ = call("GET", "/api/torrents")
        check(torrents and torrents[0]["uploaded"] >= 2 * 1024 ** 3, "UI keeps the all-time uploaded total")

        time.sleep(6)
        _, dt = call("POST", "/api/stop", timeout=30)
        check(wait_for(lambda: any(a["event"] == "stopped" for a in announces(main_hash)), 10),
              "'stopped' sent on Stop")
        stopped = [a for a in announces(main_hash) if a["event"] == "stopped"][-1]
        check(0 < int(stopped["uploaded"]) < 1024 ** 3, f"'stopped' uploaded is session-relative ({stopped['uploaded']})")

        n = len(announces(main_hash))
        _, dt = call("POST", "/api/start", timeout=30)
        check(dt < 5, f"Start is immediate ({dt:.1f} s)")
        check(wait_for(lambda: len(announces(main_hash)) > n, 15), "announces again after Start")
        restart = announces(main_hash)[n]
        check(restart["event"] == "started" and restart["uploaded"] == "0", "restart is a fresh session")

        # file watcher after stop/start + tracker refusal
        (work / "torrents" / "rejected.torrent").write_bytes(bencodepy.encode(
            {b"announce": f"http://127.0.0.1:{tracker_port}/announce".encode(), b"info": rejected_info}))

        def rejected_flagged():
            for t in call("GET", "/api/torrents")[0]:
                if t["id"] == rejected_hash:
                    return t.get("rejectedReason") == "Unregistered torrent" and not t["isRunning"]
            return False

        check(wait_for(rejected_flagged, 30), "file watcher loads new torrent after Stop/Start; "
                                              "tracker refusal flags and stops it")
        count = len(announces(rejected_hash))
        time.sleep(8)  # > one monitor cycle: must not be restarted by the seed limit
        check(len(announces(rejected_hash)) == count and count >= 1, f"rejected torrent not re-announced ({count})")
    finally:
        app.terminate()
        try:
            app.wait(20)
        except subprocess.TimeoutExpired:
            app.kill()
        tracker.terminate()
        app_log.close()

    errors = [ln for ln in (work / "app.log").read_text(encoding="utf-8", errors="replace").splitlines()
              if "| ERROR" in ln or "Traceback" in ln]
    check(not errors, f"no ERROR/traceback in server log ({len(errors)})")
    for ln in errors[:15]:
        print("    ", ln)

    print("E2E", "PASSED" if not failures else f"FAILED ({len(failures)})")
    if failures:
        print("server log kept in", work)
    else:
        shutil.rmtree(work, ignore_errors=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
