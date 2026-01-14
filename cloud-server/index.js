/**
 * Smart C AI - Cloud Management Server
 * =====================================
 * WebSocket server for device communication
 * REST API for dashboard
 * 
 * Deploy to: https://0nline.vn
 */

require('dotenv').config();
const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');
const path = require('path');

const fs = require('fs');
const multer = require('multer');

// Database
const db = require('./db');

// Configuration
const PORT = process.env.PORT || 3000;
const API_SECRET = process.env.API_SECRET || 'smartc-secret-key-change-me';

// Configure Multer for image uploads
const storage = multer.diskStorage({
    destination: function (req, file, cb) {
        const dir = path.join(__dirname, 'uploads', 'images');
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
        cb(null, dir);
    },
    filename: function (req, file, cb) {
        // Keep original extension, add timestamp to prevent dupes
        const ext = path.extname(file.originalname);
        const name = path.basename(file.originalname, ext).replace(/[^a-zA-Z0-9]/g, '_');
        cb(null, `${name}_${Date.now()}${ext}`);
    }
});

const upload = multer({
    storage: storage,
    limits: { fileSize: 10 * 1024 * 1024 }, // 10MB limit
    fileFilter: (req, file, cb) => {
        if (file.mimetype.startsWith('image/')) {
            cb(null, true);
        } else {
            cb(new Error('Only images are allowed'));
        }
    }
});

const app = express();
const server = http.createServer(app);

// WebSocket server
const wss = new WebSocket.Server({ server, path: '/ws/device' });

// ========== Device Store ==========
// In-memory cache for screenshots (not persisted - too large)
const deviceScreenshots = new Map(); // deviceId -> {image, timestamp}
// WebSocket connections (runtime only)
const deviceConnections = new Map(); // deviceId -> ws connection

// ========== Middleware ==========
app.use(cors());
app.use(express.json({ limit: '10mb' })); // For screenshot uploads
app.use(express.static(path.join(__dirname, 'dashboard')));
app.use('/uploads', express.static(path.join(__dirname, 'uploads'))); // Serve uploaded files

// Auth Configuration
const USERS = {
    'hoainguyen': '12345678#'
};
const TOKENS = new Map(); // token -> username

// Auth Middleware
const auth = (req, res, next) => {
    // Public routes
    if (req.path === '/api/login' || req.path === '/login.html' || req.path === '/health') {
        return next();
    }

    // Check header token
    const token = req.headers['authorization'];
    if (token && TOKENS.has(token)) {
        req.user = TOKENS.get(token);
        return next();
    }

    // Check cookie/query (for static files/websocket if needed)
    // For now, API only

    res.status(401).json({ error: 'Unauthorized' });
};

// ========== Auth API ==========

app.post('/api/login', (req, res) => {
    const { username, password } = req.body;

    if (USERS[username] && USERS[username] === password) {
        const token = uuidv4();
        TOKENS.set(token, username);
        res.json({ token, username });
    } else {
        res.status(401).json({ error: 'Invalid credentials' });
    }
});

app.post('/api/logout', (req, res) => {
    const token = req.headers['authorization'];
    if (token) {
        TOKENS.delete(token);
    }
    res.json({ success: true });
});

// Apply Auth to specific routes or globally (careful with static files)
// For simplicity: dashboard HTML does client-side check, 
// APIs are protected
app.use('/api/devices', auth);

