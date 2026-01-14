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

// Configuration
const PORT = process.env.PORT || 3000;
const API_SECRET = process.env.API_SECRET || 'smartc-secret-key-change-me';

const app = express();
const server = http.createServer(app);

// WebSocket server
const wss = new WebSocket.Server({ server, path: '/ws/device' });

// ========== Device Store ==========
const devices = new Map(); // deviceId -> deviceInfo
const deviceConnections = new Map(); // deviceId -> ws connection

// ========== Middleware ==========
app.use(cors());
app.use(express.json({ limit: '10mb' })); // For screenshot uploads
app.use(express.static(path.join(__dirname, 'dashboard')));

// ========== WebSocket Handlers ==========
wss.on('connection', (ws, req) => {
    console.log('📱 New device connection');

    let deviceId = null;

    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);

            switch (data.type) {
                case 'register':
                    // Device registration
                    deviceId = data.device_id || uuidv4();
                    devices.set(deviceId, {
                        id: deviceId,
                        name: data.name || `SmartC-${deviceId.slice(0, 8)}`,
                        ip: data.ip || 'Unknown',
                        version: data.version || 'Unknown',
                        status: 'online',
                        lastSeen: new Date(),
                        config: data.config || {},
                        system: data.system || {}
                    });
                    deviceConnections.set(deviceId, ws);

                    ws.send(JSON.stringify({
                        type: 'registered',
                        device_id: deviceId,
                        message: 'Device registered successfully'
                    }));

                    console.log(`✅ Device registered: ${deviceId}`);
                    break;

                case 'heartbeat':
                    // Update device status
                    if (deviceId && devices.has(deviceId)) {
                        const device = devices.get(deviceId);
                        device.lastSeen = new Date();
                        device.status = 'online';
                        device.system = data.system || device.system;
                        device.ip = data.ip || device.ip;
                    }
                    break;

                case 'screenshot':
                    // Receive screenshot from device
                    if (deviceId && devices.has(deviceId)) {
                        const device = devices.get(deviceId);
                        device.screenshot = data.image; // Base64 image
                        device.screenshotTime = new Date();
                    }
                    break;

                case 'config_updated':
                    // Device confirmed config update
                    console.log(`⚙️ Device ${deviceId} config updated`);
                    break;

                case 'command_result':
                    // Result of command execution
                    console.log(`📋 Command result from ${deviceId}:`, data.result);
                    // Could broadcast to dashboard clients here
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
            if (devices.has(deviceId)) {
                devices.get(deviceId).status = 'offline';
            }
        }
    });

    ws.on('error', (error) => {
        console.error('WebSocket error:', error);
    });
});

// ========== REST API ==========

// Get all devices
app.get('/api/devices', (req, res) => {
    const deviceList = Array.from(devices.values()).map(d => ({
        id: d.id,
        name: d.name,
        ip: d.ip,
        version: d.version,
        status: d.status,
        lastSeen: d.lastSeen,
        system: d.system
    }));
    res.json({ devices: deviceList });
});

// Get single device
app.get('/api/devices/:id', (req, res) => {
    const device = devices.get(req.params.id);
    if (!device) {
        return res.status(404).json({ error: 'Device not found' });
    }
    res.json(device);
});

// Get device screenshot
app.get('/api/devices/:id/screenshot', (req, res) => {
    const device = devices.get(req.params.id);
    if (!device) {
        return res.status(404).json({ error: 'Device not found' });
    }
    if (!device.screenshot) {
        return res.status(404).json({ error: 'No screenshot available' });
    }
    res.json({
        image: device.screenshot,
        timestamp: device.screenshotTime
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

// Set video background
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

// Get device health
app.get('/api/devices/:id/health', (req, res) => {
    const device = devices.get(req.params.id);
    if (!device) {
        return res.status(404).json({ error: 'Device not found' });
    }
    res.json({
        status: device.status,
        lastSeen: device.lastSeen,
        system: device.system
    });
});

// Dashboard route
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'dashboard', 'index.html'));
});

// Health check for server
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        devices_connected: deviceConnections.size,
        devices_registered: devices.size,
        uptime: process.uptime()
    });
});

// ========== Cleanup ==========
// Mark devices as offline if not seen for 60 seconds
setInterval(() => {
    const now = new Date();
    devices.forEach((device, id) => {
        if (device.status === 'online' && !deviceConnections.has(id)) {
            device.status = 'offline';
        }
        // Mark as offline if no heartbeat for 60s
        if (device.lastSeen && (now - device.lastSeen) > 60000) {
            device.status = 'offline';
        }
    });
}, 30000);

// ========== Start Server ==========
server.listen(PORT, () => {
    console.log('╔════════════════════════════════════════╗');
    console.log('║   Smart C AI - Cloud Management Server ║');
    console.log('╠════════════════════════════════════════╣');
    console.log(`║   🌐 HTTP:  http://localhost:${PORT}        ║`);
    console.log(`║   🔌 WS:    ws://localhost:${PORT}/ws/device ║`);
    console.log('╚════════════════════════════════════════╝');
});
