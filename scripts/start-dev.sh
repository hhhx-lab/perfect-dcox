#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
STORAGE_DIR="$ROOT_DIR/storage"
LOG_DIR="$STORAGE_DIR/logs"
PID_DIR="$STORAGE_DIR/pids"

HOST="${HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
MODE="start"

BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
BACKEND_META_FILE="$PID_DIR/backend.meta"
FRONTEND_META_FILE="$PID_DIR/frontend.meta"

usage() {
  cat <<EOF
Usage: scripts/start-dev.sh [--restart|--stop|--status] [--host HOST] [--backend-port PORT] [--frontend-port PORT]

Default:
  backend  http://$HOST:$BACKEND_PORT
  frontend http://$HOST:$FRONTEND_PORT

Examples:
  ./scripts/start-dev.sh
  ./scripts/start-dev.sh --restart
  ./scripts/start-dev.sh --status
  ./scripts/start-dev.sh --stop
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --restart)
      MODE="restart"
      shift
      ;;
    --stop)
      MODE="stop"
      shift
      ;;
    --status)
      MODE="status"
      shift
      ;;
    --host)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --host" >&2
        exit 1
      fi
      HOST="${2:-}"
      shift 2
      ;;
    --backend-port)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --backend-port" >&2
        exit 1
      fi
      BACKEND_PORT="${2:-}"
      shift 2
      ;;
    --frontend-port)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --frontend-port" >&2
        exit 1
      fi
      FRONTEND_PORT="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [ -z "$HOST" ]; then
  echo "HOST cannot be empty" >&2
  exit 1
fi

case "$BACKEND_PORT" in
  ''|*[!0-9]*)
    echo "BACKEND_PORT must be a number" >&2
    exit 1
    ;;
esac

case "$FRONTEND_PORT" in
  ''|*[!0-9]*)
    echo "FRONTEND_PORT must be a number" >&2
    exit 1
    ;;
esac

BACKEND_URL="http://$HOST:$BACKEND_PORT"
FRONTEND_URL="http://$HOST:$FRONTEND_PORT"
API_BASE_URL="${VITE_API_BASE_URL:-$BACKEND_URL/api}"

mkdir -p "$LOG_DIR" "$PID_DIR"

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

pid_alive() {
  [ -n "${1:-}" ] && kill -0 "$1" >/dev/null 2>&1
}

read_pid() {
  local pid_file="$1"
  if [ -f "$pid_file" ]; then
    sed -n '1p' "$pid_file" | tr -cd '0-9'
  fi
}

read_meta_value() {
  local meta_file="$1"
  local key="$2"
  if [ -f "$meta_file" ]; then
    sed -n "s/^$key=//p" "$meta_file" | sed -n '1p'
  fi
}

write_meta_file() {
  local meta_file="$1"
  local host="$2"
  local port="$3"
  local url="$4"

  {
    echo "host=$host"
    echo "port=$port"
    echo "url=$url"
  } > "$meta_file"
}

port_listeners() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
}

port_has_listener() {
  local port="$1"
  [ -n "$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)" ]
}

collect_descendants() {
  local pid="$1"
  local child
  for child in $(pgrep -P "$pid" 2>/dev/null || true); do
    collect_descendants "$child"
    echo "$child"
  done
}

stop_pid_file() {
  local name="$1"
  local pid_file="$2"
  local meta_file="$3"
  local pid
  pid="$(read_pid "$pid_file" || true)"

  if [ -z "$pid" ]; then
    rm -f "$pid_file"
    rm -f "$meta_file"
    echo "$name: not running"
    return 0
  fi

  if ! pid_alive "$pid"; then
    rm -f "$pid_file"
    rm -f "$meta_file"
    echo "$name: stale pid removed ($pid)"
    return 0
  fi

  local descendants
  descendants="$(collect_descendants "$pid" | sort -rn | tr '\n' ' ')"
  echo "$name: stopping pid $pid"
  # shellcheck disable=SC2086
  kill $descendants "$pid" >/dev/null 2>&1 || true

  local i
  for i in $(seq 1 30); do
    if ! pid_alive "$pid"; then
      rm -f "$pid_file"
      rm -f "$meta_file"
      echo "$name: stopped"
      return 0
    fi
    sleep 0.2
  done

  echo "$name: forcing pid $pid"
  # shellcheck disable=SC2086
  kill -9 $descendants "$pid" >/dev/null 2>&1 || true
  rm -f "$pid_file"
  rm -f "$meta_file"
}

