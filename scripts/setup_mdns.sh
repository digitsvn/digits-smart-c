#!/bin/bash
# =============================================================================
# mDNS Setup Script for Smart C AI
# =============================================================================
# Enables access via smartc.local instead of IP address
# Requirements: avahi-daemon
# =============================================================================

set -e

HOSTNAME="smartc"

echo "🔧 Setting up mDNS (Bonjour/Avahi) for Smart C AI..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo bash $0"
    exit 1
fi

# Install avahi-daemon if not present
if ! command -v avahi-daemon &> /dev/null; then
    echo "📦 Installing avahi-daemon..."
    apt-get update -qq
    apt-get install -y avahi-daemon avahi-utils
fi

# Set hostname
echo "🏷️  Setting hostname to: $HOSTNAME"
hostnamectl set-hostname "$HOSTNAME"

# Update /etc/hosts
if ! grep -q "$HOSTNAME" /etc/hosts; then
    echo "127.0.1.1   $HOSTNAME" >> /etc/hosts
fi

# Create avahi service file for HTTP
echo "📝 Creating Avahi service file..."
cat > /etc/avahi/services/smartc.service << 'EOF'
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name>Smart C AI Dashboard</name>
  <service>
    <type>_http._tcp</type>
    <port>8080</port>
    <txt-record>path=/</txt-record>
    <txt-record>desc=Smart C AI Web Settings</txt-record>
  </service>
</service-group>
EOF

# Enable and restart avahi-daemon
echo "🔄 Enabling avahi-daemon..."
systemctl enable avahi-daemon
systemctl restart avahi-daemon

# Verify
sleep 2
if systemctl is-active --quiet avahi-daemon; then
    echo ""
    echo "✅ mDNS setup complete!"
    echo ""
    echo "You can now access Smart C AI at:"
    echo "   🌐 http://${HOSTNAME}.local:8080"
    echo ""
    echo "Note: Both your computer and the Pi must be on the same network."
    echo "      Windows users may need Bonjour Print Services installed."
else
    echo "❌ avahi-daemon failed to start"
    exit 1
fi
