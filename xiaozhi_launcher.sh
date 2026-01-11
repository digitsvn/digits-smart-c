#!/bin/bash
# xiaozhi_launcher.sh - Official Launcher for Digits Smart C AI

# Prefer the renamed install dir, but keep backward compatibility.
APP_HOME="$HOME/.digits"
if [ ! -d "$APP_HOME" ]; then
	APP_HOME="$HOME/.xiaozhi"
fi

# 1. Ensure DEVICE_ID matches original scheme (efuse MAC)
# The upstream code uses efuse MAC as DEVICE_ID; server activation is tied to it.
python3 "$APP_HOME/scripts/ensure_device_id_mac.py"

# 2. Check for First Run / Activation
# If not activated, config might be needing setup.
# The app's 'main.py' handles activation flow.

# 3. Launch App
# Ensure Display is set for GUI
export DISPLAY=:0

# Change directory to app root
cd "$APP_HOME"

# Stop any existing instance
pkill -f "python3 main.py" 2>/dev/null

echo "🚀 Starting Digits Smart C AI..."

# Run the main application
# --mode gui: Launch with graphical interface
exec python3 main.py --mode gui