print_service_status() {
  local name="$1"
  local pid_file="$2"
  local meta_file="$3"
  local default_port="$4"
  local log_file="$5"
  local pid
  local port
  local url
  pid="$(read_pid "$pid_file" || true)"
  port="$(read_meta_value "$meta_file" port || true)"
  url="$(read_meta_value "$meta_file" url || true)"
  port="${port:-$default_port}"

  if [ -n "$pid" ] && pid_alive "$pid"; then
    if [ -n "$url" ]; then
      echo "$name: running (pid $pid, url $url, log $log_file)"
    else
      echo "$name: running (pid $pid, port $port, log $log_file)"
    fi
  else
    echo "$name: not running (port $port, log $log_file)"
  fi

  if port_has_listener "$port"; then
    port_listeners "$port" | sed 's/^/  /'
  fi
}

ensure_tools() {
  local missing=0
  if ! command_exists uv; then
    echo "Missing dependency: uv" >&2
    missing=1
  fi
  if ! command_exists npm; then
    echo "Missing dependency: npm" >&2
    missing=1
  fi
  if ! command_exists curl; then
    echo "Missing dependency: curl" >&2
    missing=1
  fi
  if ! command_exists lsof; then
    echo "Missing dependency: lsof" >&2
    missing=1
  fi
  if ! command_exists python3; then
    echo "Missing dependency: python3" >&2
    missing=1
  fi
  if [ "$missing" -ne 0 ]; then
    exit 1
  fi
}

ensure_project_files() {
  if [ ! -f "$BACKEND_DIR/app/main.py" ]; then
    echo "Backend entry not found: $BACKEND_DIR/app/main.py" >&2
    exit 1
  fi
  if [ ! -f "$FRONTEND_DIR/package.json" ]; then
    echo "Frontend package not found: $FRONTEND_DIR/package.json" >&2
    exit 1
  fi
}

ensure_port_free_for_start() {
  local name="$1"
  local pid_file="$2"
  local meta_file="$3"
  local port="$4"
  local pid
  local managed_port
  local managed_url
  pid="$(read_pid "$pid_file" || true)"

  if [ -n "$pid" ] && pid_alive "$pid"; then
    managed_port="$(read_meta_value "$meta_file" port || true)"
    managed_url="$(read_meta_value "$meta_file" url || true)"
    if [ "$managed_port" = "$port" ]; then
      echo "$name: already managed by pid $pid at ${managed_url:-port $managed_port}"
      return 1
    fi
    echo "$name: already managed by pid $pid at ${managed_url:-port ${managed_port:-unknown}}" >&2
    echo "Run ./scripts/start-dev.sh --stop first, or use --restart with the desired ports." >&2
    exit 1
  fi
  rm -f "$pid_file"
  rm -f "$meta_file"

  if port_has_listener "$port"; then
    echo "$name: port $port is already in use by another process:" >&2
    port_listeners "$port" >&2
    echo "Use a different port or stop that process first. This script only stops processes it started." >&2
    exit 1
  fi

  return 0
}

wait_for_url() {
  local name="$1"
  local url="$2"
  local log_file="$3"
  local i

  for i in $(seq 1 80); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "$name: ready at $url"
      return 0
    fi
    sleep 0.5
  done

  echo "$name: failed to become ready at $url" >&2
  echo "Last log lines from $log_file:" >&2
  tail -n 80 "$log_file" >&2 || true
  exit 1
}

install_frontend_deps_if_needed() {
  if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "frontend: node_modules not found, running npm install"
    (cd "$FRONTEND_DIR" && npm install)
  fi
}

