/**
 * Smart C AI - Database Module (SQLite)
 * ======================================
 * Persistent storage for devices, logs, etc.
 */

const Database = require('better-sqlite3');
const path = require('path');

// Database file location
const DB_PATH = process.env.DB_PATH || path.join(__dirname, 'data', 'smartc.db');

// Ensure data directory exists
const fs = require('fs');
const dataDir = path.dirname(DB_PATH);
if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
}

// Initialize database
const db = new Database(DB_PATH);

// Enable WAL mode for better performance
db.pragma('journal_mode = WAL');

// ========== Create Tables ==========
db.exec(`
    -- Devices table
    CREATE TABLE IF NOT EXISTS devices (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        ip TEXT,
        version TEXT,
        status TEXT DEFAULT 'offline',
        last_seen DATETIME,
        config TEXT,
        system_info TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Device logs table
    CREATE TABLE IF NOT EXISTS device_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT NOT NULL,
        type TEXT,
        message TEXT,
        data TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (device_id) REFERENCES devices(id)
    );
    
    -- Commands history
    CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT NOT NULL,
        command TEXT NOT NULL,
        params TEXT,
        result TEXT,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        completed_at DATETIME,
        FOREIGN KEY (device_id) REFERENCES devices(id)
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
    CREATE INDEX IF NOT EXISTS idx_logs_device ON device_logs(device_id);
    CREATE INDEX IF NOT EXISTS idx_commands_device ON commands(device_id);
`);

console.log('📦 Database initialized:', DB_PATH);

// ========== Device Functions ==========

const deviceQueries = {
    upsert: db.prepare(`
        INSERT INTO devices (id, name, ip, version, status, last_seen, config, system_info, updated_at)
        VALUES (@id, @name, @ip, @version, @status, @last_seen, @config, @system_info, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            name = @name,
            ip = @ip,
            version = @version,
            status = @status,
            last_seen = @last_seen,
            config = COALESCE(@config, config),
            system_info = @system_info,
            updated_at = CURRENT_TIMESTAMP
    `),

    getById: db.prepare('SELECT * FROM devices WHERE id = ?'),

    getAll: db.prepare('SELECT * FROM devices ORDER BY last_seen DESC'),

    updateStatus: db.prepare(`
        UPDATE devices SET status = ?, last_seen = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    `),

    updateSystemInfo: db.prepare(`
        UPDATE devices SET system_info = ?, last_seen = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    `),

    markOffline: db.prepare(`
        UPDATE devices SET status = 'offline', updated_at = CURRENT_TIMESTAMP
        WHERE status = 'online' AND last_seen < datetime('now', '-60 seconds')
    `)
};

// ========== Log Functions ==========

const logQueries = {
    insert: db.prepare(`
        INSERT INTO device_logs (device_id, type, message, data)
        VALUES (?, ?, ?, ?)
    `),

    getByDevice: db.prepare(`
        SELECT * FROM device_logs 
        WHERE device_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    `),

    cleanup: db.prepare(`
        DELETE FROM device_logs 
        WHERE created_at < datetime('now', '-7 days')
    `)
};

// ========== Command Functions ==========

const commandQueries = {
    insert: db.prepare(`
        INSERT INTO commands (device_id, command, params, status)
        VALUES (?, ?, ?, 'pending')
    `),

    complete: db.prepare(`
        UPDATE commands SET status = 'completed', result = ?, completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    `),

    getByDevice: db.prepare(`
        SELECT * FROM commands 
        WHERE device_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    `)
};

// ========== Export Functions ==========

module.exports = {
    db,

    // Device operations
    upsertDevice: (device) => {
        return deviceQueries.upsert.run({
            id: device.id,
            name: device.name || `SmartC-${device.id.slice(0, 8)}`,
            ip: device.ip || null,
            version: device.version || null,
            status: device.status || 'online',
            last_seen: new Date().toISOString(),
            config: device.config ? JSON.stringify(device.config) : null,
            system_info: device.system ? JSON.stringify(device.system) : null
        });
    },

    getDevice: (id) => {
        const row = deviceQueries.getById.get(id);
        if (row) {
            row.config = row.config ? JSON.parse(row.config) : {};
            row.system = row.system_info ? JSON.parse(row.system_info) : {};
        }
        return row;
    },

    getAllDevices: () => {
        return deviceQueries.getAll.all().map(row => ({
            ...row,
            config: row.config ? JSON.parse(row.config) : {},
            system: row.system_info ? JSON.parse(row.system_info) : {}
        }));
    },

    updateDeviceStatus: (id, status) => {
        return deviceQueries.updateStatus.run(status, id);
    },

    updateDeviceSystem: (id, systemInfo) => {
        return deviceQueries.updateSystemInfo.run(JSON.stringify(systemInfo), id);
    },

    markOfflineDevices: () => {
        return deviceQueries.markOffline.run();
    },

    // Log operations
    addLog: (deviceId, type, message, data = null) => {
        return logQueries.insert.run(
            deviceId,
            type,
            message,
            data ? JSON.stringify(data) : null
        );
    },

    getDeviceLogs: (deviceId, limit = 50) => {
        return logQueries.getByDevice.all(deviceId, limit).map(row => ({
            ...row,
            data: row.data ? JSON.parse(row.data) : null
        }));
    },

    cleanupOldLogs: () => {
        return logQueries.cleanup.run();
    },

    // Command operations
    addCommand: (deviceId, command, params = null) => {
        return commandQueries.insert.run(
            deviceId,
            command,
            params ? JSON.stringify(params) : null
        );
    },

    completeCommand: (commandId, result) => {
        return commandQueries.complete.run(
            result ? JSON.stringify(result) : null,
            commandId
        );
    },

    getDeviceCommands: (deviceId, limit = 20) => {
        return commandQueries.getByDevice.all(deviceId, limit).map(row => ({
            ...row,
            params: row.params ? JSON.parse(row.params) : null,
            result: row.result ? JSON.parse(row.result) : null
        }));
    }
};
