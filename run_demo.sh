#!/usr/bin/env bash
# ===============================================================================
# Column-Stores vs. Row-Stores (SIGMOD 2008 Replication Lab)
# Cross-platform 1-click launcher for macOS and Linux
# ===============================================================================

set -e
cd "$(dirname "$0")"

echo "==============================================================================="
echo "  COLUMN-STORES VS. ROW-STORES: HOW DIFFERENT ARE THEY REALLY? (SIGMOD 2008)"
echo "  Interactive Replication Lab & Benchmark Dashboard"
echo "==============================================================================="
echo ""

# Detect Python interpreter
PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "[NOTICE] Python 3 was not detected in PATH."
    echo "Opening index.html directly in your default browser (Offline Standalone Mode)..."
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open index.html
    elif command -v open >/dev/null 2>&1; then
        open index.html
    else
        echo "Please open index.html manually in your web browser."
    fi
    exit 0
fi

echo "[+] Python detected: $($PYTHON_BIN --version)"
echo "[*] Verifying dependencies from requirements.txt..."
$PYTHON_BIN -m pip install -r requirements.txt --quiet || echo "[WARNING] pip install had warnings, continuing..."

echo "[*] Starting Python backend server on http://localhost:8000 ..."
$PYTHON_BIN web_server.py &
SERVER_PID=$!
sleep 2

URL="http://localhost:8000"
echo "[+] Opening $URL in your web browser..."
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
    open "$URL"
else
    echo "Please visit $URL in your web browser."
fi

echo ""
echo "==============================================================================="
echo "[SUCCESS] Local server is running on $URL (PID: $SERVER_PID)"
echo "Available Modules:"
echo " - Tab 0: Architecture & SSBM Star Schema"
echo " - Tab 1: Storage Layout & Physical Organization"
echo " - Tab 2: Compression & Vectorized Execution"
echo " - Tab 3: Invisible Join (3-Phase Hash Bitmaps)"
echo " - Tab 4: Benchmark Suite & Query Profiler"
echo ""
echo "Press [Ctrl+C] to stop the server."
echo "==============================================================================="

trap "kill $SERVER_PID 2>/dev/null; exit 0" INT TERM
wait $SERVER_PID
