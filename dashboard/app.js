/**
 * MechMind AI — Telemetry & Diagnostics Frontend Logic (app.js)
 * Minimalist Monochrome Aesthetics, High-precision Chart.js, Ollama Copilot
 */

const API_BASE = window.location.origin.includes('5500') || window.location.origin.includes('3000') 
  ? 'http://localhost:8080' 
  : window.location.origin;

// State
let activeEquipmentId = 1;
let isSimulating = true;
let simInterval = null;

// Chart Instances
let vibrationChart = null;
let tempChart = null;

// Data Buffers
const MAX_DATA_POINTS = 30;
const timeLabels = [];
const vibXData = [];
const vibYData = [];
const vibZData = [];
const vibMagData = [];
const tempData = [];
const soundData = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  initCharts();
  setupEventListeners();
  checkSystemHealth();
  startSimulation();
  fetchAlerts();

  // Polling for health and alert updates
  setInterval(() => {
    fetchAlerts();
    checkSystemHealth();
  }, 5000);
});

// Setup Minimalist Chart.js
function initCharts() {
  const chartFont = { family: "'JetBrains Mono', monospace", size: 10 };
  const gridColor = 'rgba(255, 255, 255, 0.04)';

  // 1. Vibration Waveform (3-Axis + Magnitude)
  const ctxVib = document.getElementById('vibrationChart').getContext('2d');
  vibrationChart = new Chart(ctxVib, {
    type: 'line',
    data: {
      labels: timeLabels,
      datasets: [
        {
          label: 'Magnitude',
          data: vibMagData,
          borderColor: '#ffffff',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.3,
          order: 1
        },
        {
          label: 'X-Axis',
          data: vibXData,
          borderColor: '#d4d4d8',
          borderWidth: 1.2,
          pointRadius: 0,
          tension: 0.3,
          order: 2
        },
        {
          label: 'Y-Axis',
          data: vibYData,
          borderColor: '#a1a1aa',
          borderWidth: 1.2,
          pointRadius: 0,
          tension: 0.3,
          order: 3
        },
        {
          label: 'Z-Axis',
          data: vibZData,
          borderColor: '#71717a',
          borderWidth: 1.2,
          pointRadius: 0,
          tension: 0.3,
          order: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: { 
        legend: { display: false },
        tooltip: {
          backgroundColor: '#111114',
          titleFont: chartFont,
          bodyFont: chartFont,
          borderColor: '#2f2f36',
          borderWidth: 1,
          padding: 8
        }
      },
      scales: {
        x: { 
          grid: { color: gridColor }, 
          ticks: { font: chartFont, color: '#71717a', maxTicksLimit: 8 } 
        },
        y: {
          grid: { color: gridColor },
          ticks: { font: chartFont, color: '#71717a' },
          suggestedMin: 0,
          suggestedMax: 6.0
        }
      }
    }
  });

  // 2. Thermal Profile & Acoustic Trend History
  const ctxTemp = document.getElementById('tempChart').getContext('2d');
  tempChart = new Chart(ctxTemp, {
    type: 'line',
    data: {
      labels: timeLabels,
      datasets: [
        {
          label: 'Temp (°C)',
          data: tempData,
          borderColor: '#ffffff',
          backgroundColor: 'rgba(255, 255, 255, 0.03)',
          fill: true,
          borderWidth: 1.8,
          pointRadius: 0,
          tension: 0.35,
          yAxisID: 'yTemp'
        },
        {
          label: 'Sound (dB)',
          data: soundData,
          borderColor: '#a1a1aa',
          borderWidth: 1.2,
          borderDash: [3, 3],
          pointRadius: 0,
          tension: 0.35,
          yAxisID: 'ySound'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          align: 'end',
          labels: { font: chartFont, color: '#a1a1aa', boxWidth: 10, padding: 10 }
        },
        tooltip: {
          backgroundColor: '#111114',
          titleFont: chartFont,
          bodyFont: chartFont,
          borderColor: '#2f2f36',
          borderWidth: 1,
          padding: 8
        }
      },
      scales: {
        x: { 
          grid: { color: gridColor }, 
          ticks: { font: chartFont, color: '#71717a', maxTicksLimit: 8 } 
        },
        yTemp: {
          position: 'left',
          grid: { color: gridColor },
          ticks: { font: chartFont, color: '#e4e4e7' },
          suggestedMin: 40,
          suggestedMax: 120
        },
        ySound: {
          position: 'right',
          grid: { display: false },
          ticks: { font: chartFont, color: '#71717a' },
          suggestedMin: 40,
          suggestedMax: 130
        }
      }
    }
  });
}

// Push New Telemetry
function pushTelemetry(temp, ax, ay, az, mag, sound) {
  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });

  timeLabels.push(timeStr);
  vibXData.push(ax);
  vibYData.push(ay);
  vibZData.push(az);
  vibMagData.push(mag);
  tempData.push(temp);
  soundData.push(sound);

  if (timeLabels.length > MAX_DATA_POINTS) {
    timeLabels.shift();
    vibXData.shift();
    vibYData.shift();
    vibZData.shift();
    vibMagData.shift();
    tempData.shift();
    soundData.shift();
  }

  // Update Numerical Metric Displays
  document.getElementById('tempVal').textContent = temp.toFixed(1);
  document.getElementById('vibVal').textContent = mag.toFixed(2);
  document.getElementById('soundVal').textContent = sound.toFixed(1);

  document.getElementById('axisReadout').textContent = `X: ${ax.toFixed(1)} · Y: ${ay.toFixed(1)} · Z: ${az.toFixed(1)}`;
  document.getElementById('lastUpdated').textContent = `UPDATED ${timeStr}`;

  // Temp Status Badges & Meters
  const tempBadge = document.getElementById('tempBadge');
  const tempBar = document.getElementById('tempBar');
  const tempPct = Math.min(100, Math.max(5, (temp / 120) * 100));
  tempBar.style.width = `${tempPct}%`;

  if (temp >= 105) {
    tempBadge.className = 'stat-badge critical';
    tempBadge.textContent = 'CRITICAL';
  } else if (temp >= 85) {
    tempBadge.className = 'stat-badge warning';
    tempBadge.textContent = 'WARNING';
  } else {
    tempBadge.className = 'stat-badge normal';
    tempBadge.textContent = 'NORMAL';
  }

  // Vibration Status Badge & Meter
  const vibBadge = document.getElementById('vibBadge');
  const vibBar = document.getElementById('vibBar');
  const vibPct = Math.min(100, Math.max(5, (mag / 8.0) * 100));
  vibBar.style.width = `${vibPct}%`;

  if (mag >= 8.0) {
    vibBadge.className = 'stat-badge critical';
    vibBadge.textContent = 'SEVERE SHOCK';
  } else if (mag >= 4.5) {
    vibBadge.className = 'stat-badge warning';
    vibBadge.textContent = 'ELEVATED';
  } else {
    vibBadge.className = 'stat-badge normal';
    vibBadge.textContent = 'OPTIMAL';
  }

  // Sound meter
  const soundBar = document.getElementById('soundBar');
  if (soundBar) {
    const soundPct = Math.min(100, Math.max(5, (sound / 130) * 100));
    soundBar.style.width = `${soundPct}%`;
  }

  // Refresh Charts
  vibrationChart.update();
  tempChart.update();
}

