#!/bin/bash
# ToneForge / KentKClaw-Studio Watchdog
# Checks all services every 2 min, restarts if dead

LOG="/tmp/watchdog.log"
STAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() { echo "[$STAMP] $1" >> "$LOG"; }

# 1. ComfyUI (port 8188)
if ! curl -s -o /dev/null -w '' http://localhost:8188 2>/dev/null; then
    log "⚠ ComfyUI down, restarting..."
    cd /home/skybo/ComfyUI && nohup .venv/bin/python main.py --listen 0.0.0.0 --port 8188 --fp16-unet --fp16-vae > /tmp/comfyui.log 2>&1 &
    log "✅ ComfyUI restarted (PID: $!)"
fi

# 2. Middleware (port 3000)
if ! curl -s -o /dev/null -w '' http://localhost:3000 2>/dev/null; then
    log "⚠ Middleware down, restarting..."
    cd /home/skybo/KentKClaw-Studio/middleware && nohup node server.js > /tmp/middleware.log 2>&1 &
    log "✅ Middleware restarted (PID: $!)"
fi

# 3. Hermes API Server (port 3001)
if ! curl -s -o /dev/null -w '' http://localhost:3001/health 2>/dev/null; then
    log "⚠ Hermes API down, restarting..."
    cd /home/skybo/KentKClaw-Studio/hermes-api-server && nohup node server.js > /tmp/hermes-api.log 2>&1 &
    log "✅ Hermes API restarted (PID: $!)"
fi

# 4. Hermes Gateway
if ! pgrep -f "hermes gateway run" > /dev/null 2>&1; then
    log "⚠ Hermes Gateway down, restarting..."
    nohup hermes gateway run > ~/.hermes/logs/gateway.log 2>&1 &
    log "✅ Hermes Gateway restarted (PID: $!)"
fi

# 5. Ngrok tunnel (optional, check if configured)
if command -v ngrok &>/dev/null; then
    if ! pgrep -f "ngrok http" > /dev/null 2>&1; then
        log "⚠ Ngrok down, restarting..."
        nohup ngrok http 80 --log=stdout > /tmp/ngrok.log 2>&1 &
        log "✅ Ngrok restarted (PID: $!)"
    fi
fi

# Keep log under 500 lines
if [ -f "$LOG" ]; then
    lines=$(wc -l < "$LOG")
    if [ "$lines" -gt 500 ]; then
        tail -200 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
    fi
fi