// ========== WebSocket Handlers ==========
wss.on('connection', (ws, req) => {
    console.log('📱 New device connection');
    // Device auth logic could be added here (e.g. check API Key)

    let deviceId = null;

    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);

            switch (data.type) {
                case 'register':
                    // Device registration
                    deviceId = data.device_id || uuidv4();

                    // Save to database
                    db.upsertDevice({
                        id: deviceId,
                        name: data.name || `SmartC-${deviceId.slice(0, 8)}`,
                        ip: data.ip || 'Unknown',
                        version: data.version || 'Unknown',
                        status: 'online',
                        config: data.config || {},
                        system: data.system || {}
                    });

                    deviceConnections.set(deviceId, ws);

                    // Log registration
                    db.addLog(deviceId, 'connect', 'Device connected');

                    ws.send(JSON.stringify({
                        type: 'registered',
                        device_id: deviceId,
                        message: 'Device registered successfully'
                    }));

                    console.log(`✅ Device registered: ${deviceId}`);
                    break;

                case 'heartbeat':
                    // Update device status in database
                    if (deviceId) {
                        db.upsertDevice({
                            id: deviceId,
                            name: null, // Keep existing
                            ip: data.ip,
                            version: null,
                            status: 'online',
                            system: data.system || {}
                        });
                    }
                    break;

                case 'screenshot':
                    // Store screenshot in memory cache (not DB - too large)
                    if (deviceId) {
                        deviceScreenshots.set(deviceId, {
                            image: data.image,
                            timestamp: new Date()
                        });
                    }
                    break;

                case 'config_updated':
                    // Device confirmed config update
                    console.log(`⚙️ Device ${deviceId} config updated`);
                    db.addLog(deviceId, 'config', 'Config updated');
                    break;

                case 'command_result':
                    // Result of command execution
                    console.log(`📋 Command result from ${deviceId}:`, data.command);
                    db.addLog(deviceId, 'command', `Command result: ${data.command}`, data.result);

                    if (data.command_id) {
                        try {
                            const resultStr = JSON.stringify(data.result);
                            db.db.prepare('UPDATE commands SET status = ?, result = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?')
                                .run('completed', resultStr, data.command_id);
                        } catch (e) {
                            console.error('Failed to update command status:', e);
                        }
                    }
                    break;

                default:
                    console.log(`Unknown message type: ${data.type}`);
            }
        } catch (e) {
            console.error('Error processing message:', e);
        }
    });

    ws.on('close', () => {
        if (deviceId) {
            console.log(`❌ Device disconnected: ${deviceId}`);
            deviceConnections.delete(deviceId);
            db.updateDeviceStatus(deviceId, 'offline');
            db.addLog(deviceId, 'disconnect', 'Device disconnected');
        }
    });

    ws.on('error', (error) => {
        console.error('WebSocket error:', error);
    });
});


// ========== REST API ==========

// Get all devices
app.get('/api/devices', (req, res) => {
    const deviceList = db.getAllDevices().map(d => ({
        id: d.id,
        name: d.name,
        ip: d.ip,
        version: d.version,
        status: deviceConnections.has(d.id) ? 'online' : d.status,
        lastSeen: d.last_seen,
        system: d.system
    }));
    res.json({ devices: deviceList });
});

// Get single device
app.get('/api/devices/:id', (req, res) => {
    const device = db.getDevice(req.params.id);
    if (!device) {
        return res.status(404).json({ error: 'Device not found' });
    }
    device.status = deviceConnections.has(device.id) ? 'online' : device.status;
    res.json(device);
});

// Get device screenshot
app.get('/api/devices/:id/screenshot', (req, res) => {
    const screenshot = deviceScreenshots.get(req.params.id);
    if (!screenshot) {
        return res.status(404).json({ error: 'No screenshot available' });
    }
    res.json({
        image: screenshot.image,
        timestamp: screenshot.timestamp
    });
});

// Request screenshot from device
app.post('/api/devices/:id/screenshot/request', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    ws.send(JSON.stringify({ type: 'capture_screenshot' }));
    res.json({ message: 'Screenshot requested' });
});

// Send command to device
app.post('/api/devices/:id/command', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    const { command, params } = req.body;

    ws.send(JSON.stringify({
        type: 'command',
        command: command,
        params: params || {}
    }));

    res.json({ message: `Command '${command}' sent to device` });
});

