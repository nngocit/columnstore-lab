#!/usr/bin/env python3
"""Minimal zero-dependency HTTP server (port 8000) calling the pure-Python demo engine in-process."""
import json, threading, mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from datetime import datetime
from column_store_demo import chay_demo_cho_web, chay_invisible_join_cho_web, lay_du_lieu_preview

DASHBOARD = Path(__file__).resolve().parent / "web_dashboard.html"
CORS = (("Access-Control-Allow-Origin", "*"), ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"), ("Access-Control-Allow-Headers", "Content-Type, Accept"), ("Cache-Control", "no-store"))
_RUN_LOCK = threading.Lock()


class DemoHandler(BaseHTTPRequestHandler):
    """HTTP handler for web_dashboard.html, /api/status, /api/run, and /api/invisible-join."""
    protocol_version = "HTTP/1.1"

    def _reply(self, code: int, body, ctype: str = "application/json; charset=utf-8"):
        try:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8") if isinstance(body, dict) else body
            self.send_response(code)
            for k, v in CORS:
                self.send_header(k, v)
            if code != 204:
                self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if data:
                self.wfile.write(data)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
            pass
        except Exception:
            pass

    def log_message(self, format, *args):
        # Silence default stderr logging to prevent pipe break on Windows
        pass

    def do_OPTIONS(self): self._reply(204, b"")

    def do_GET(self):
        route = urlsplit(self.path).path
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [SERVER GET] {route} (path: {self.path})")
        if route in ("/", "/index.html", "/web_dashboard.html") and DASHBOARD.is_file():
            return self._reply(200, DASHBOARD.read_bytes(), "text/html; charset=utf-8")
        if route == "/api/status":
            return self._reply(200, {"status": "ready"})
        if route in ("/column_store_demo.py", "/column_store_demo_de_hieu.py"):
            target_f = DASHBOARD.parent / route.lstrip("/")
            if target_f.is_file():
                return self._reply(200, target_f.read_bytes(), "text/plain; charset=utf-8")
        if route.startswith("/locales/"):
            rel = route[len("/locales/"):]
            local_file = (DASHBOARD.parent / "locales" / rel).resolve()
            if local_file.is_file() and str(local_file).startswith(str((DASHBOARD.parent / "locales").resolve())):
                if rel.endswith(".json"):
                    ct = "application/json; charset=utf-8"
                elif rel.endswith(".js"):
                    ct = "application/javascript; charset=utf-8"
                else:
                    ct = mimetypes.guess_type(local_file.name)[0] or "application/octet-stream"
                return self._reply(200, local_file.read_bytes(), ct)
        if route.startswith("/monaco/"):
            rel = route[len("/monaco/"):]
            local_file = (DASHBOARD.parent / "monaco" / rel).resolve()
            if local_file.is_file() and str(local_file).startswith(str((DASHBOARD.parent / "monaco").resolve())):
                ct = mimetypes.guess_type(local_file.name)[0] or ("font/ttf" if rel.endswith(".ttf") else "application/octet-stream")
                return self._reply(200, local_file.read_bytes(), ct)
        if route in ("/api/preview-data", "/api/preview"):
            try:
                query = parse_qs(urlsplit(self.path).query)
                seed = int(query.get("seed", [42])[0])
                rows = int(query.get("rows", [6_000_000])[0])
                data = lay_du_lieu_preview(rows=rows, seed=seed)
                return self._reply(200, data)
            except Exception as exc:
                return self._reply(500, {"ok": False, "error": str(exc)})
        self._reply(204 if route == "/favicon.ico" else 404, b"" if route == "/favicon.ico" else {"error": f"Unknown route: {route}"})

    def do_POST(self):
        route = urlsplit(self.path).path
        if route not in {"/api/run", "/api/invisible-join", "/api/preview-data", "/api/preview"}:
            return self._reply(404, {"error": f"Unknown route: {route}"})

        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(n).decode("utf-8")) if n > 0 else {}
            if not isinstance(req, dict):
                raise ValueError("JSON body must be an object")
        except (ValueError, UnicodeDecodeError, TypeError, json.JSONDecodeError) as exc:
            return self._reply(400, {"ok": False, "error": str(exc)})

        if route == "/api/run":
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [SERVER POST] /api/run part={req.get('part')} rows={req.get('rows')} seed={req.get('seed')}")
            try:
                part = str(req.get("part", "all")).strip().lower()
                rows_raw, seed_raw = req.get("rows", 6_000_000), req.get("seed", 42)
                if isinstance(rows_raw, bool) or isinstance(seed_raw, bool):
                    raise ValueError("rows and seed must be integers")
                rows, seed = int(rows_raw), int(seed_raw)
                cols = req.get("cols")
                if cols is not None and not isinstance(cols, list):
                    raise ValueError("cols must be a list of column names")
                sql = req.get("sql")
                if sql is not None and not isinstance(sql, str):
                    raise ValueError("sql must be a string")
                rle_start_raw, rle_end_raw = req.get("rle_start"), req.get("rle_end")
                if isinstance(rle_start_raw, bool) or isinstance(rle_end_raw, bool):
                    raise ValueError("rle_start and rle_end must be integers")
                rle_start = int(rle_start_raw) if rle_start_raw is not None else None
                rle_end = int(rle_end_raw) if rle_end_raw is not None else None
                if part not in {"1", "2", "3", "4", "all"} or not (1 <= rows <= 30_000_000):
                    raise ValueError("Invalid part or rows (1..30,000,000)")
            except (ValueError, TypeError) as exc:
                return self._reply(400, {"ok": False, "error": str(exc)})
            try:
                with _RUN_LOCK:
                    return self._reply(200, chay_demo_cho_web(part=part, rows=rows, seed=seed, cols=cols, sql=sql, rle_start=rle_start, rle_end=rle_end))
            except Exception as exc:
                return self._reply(500, {"ok": False, "error": str(exc)})

        elif route in {"/api/preview-data", "/api/preview"}:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [SERVER POST] /api/preview-data rows={req.get('rows')} seed={req.get('seed')}")
            try:
                rows_raw = req.get("rows", 6_000_000)
                seed_raw = req.get("seed", 42)
                rows = 6_000_000 if rows_raw is None else int(rows_raw)
                seed = 42 if seed_raw is None else int(seed_raw)
                with _RUN_LOCK:
                    return self._reply(200, lay_du_lieu_preview(rows=rows, seed=seed))
            except Exception as exc:
                return self._reply(500, {"ok": False, "error": str(exc)})

        elif route == "/api/invisible-join":
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [SERVER POST] /api/invisible-join cust={req.get('cust_region')} supp={req.get('supp_region')} rows={req.get('rows')} seed={req.get('seed')}")
            try:
                cust_region = str(req.get("cust_region", "Asia") or "Asia").strip()
                supp_region = str(req.get("supp_region", "Asia") or "Asia").strip()
                ys_raw = req.get("year_start", 1992)
                ye_raw = req.get("year_end", 1997)
                rows_raw = req.get("rows", 6_000_000)
                seed_raw = req.get("seed", 42)

                if any(isinstance(v, bool) for v in (ys_raw, ye_raw, rows_raw, seed_raw)):
                    raise ValueError("Numeric fields must not be boolean")

                year_start = 1992 if ys_raw is None else int(ys_raw)
                year_end = 1997 if ye_raw is None else int(ye_raw)
                rows = 6_000_000 if rows_raw is None else int(rows_raw)
                seed = 42 if seed_raw is None else int(seed_raw)

                if not (1 <= rows <= 30_000_000):
                    raise ValueError("rows must be between 1 and 30,000,000")
                if year_start > year_end:
                    raise ValueError("year_start must be <= year_end")
            except (ValueError, TypeError) as exc:
                return self._reply(400, {"ok": False, "error": str(exc)})
            try:
                with _RUN_LOCK:
                    return self._reply(200, chay_invisible_join_cho_web(
                        cust_region=cust_region,
                        supp_region=supp_region,
                        year_start=year_start,
                        year_end=year_end,
                        rows=rows,
                        seed=seed
                    ))
            except Exception as exc:
                return self._reply(500, {"ok": False, "error": str(exc)})


