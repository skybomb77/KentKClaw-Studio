#!/bin/bash
# Kent & KClaw Studio - All Services Launcher
# Usage: bash start-services.sh [start|stop|status]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$SCRIPT_DIR/.pids"
mkdir -p "$PID_DIR"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_port() {
    ss -tlnp 2>/dev/null | grep -q ":$1 " && echo "running" || echo "stopped"
}

start_service() {
    local name=$1
    local dir=$2
    local cmd=$3
    local port=$4
    local pidfile="$PID_DIR/$name.pid"

    if [ "$(check_port $port)" = "running" ]; then
        echo -e "${YELLOW}⚡ $name already running on :$port${NC}"
        return 0
    fi

    echo -n "🚀 Starting $name on :$port... "
    cd "$dir" && nohup $cmd > "$PID_DIR/$name.log" 2>&1 &
    echo $! > "$pidfile"
    sleep 2

    if [ "$(check_port $port)" = "running" ]; then
        echo -e "${GREEN}✅ OK${NC}"
    else
        echo -e "${RED}❌ FAILED (check $PID_DIR/$name.log)${NC}"
    fi
}

stop_service() {
    local name=$1
    local port=$2
    local pidfile="$PID_DIR/$name.pid"

    if [ -f "$pidfile" ]; then
        kill $(cat "$pidfile") 2>/dev/null
        rm -f "$pidfile"
        echo -e "${RED}🛑 Stopped $name${NC}"
    else
        echo -e "${YELLOW}⚠️  $name not running (no PID file)${NC}"
    fi
}

case "${1:-start}" in
    start)
        echo ""
        echo "🏗️  Kent & KClaw Studio - Starting all services"
        echo "==========================================="
        start_service "hermes" "$SCRIPT_DIR/hermes-api-server" "node server.js" 3001
        start_service "middleware" "$SCRIPT_DIR/middleware" "node server.js" 3000
        echo ""
        echo "==========================================="
        echo -e "📊 ${GREEN}Services Status:${NC}"
        echo "  Hermes API:   :3001 → $(check_port 3001)"
        echo "  Middleware:   :3000 → $(check_port 3000)"
        echo "  ComfyUI:      :8188 → $(check_port 8188) (GPU engine)"
        echo ""
        echo "  Health: curl http://localhost:3000/api/health"
        echo "  Music:  curl -X POST http://localhost:3000/api/forge-music -H 'Content-Type: application/json' -d '{\"style\":\"Lofi Hip Hop\",\"duration\":5}'"
        echo ""
        ;;
    stop)
        echo ""
        echo "🛑 Stopping all services..."
        stop_service "hermes" 3001
        stop_service "middleware" 3000
        echo ""
        ;;
    status)
        echo ""
        echo "📊 Services Status:"
        echo "  Hermes API:   :3001 → $(check_port 3001)"
        echo "  Middleware:   :3000 → $(check_port 3000)"
        echo "  ComfyUI:      :8188 → $(check_port 8188)"
        echo "  GPU: $(nvidia-smi --query-gpu=temperature.gpu,memory.used,memory.total --format=csv,noheader 2>/dev/null || echo 'N/A')"
        echo ""
        ;;
    restart)
        $0 stop
        sleep 1
        $0 start
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        ;;
esac