// Update device config
app.post('/api/devices/:id/config', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    const { config } = req.body;

    ws.send(JSON.stringify({
        type: 'update_config',
        config: config
    }));

    res.json({ message: 'Config update sent to device' });
});

// Get device full config
app.get('/api/devices/:id/config', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);
    const device = devices.get(deviceId);

    if (!device) {
        return res.status(404).json({ error: 'Device not found' });
    }

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    // Request config from device
    ws.send(JSON.stringify({ type: 'get_config' }));

    // Return cached config for now
    res.json({
        config: device.config || {},
        message: 'Config requested from device'
    });
});

// ========== Remote Settings API ==========

// Get Audio devices
app.post('/api/devices/:id/audio/devices', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    ws.send(JSON.stringify({ type: 'get_audio_devices' }));
    res.json({ message: 'Audio devices requested' });
});

// Set Audio device
app.post('/api/devices/:id/audio/set', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    const { input_device, output_device } = req.body;

    ws.send(JSON.stringify({
        type: 'command',
        command: 'set_audio',
        params: { input_device, output_device }
    }));

    res.json({ message: 'Audio settings sent' });
});

// Get video list
app.post('/api/devices/:id/videos', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    ws.send(JSON.stringify({ type: 'get_videos' }));
    res.json({ message: 'Videos requested' });
});

// Set video background (Legacy)
app.post('/api/devices/:id/video/set', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    const { video_path } = req.body;

    ws.send(JSON.stringify({
        type: 'command',
        command: 'set_video',
        params: { video_path }
    }));

    res.json({ message: 'Video setting sent' });
});

// Generic Command Endpoint
app.post('/api/devices/:id/command', auth, (req, res) => {
    const deviceId = req.params.id;
    const { type, data } = req.body;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    // Create command record
    const result = db.addCommand(deviceId, type, data);
    const commandId = result.lastInsertRowid;

    // Send to device
    ws.send(JSON.stringify({
        type: 'command',
        command: type,
        params: data,
        command_id: commandId
    }));

    res.json({ success: true, commandId: commandId });
});

// Check Command Status
app.get('/api/commands/:id', auth, (req, res) => {
    const cmdId = req.params.id;
    const cmd = db.db.prepare('SELECT * FROM commands WHERE id = ?').get(cmdId);

    if (!cmd) {
        return res.status(404).json({ error: 'Command not found' });
    }
    res.json(cmd);
});

// Set Slide (New)
app.post('/api/devices/:id/slide/set', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    const { type, urls, interval } = req.body; // type: 'video' | 'slide'

    ws.send(JSON.stringify({
        type: 'command',
        command: 'set_background_mode',
        params: { type, urls: urls || [], interval: interval || 5000 }
    }));

    res.json({ message: 'Background settings sent' });
});

// Upload image
app.post('/api/uploads', auth, upload.single('image'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ error: 'No file uploaded' });
    }

    // Construct full URL
    const protocol = req.protocol;
    const host = req.get('host');
    const url = `${protocol}://${host}/uploads/images/${req.file.filename}`;

    res.json({
        success: true,
        message: 'Upload successful',
        url: url,
        filename: req.file.filename
    });
});

// List uploaded images
app.get('/api/images', auth, (req, res) => {
    const dir = path.join(__dirname, 'uploads', 'images');

    if (!fs.existsSync(dir)) {
        return res.json({ images: [] });
    }

    fs.readdir(dir, (err, files) => {
        if (err) {
            return res.status(500).json({ error: 'Failed to list images' });
        }

        const protocol = req.protocol;
        const host = req.get('host');

        const images = files
            .filter(file => /\.(jpg|jpeg|png|gif|webp)$/i.test(file))
            .map(file => ({
                filename: file,
                url: `${protocol}://${host}/uploads/images/${file}`,
                created: fs.statSync(path.join(dir, file)).birthtime
            }))
            .sort((a, b) => b.created - a.created);

        res.json({ images });
    });
});