// Telemetry Simulation Loop
function startSimulation() {
  if (simInterval) clearInterval(simInterval);

  let baseTemp = 74.0;
  simInterval = setInterval(async () => {
    // Generate realistic engine telemetry with occasional harmonic fluctuation
    const tShift = (Math.random() - 0.48) * 0.5;
    baseTemp = Math.max(68, Math.min(96, baseTemp + tShift));

    const ax = +(1.1 + (Math.random() - 0.5) * 0.8).toFixed(2);
    const ay = +(0.8 + (Math.random() - 0.5) * 0.6).toFixed(2);
    const az = +(1.5 + (Math.random() - 0.5) * 0.9).toFixed(2);
    const mag = +Math.sqrt(ax * ax + ay * ay + az * az).toFixed(2);
    const sound = +(82.0 + Math.random() * 8.0).toFixed(1);

    pushTelemetry(baseTemp, ax, ay, az, mag, sound);

    // Forward simulated reading to backend DB
    const select = document.getElementById('equipmentSelect');
    const nodeId = select.options[select.selectedIndex].getAttribute('data-node') || 'NODE-001';

    try {
      await fetch(`${API_BASE}/api/sensors/data`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          node_id: nodeId,
          temperature: baseTemp,
          vibration_x: ax,
          vibration_y: ay,
          vibration_z: az,
          vibration_magnitude: mag,
          sound_level_db: sound
        })
      });
    } catch (e) {
      // Backend maybe offline
    }
  }, 2000);
}

// Backend & WhatsApp Bot Health Checks
async function checkSystemHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      document.getElementById('backendStatusText').textContent = 'ONLINE';
    }
  } catch (err) {
    document.getElementById('backendStatusText').textContent = 'CONNECTING';
  }

  // Check WhatsApp Bot Daemon on port 3001
  try {
    const waRes = await fetch('http://localhost:3001/health');
    if (waRes.ok) {
      const waData = await waRes.json();
      const statusText = waData.status === 'connected' ? 'CONNECTED' : 'ACTIVE (SCAN QR IN TERMINAL)';
      const modalEl = document.getElementById('botStatusModalText');
      if (modalEl) modalEl.textContent = `Bot daemon listening on port 3001: ${statusText}`;
      const pillDot = document.querySelector('#whatsappPill .status-dot');
      if (pillDot) pillDot.className = 'status-dot dot-active';
    }
  } catch (e) {
    const modalEl = document.getElementById('botStatusModalText');
    if (modalEl) modalEl.textContent = 'Bot daemon offline. Run command above to start.';
  }
}