start_detached() {
  local pid_file="$1"
  local log_file="$2"
  local cwd="$3"
  shift 3

  python3 - "$pid_file" "$log_file" "$cwd" "$@" <<'PY'
import os
import subprocess
import sys

pid_file, log_file, cwd, *cmd = sys.argv[1:]
os.makedirs(os.path.dirname(pid_file), exist_ok=True)
os.makedirs(os.path.dirname(log_file), exist_ok=True)

log = open(log_file, "ab", buffering=0)
process = subprocess.Popen(
    cmd,
    cwd=cwd,
    env=os.environ.copy(),
    stdin=subprocess.DEVNULL,
    stdout=log,
    stderr=subprocess.STDOUT,
    start_new_session=True,
    close_fds=True,
)

with open(pid_file, "w", encoding="utf-8") as handle:
    handle.write(str(process.pid))

print(process.pid)
PY
}

start_backend() {
  if ! ensure_port_free_for_start "backend" "$BACKEND_PID_FILE" "$BACKEND_META_FILE" "$BACKEND_PORT"; then
    return 0
  fi

  : > "$BACKEND_LOG"
  echo "backend: starting on $BACKEND_URL"
  local cors_origins
  local pid
  cors_origins="${CORS_ORIGINS:-[\"http://$HOST:$FRONTEND_PORT\",\"http://localhost:$FRONTEND_PORT\"]}"
  export CORS_ORIGINS="$cors_origins"
  pid="$(start_detached "$BACKEND_PID_FILE" "$BACKEND_LOG" "$BACKEND_DIR" uv run uvicorn app.main:app --reload --host "$HOST" --port "$BACKEND_PORT")"
  echo "backend: pid $pid"
  write_meta_file "$BACKEND_META_FILE" "$HOST" "$BACKEND_PORT" "$BACKEND_URL"
}

start_frontend() {
  if ! ensure_port_free_for_start "frontend" "$FRONTEND_PID_FILE" "$FRONTEND_META_FILE" "$FRONTEND_PORT"; then
    return 0
  fi

  install_frontend_deps_if_needed

  : > "$FRONTEND_LOG"
  echo "frontend: starting on $FRONTEND_URL"
  local pid
  export VITE_API_BASE_URL="$API_BASE_URL"
  pid="$(start_detached "$FRONTEND_PID_FILE" "$FRONTEND_LOG" "$FRONTEND_DIR" npm run dev -- --host "$HOST" --port "$FRONTEND_PORT")"
  echo "frontend: pid $pid"
  write_meta_file "$FRONTEND_META_FILE" "$HOST" "$FRONTEND_PORT" "$FRONTEND_URL"
}

case "$MODE" in
  status)
    print_service_status "backend" "$BACKEND_PID_FILE" "$BACKEND_META_FILE" "$BACKEND_PORT" "$BACKEND_LOG"
    print_service_status "frontend" "$FRONTEND_PID_FILE" "$FRONTEND_META_FILE" "$FRONTEND_PORT" "$FRONTEND_LOG"
    exit 0
    ;;
  stop)
    stop_pid_file "frontend" "$FRONTEND_PID_FILE" "$FRONTEND_META_FILE"
    stop_pid_file "backend" "$BACKEND_PID_FILE" "$BACKEND_META_FILE"
    exit 0
    ;;
  restart)
    stop_pid_file "frontend" "$FRONTEND_PID_FILE" "$FRONTEND_META_FILE"
    stop_pid_file "backend" "$BACKEND_PID_FILE" "$BACKEND_META_FILE"
    ;;
esac

ensure_tools
ensure_project_files
start_backend
start_frontend

wait_for_url "backend" "$BACKEND_URL/api/health" "$BACKEND_LOG"
wait_for_url "frontend" "$FRONTEND_URL" "$FRONTEND_LOG"

cat <<EOF

Dev servers are ready.
Frontend: $FRONTEND_URL
Backend:  $BACKEND_URL
API:      $API_BASE_URL

Logs:
  $BACKEND_LOG
  $FRONTEND_LOG

Manage:
  ./scripts/start-dev.sh --status
  ./scripts/start-dev.sh --restart
  ./scripts/start-dev.sh --stop
EOF
