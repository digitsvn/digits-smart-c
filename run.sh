#!/bin/bash
# =============================================================================
#                    SMART C AI - LAUNCHER
# =============================================================================

APP_HOME="$HOME/.digits"
if [ ! -d "$APP_HOME" ]; then
    APP_HOME="$HOME/.xiaozhi"
fi

cd "$APP_HOME"
mkdir -p logs

# Detect display environment
if [ -n "$WAYLAND_DISPLAY" ]; then
    echo "🖥️  Running on Wayland: $WAYLAND_DISPLAY"
    export QT_QPA_PLATFORM=wayland
elif [ -n "$DISPLAY" ]; then
    echo "🖥️  Running on X11: $DISPLAY"
    export QT_QPA_PLATFORM=xcb
else
    # Try to find Wayland socket
    WAYLAND_SOCK=$(ls /run/user/$(id -u)/wayland-0 2>/dev/null | head -1)
    if [ -n "$WAYLAND_SOCK" ]; then
        export WAYLAND_DISPLAY=$(basename "$WAYLAND_SOCK")
        export QT_QPA_PLATFORM=wayland
        echo "🖥️  Found Wayland socket: $WAYLAND_DISPLAY"
    else
        # Fallback to X11 display :0
        export DISPLAY=:0
        export QT_QPA_PLATFORM=xcb
        echo "🖥️  Fallback to DISPLAY=:0"
    fi
fi

# XDG Runtime
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# Start PulseAudio if not running  
if ! pulseaudio --check 2>/dev/null; then
    echo "🔊 Starting PulseAudio..."
    pulseaudio --start --daemonize=true 2>/dev/null || true
    sleep 1
fi

# Ensure device ID
python3 "$APP_HOME/scripts/ensure_device_id_mac.py" 2>/dev/null || true

# Stop existing instance
pkill -f "python3 main.py" 2>/dev/null
sleep 0.5

echo "🚀 Starting Smart C AI..."
echo "📁 App directory: $APP_HOME"
echo "📝 Logs: $APP_HOME/logs/smartc.log"

# Run the application
exec python3 main.py --mode gui 2>&1 | tee -a logs/smartc.log