// Fetch Alerts & Render Log Entries
async function fetchAlerts() {
  try {
    const res = await fetch(`${API_BASE}/api/alerts?limit=5`);
    if (!res.ok) return;
    const alerts = await res.json();
    const container = document.getElementById('alertsList');
    if (!alerts || alerts.length === 0) return;

    document.getElementById('alertCountBadge').textContent = `${alerts.length} RECENT`;
    container.innerHTML = alerts.map(a => {
      const sev = (a.severity || 'info').toLowerCase();
      const tag = sev === 'critical' ? 'CRIT' : (sev === 'warning' ? 'WARN' : 'INFO');
      const timeStr = a.time ? new Date(a.time).toLocaleTimeString() : 'RECENT';
      return `
        <div class="log-entry ${sev}">
          <div class="log-tag">${tag}</div>
          <div class="log-body">
            <div class="log-title">${a.type ? a.type.toUpperCase() : 'INCIDENT'} · ${sev.toUpperCase()}</div>
            <div class="log-detail">${a.message}</div>
            <div class="log-meta">${timeStr} · ${a.equipment || 'CAT 320'}</div>
          </div>
        </div>
      `;
    }).join('');
  } catch (e) {
    // ignore
  }
}

// Event Listeners & Chat Form
function setupEventListeners() {
  // Equipment Select
  document.getElementById('equipmentSelect').addEventListener('change', (e) => {
    activeEquipmentId = +e.target.value;
    const node = e.target.options[e.target.selectedIndex].getAttribute('data-node');
    document.getElementById('nodeIdLabel').textContent = `NODE: ${node}`;
  });

  // Sim Button Toggle
  const simBtn = document.getElementById('btnSimulate');
  simBtn.addEventListener('click', () => {
    isSimulating = !isSimulating;
    if (isSimulating) {
      simBtn.classList.add('active');
      startSimulation();
    } else {
      simBtn.classList.remove('active');
      if (simInterval) clearInterval(simInterval);
    }
  });

  // Sync DB Button
  document.getElementById('btnRefresh').addEventListener('click', async () => {
    try {
      const res = await fetch(`${API_BASE}/api/equipment/${activeEquipmentId}/readings?limit=20`);
      if (res.ok) {
        const readings = await res.json();
        readings.reverse().forEach(r => {
          pushTelemetry(r.temperature, 1.2, 0.9, 1.5, r.vibration, r.sound);
        });
      }
    } catch (e) {
      alert('Unable to connect to FastAPI backend on port 8080.');
    }
  });

  // Quick Prompt Chips
  document.querySelectorAll('.quick-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('aiInput').value = btn.getAttribute('data-prompt');
      document.getElementById('aiChatForm').dispatchEvent(new Event('submit'));
    });
  });

  // Diagnostic Chat Submission
  document.getElementById('aiChatForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('aiInput');
    const msg = input.value.trim();
    if (!msg) return;

    input.value = '';
    appendMessage('OPERATOR', msg, 'user-bubble');

    // Show processing indicator
    const typingId = appendMessage('MECHMIND ENGINE', 'Consulting diagnostic database & telemetry logs...', 'ai-bubble');

    try {
      const res = await fetch(`${API_BASE}/api/diagnose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone_number: '+2347010299562',
          message: msg,
          equipment_id: activeEquipmentId
        })
      });

      const data = await res.json();
      removeMessage(typingId);
      appendMessage('MECHMIND ENGINE', data.response || 'No diagnostic output returned.', 'ai-bubble');
    } catch (err) {
      removeMessage(typingId);
      appendMessage('MECHMIND ENGINE', 'Diagnostic API unreachable. Confirm FastAPI backend is active on port 8080.', 'ai-bubble');
    }
  });

  // Terminal Pairing Modal
  const modal = document.getElementById('qrModal');
  document.getElementById('openQrModalBtn').addEventListener('click', () => modal.classList.add('open'));
  document.getElementById('closeQrModalBtn').addEventListener('click', () => modal.classList.remove('open'));
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('open'); });
}

function appendMessage(sender, text, bubbleClass) {
  const container = document.getElementById('chatContainer');
  const div = document.createElement('div');
  const id = 'msg-' + Date.now();
  div.id = id;
  div.className = `console-message ${bubbleClass}`;
  
  const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' });
  div.innerHTML = `
    <div class="msg-meta">
      <span class="msg-author">${sender.toUpperCase()}</span>
      <span class="msg-timestamp">${time}</span>
    </div>
    <p>${text.replace(/\n/g, '<br>')}</p>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeMessage(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}
