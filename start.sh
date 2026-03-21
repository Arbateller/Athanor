#!/bin/bash
#
#  start.sh - Start the entire BIST Tracker stack
#
#  Created by Murat Şahin
#
#  Usage:
#    ./start.sh          Start all services
#    ./start.sh stop     Stop all services
#

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$PROJECT_DIR/.pids"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()   { echo -e "${CYAN}[BIST]${NC} $1"; }
ok()    { echo -e "${GREEN}  ✓${NC} $1"; }
warn()  { echo -e "${YELLOW}  ⚠${NC} $1"; }
fail()  { echo -e "${RED}  ✗${NC} $1"; }

save_pid() {
  echo "$1=$2" >> "$PIDFILE"
}

stop_all() {
  log "Stopping all services..."
  if [ -f "$PIDFILE" ]; then
    while IFS='=' read -r name pid; do
      if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null
        ok "Stopped $name (PID $pid)"
      fi
    done < "$PIDFILE"
    rm -f "$PIDFILE"
  fi

  # Also stop Redis if we started it
  if redis-cli ping &>/dev/null; then
    redis-cli shutdown nosave &>/dev/null
    ok "Stopped Redis"
  fi

  log "All services stopped."
  exit 0
}

# Handle stop command
if [ "$1" = "stop" ]; then
  stop_all
fi

# Cleanup on exit
trap stop_all SIGINT SIGTERM

echo ""
echo -e "${BOLD}══════════════════════════════════════════${NC}"
echo -e "${BOLD}   📈 BIST Tracker — Full Stack Startup${NC}"
echo -e "${BOLD}══════════════════════════════════════════${NC}"
echo ""

# ── 1. Redis ──────────────────────────────────────────
log "Starting Redis..."
if redis-cli ping &>/dev/null; then
  ok "Redis already running"
else
  redis-server --daemonize yes --loglevel warning
  sleep 1
  if redis-cli ping &>/dev/null; then
    ok "Redis started on port 6379"
  else
    fail "Redis failed to start"
    exit 1
  fi
fi

# ── 2. Python virtual environment ─────────────────────
log "Activating Python environment..."
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
  source "$PROJECT_DIR/venv/bin/activate"
  ok "Virtual environment activated"
else
  fail "No venv found at $PROJECT_DIR/venv"
  fail "Run: python3 -m venv venv && pip install -r requirements.txt"
  exit 1
fi

# ── 3. Fetcher ────────────────────────────────────────
log "Starting Fetcher..."
cd "$PROJECT_DIR"
python fetcher/fetcher.py > "$PROJECT_DIR/logs/fetcher.log" 2>&1 &
FETCHER_PID=$!
save_pid "fetcher" "$FETCHER_PID"
ok "Fetcher started (PID $FETCHER_PID) — logs: logs/fetcher.log"

# ── 4. API Server ─────────────────────────────────────
log "Starting API server..."
cd "$PROJECT_DIR"
uvicorn api.main:app --host 0.0.0.0 --port 8000 > "$PROJECT_DIR/logs/api.log" 2>&1 &
API_PID=$!
save_pid "api" "$API_PID"
ok "API started on http://0.0.0.0:8000 (PID $API_PID) — logs: logs/api.log"

# ── 5. React Dashboard ───────────────────────────────
log "Starting React Dashboard..."
cd "$PROJECT_DIR/dashboard"
npm run dev -- --host > "$PROJECT_DIR/logs/dashboard.log" 2>&1 &
DASH_PID=$!
save_pid "dashboard" "$DASH_PID"
ok "Dashboard started on http://localhost:3000 (PID $DASH_PID) — logs: logs/dashboard.log"

cd "$PROJECT_DIR"

# ── Summary ───────────────────────────────────────────
echo ""
echo -e "${BOLD}══════════════════════════════════════════${NC}"
echo -e "  ${GREEN}All services running!${NC}"
echo ""
echo -e "  Redis:      ${CYAN}localhost:6379${NC}"
echo -e "  API:        ${CYAN}http://0.0.0.0:8000${NC}"
echo -e "  API Docs:   ${CYAN}http://0.0.0.0:8000/docs${NC}"
echo -e "  Dashboard:  ${CYAN}http://localhost:3000${NC}"
echo ""
echo -e "  Press ${BOLD}Ctrl+C${NC} to stop all services"
echo -e "  Or run: ${BOLD}./start.sh stop${NC}"
echo -e "${BOLD}══════════════════════════════════════════${NC}"
echo ""

# Wait for all background processes
wait
