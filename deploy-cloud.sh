#!/bin/bash
# Deploy Smart C Cloud Server to VPS
# Usage: ./deploy.sh

set -e

SERVER="root@116.118.2.38"
REMOTE_PATH="/www/wwwroot/0nline.vn"
LOCAL_PATH="cloud-server"

echo "📦 Deploying Smart C Cloud Server..."

# Create tarball of cloud-server
echo "📁 Creating archive..."
tar -czf /tmp/cloud-server.tar.gz -C . cloud-server

# Upload to server
echo "📤 Uploading to server..."
scp /tmp/cloud-server.tar.gz $SERVER:/tmp/

# Execute remote commands
echo "🚀 Installing on server..."
ssh $SERVER << 'ENDSSH'
cd /www/wwwroot/0nline.vn

# Backup existing if any
if [ -d "cloud-server" ]; then
    mv cloud-server cloud-server.bak.$(date +%Y%m%d_%H%M%S)
fi

# Extract new version
tar -xzf /tmp/cloud-server.tar.gz
cd cloud-server

# Install PM2 globally if not exists
npm install -g pm2 2>/dev/null || true

# Install dependencies
npm install

# Create .env if not exists
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env from example"
fi

# Stop existing if running
pm2 stop smartc-cloud 2>/dev/null || true
pm2 delete smartc-cloud 2>/dev/null || true

# Start with PM2
pm2 start index.js --name smartc-cloud
pm2 save

echo "✅ Deployment complete!"
pm2 status
ENDSSH

echo "🎉 Done! Server running at https://0nline.vn"