// Get WiFi networks
app.post('/api/devices/:id/wifi/scan', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    ws.send(JSON.stringify({ type: 'wifi_scan' }));
    res.json({ message: 'WiFi scan requested' });
});

// Connect to WiFi
app.post('/api/devices/:id/wifi/connect', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    const { ssid, password } = req.body;

    ws.send(JSON.stringify({
        type: 'command',
        command: 'wifi_connect',
        params: { ssid, password }
    }));

    res.json({ message: 'WiFi connect command sent' });
});

// Get saved WiFi networks
app.get('/api/devices/:id/wifi/saved', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    ws.send(JSON.stringify({ type: 'get_saved_wifi' }));
    res.json({ message: 'Saved WiFi requested' });
});

// Wake Word settings
app.post('/api/devices/:id/wakeword', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    const { enabled, threshold } = req.body;

    ws.send(JSON.stringify({
        type: 'command',
        command: 'set_wakeword',
        params: { enabled, threshold }
    }));

    res.json({ message: 'Wakeword settings sent' });
});

// System settings (language, URLs)
app.post('/api/devices/:id/system', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    const settings = req.body;

    ws.send(JSON.stringify({
        type: 'command',
        command: 'set_system',
        params: settings
    }));

    res.json({ message: 'System settings sent' });
});

// Test microphone
app.post('/api/devices/:id/test/mic', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    ws.send(JSON.stringify({
        type: 'command',
        command: 'test_mic',
        params: {}
    }));

    res.json({ message: 'Mic test started' });
});

// Test speaker
app.post('/api/devices/:id/test/speaker', (req, res) => {
    const deviceId = req.params.id;
    const ws = deviceConnections.get(deviceId);

    if (!ws) {
        return res.status(404).json({ error: 'Device not connected' });
    }

    const { hdmi_audio } = req.body;

    ws.send(JSON.stringify({
        type: 'command',
        command: 'test_speaker',
        params: { hdmi_audio: hdmi_audio || false }
    }));

    res.json({ message: 'Speaker test started' });
});

// Placeholder for images API to fix Dashboard error
app.get('/api/images', (req, res) => {
    res.json({ images: [] });
});

// Get device health
app.get('/api/devices/:id/health', (req, res) => {
    const device = db.getDevice(req.params.id);
    if (!device) {
        return res.status(404).json({ error: 'Device not found' });
    }
    res.json({
        status: deviceConnections.has(device.id) ? 'online' : device.status,
        lastSeen: device.last_seen,
        system: device.system
    });
});

// Get device logs
app.get('/api/devices/:id/logs', (req, res) => {
    const limit = parseInt(req.query.limit) || 50;
    const logs = db.getDeviceLogs(req.params.id, limit);
    res.json({ logs });
});

// Dashboard route
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'dashboard', 'index.html'));
});

// Health check for server
app.get('/health', (req, res) => {
    const allDevices = db.getAllDevices();
    res.json({
        status: 'ok',
        devices_connected: deviceConnections.size,
        devices_registered: allDevices.length,
        uptime: process.uptime()
    });
});

// ========== Cleanup ==========
// Mark devices as offline and cleanup logs
setInterval(() => {
    // Mark disconnected devices as offline in DB
    db.markOfflineDevices();

    // Cleanup old logs (older than 7 days)
    db.cleanupOldLogs();
}, 30000);

// ========== Start Server ==========
server.listen(PORT, () => {
    console.log('╔════════════════════════════════════════╗');
    console.log('║   Smart C AI - Cloud Management Server ║');
    console.log('╠════════════════════════════════════════╣');
    console.log(`║   🌐 HTTP:  http://localhost:${PORT}        ║`);
    console.log(`║   🔌 WS:    ws://localhost:${PORT}/ws/device ║`);
    console.log(`║   📦 DB:    SQLite (data/smartc.db)     ║`);
    console.log('╚════════════════════════════════════════╝');
});