def check_port_open(host="127.0.0.1", port=8000):
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False

def check_server_healthy(host="127.0.0.1", port=8000):
    try:
        import urllib.request
        req = urllib.request.Request(f"http://{host}:{port}/api/status", headers={"User-Agent": "HealthCheck"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False

def kill_process_on_port(port=8000):
    import os, subprocess, time
    try:
        out = subprocess.check_output(f'netstat -aon | findstr ":{port}" | findstr "LISTENING"', shell=True, text=True)
        for line in out.strip().splitlines():
            parts = line.strip().split()
            if len(parts) >= 5:
                pid = parts[-1]
                if pid and pid != str(os.getpid()):
                    print(f"[*] Releasing port {port} occupied by previous process (PID: {pid})...")
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
        time.sleep(1.0)
    except Exception:
        pass

if __name__ == "__main__":
    import sys, time, webbrowser
    host, port = "127.0.0.1", 8000

    # 1. If server is already running and healthy:
    if check_server_healthy(host, port):
        print("=" * 75)
        print(f"  [OK] DEMO SERVER IS ALREADY RUNNING AT: http://{host}:{port}")
        print("  >> Automatically opening default web browser...")
        print("=" * 75)
        webbrowser.open(f"http://{host}:{port}")
        print("\n>> Press Enter to exit (server will continue running in background)...")
        try: input()
        except Exception: pass
        sys.exit(0)

    # 2. If port 8000 is occupied by a stale process, release it:
    if check_port_open(host, port):
        print(f"[*] Detected port {port} is occupied, releasing...")
        kill_process_on_port(port)

    # 3. Start server with 5-attempt retry mechanism:
    ThreadingHTTPServer.allow_reuse_address, ThreadingHTTPServer.daemon_threads = True, True
    srv = None
    for attempt in range(1, 6):
        try:
            srv = ThreadingHTTPServer((host, port), DemoHandler)
            break
        except OSError as e:
            if attempt < 5:
                print(f"[*] Port {port} is being released by the OS... Retrying attempt {attempt}/5 in 1.2s...")
                kill_process_on_port(port)
                time.sleep(1.2)
            else:
                print(f"[ERROR] Unable to bind to port {port} after 5 attempts: {e}")
                sys.exit(1)

    # 4. Automatically open web browser after 0.8s
    def _open_browser():
        time.sleep(0.8)
        print(f">> Web browser opened at: http://{host}:{port}")
        webbrowser.open(f"http://{host}:{port}")

    threading.Thread(target=_open_browser, daemon=True).start()

    print("=" * 75)
    print("  COLUMN-STORE (SIGMOD 2008) DEMO SERVER IS RUNNING:")
    print(f"  URL: http://{host}:{port}")
    print("  To stop web server: Press Ctrl + C or close this window.")
    print("=" * 75)

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped gracefully.")
    finally:
        try: srv.server_close()
        except Exception: pass
