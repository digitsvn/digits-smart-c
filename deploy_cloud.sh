#!/bin/bash
HOST="116.118.2.38"
USER="root"
DIR="/root/cloud-server"

echo "🚀 Đang deploy lên Cloud Server ($HOST)..."

# 1. Copy file server
echo "📂 Uploading server files..."
scp cloud-server/index.js cloud-server/db.js cloud-server/package.json $USER@$HOST:$DIR/

# 2. Copy dashboard
echo "📂 Uploading dashboard..."
scp -r cloud-server/dashboard $USER@$HOST:$DIR/

# 3. Install dependencies & Restart
echo "🔄 Updating dependencies and restarting service..."
ssh $USER@$HOST "cd $DIR && npm install && pm2 restart smartc-cloud"

echo "✅ Deploy hoàn tất!"
