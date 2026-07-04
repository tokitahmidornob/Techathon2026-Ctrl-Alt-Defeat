const API_BASE = 'http://localhost:8000/api';

const FAN_WATTAGE = 60;
const LIGHT_WATTAGE = 15;
const ANOMALY_THRESHOLD_MS = 2 * 60 * 60 * 1000; // 2 hours

// Device SVG Icons
const icons = {
    Fan: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.827 16.379a6.082 6.082 0 0 1-8.618-7.002l5.412 1.45a6.082 6.082 0 0 1 7.002-8.618l-1.45 5.413a6.082 6.082 0 0 1 8.617 7.002l-5.412-1.45a6.082 6.082 0 0 1-7.002 8.618l1.45-5.413z"></path>
            <circle cx="12" cy="12" r="2"></circle>
          </svg>`,
    Light: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2v1"/>
              <path d="M12 7a5 5 0 1 0 5 5c0 1.28-.56 2.45-1.5 3.2L15 16H9l-.5-.8A5 5 0 0 1 12 7z"/>
            </svg>`
};

let isConnected = true;
let currentDevices = [];

async function fetchStatus() {
    try {
        const [statusRes, usageRes, logsRes] = await Promise.all([
            fetch(`${API_BASE}/status`),
            fetch(`${API_BASE}/usage/total`),
            fetch(`${API_BASE}/eco/logs`)
        ]);

        if (!statusRes.ok || !usageRes.ok || !logsRes.ok) throw new Error('Network response was not ok');

        const statusData = await statusRes.json();
        const usageData = await usageRes.json();
        const logsData = await logsRes.json();
        
        handleConnectionRestored();
        processData(statusData.devices, usageData, logsData);
    } catch (error) {
        console.error('Error fetching API:', error);
        handleConnectionDropped();
    }
}

function processData(devices, usageData, logsData) {
    currentDevices = devices;
    let totalLoad = 0;
    const roomLoads = {};
    const now = new Date();

    devices.forEach(dev => {
        const wattage = dev.type === 'Fan' ? FAN_WATTAGE : LIGHT_WATTAGE;
        
        if (dev.is_on) {
            totalLoad += wattage;
            roomLoads[dev.room] = (roomLoads[dev.room] || 0) + wattage;
        } else {
            roomLoads[dev.room] = roomLoads[dev.room] || 0;
        }

        updateDeviceDOM(dev, wattage);
    });

    // Update Office Totals
    document.getElementById('total-power').textContent = `${totalLoad} W`;
    
    // Update Projected Cost
    if (usageData && usageData.projected_daily_cost_bdt !== undefined) {
        document.getElementById('projected-cost').textContent = `${usageData.projected_daily_cost_bdt.toFixed(2)} BDT`;
    }
    
    // Update Room Powers
    for (const [room, load] of Object.entries(roomLoads)) {
        const roomIdStr = room.replace(/\s+/g, '-');
        const powerEl = document.getElementById(`power-${roomIdStr}`);
        if (powerEl) {
            powerEl.textContent = `${load} W`;
        }
    }

    // Update Eco Logs Feed
    updateEcoLogsDOM(logsData ? logsData.logs : []);
}

function updateDeviceDOM(dev, wattage) {
    const roomIdStr = dev.room.replace(/\s+/g, '-');
    const container = document.getElementById(`devices-${roomIdStr}`);
    if (!container) return;

    let deviceEl = document.getElementById(`device-${dev.id}`);
    
    // Lazy render device cards on first pass
    if (!deviceEl) {
        deviceEl = document.createElement('div');
        deviceEl.id = `device-${dev.id}`;
        
        const iconSvg = dev.type === 'Fan' ? icons.Fan : icons.Light;
        
        deviceEl.innerHTML = `
            <div class="device-icon-wrapper">
                ${iconSvg}
            </div>
            <div class="device-info">
                <span class="device-name">${dev.id}</span>
                <span class="device-wattage">${wattage}W</span>
            </div>
        `;
        container.appendChild(deviceEl);
    }
    
    // Class assignment handles all CSS animations and colors smoothly
    if (dev.is_on) {
        deviceEl.className = `device-card type-${dev.type} active`;
    } else {
        deviceEl.className = `device-card type-${dev.type} off`;
    }
}

let shownLogs = new Set();

function updateEcoLogsDOM(logs) {
    const container = document.getElementById('eco-logs-container');
    
    if (!logs || logs.length === 0) {
        return;
    }

    // Process from oldest to newest to ensure multiple new logs appear in correct order when prepended
    for (let i = logs.length - 1; i >= 0; i--) {
        const log = logs[i];
        if (!shownLogs.has(log)) {
            shownLogs.add(log);
            
            // Remove the all-clear message if it exists
            const allClear = container.querySelector('.all-clear');
            if (allClear) {
                allClear.remove();
            }
            
            const logEl = document.createElement('div');
            logEl.className = 'eco-log-card';
            logEl.innerHTML = log;
            logEl.style.transition = 'opacity 0.5s ease-out';
            logEl.style.opacity = '1';
            
            container.prepend(logEl);
            
            setTimeout(() => {
                logEl.style.opacity = '0';
                setTimeout(() => {
                    if (logEl.parentNode) {
                        logEl.remove();
                    }
                }, 500);
            }, 5000);
        }
    }
}

function handleConnectionDropped() {
    if (!isConnected) return;
    isConnected = false;
    const banner = document.getElementById('connection-banner');
    if (banner) banner.classList.remove('hidden');
}

function handleConnectionRestored() {
    if (!isConnected) {
        isConnected = true;
        const banner = document.getElementById('connection-banner');
        if (banner) banner.classList.add('hidden');
    }
}

// Initial fetch and start asynchronous polling engine
fetchStatus();
setInterval(fetchStatus, 2000);

// Manual Override Logic
const roomSelect = document.getElementById('override-room');
const deviceSelect = document.getElementById('override-device');
const overrideBtn = document.getElementById('override-btn');

roomSelect.addEventListener('change', (e) => {
    const room = e.target.value;
    deviceSelect.innerHTML = '<option value="">Select Device</option>';
    if (room) {
        const roomDevices = currentDevices.filter(d => d.room === room);
        roomDevices.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.id;
            opt.textContent = `${d.id} (${d.type})`;
            deviceSelect.appendChild(opt);
        });
        deviceSelect.disabled = false;
    } else {
        deviceSelect.disabled = true;
        overrideBtn.disabled = true;
    }
});

deviceSelect.addEventListener('change', (e) => {
    overrideBtn.disabled = !e.target.value;
});

overrideBtn.addEventListener('click', async () => {
    const room = roomSelect.value;
    const deviceId = deviceSelect.value;
    if (!room || !deviceId) return;

    try {
        const response = await fetch(`${API_BASE}/toggle/${encodeURIComponent(room)}/${encodeURIComponent(deviceId)}`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('Failed to toggle device');
    } catch (error) {
        console.error('Error toggling device:', error);
        alert('Failed to toggle device');
    }
});
