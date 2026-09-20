/**
 * MechMind AI — Telemetry & Diagnostics Frontend Logic (app.js)
 * Minimalist Monochrome Aesthetics, High-precision Chart.js, Ollama Copilot
 */

const API_BASE = window.location.origin.includes('5500') || window.location.origin.includes('3000') 
  ? 'http://localhost:8080' 
  : window.location.origin;

// State
let activeEquipmentId = 1;
let pollInterval = null;
let lastReadingTimestamp = null;

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

document.addEventListener('DOMContentLoaded', () => {
  initCharts();
  setupEventListeners();
  setupMobileTabs();
  setupImageAttachment();
  checkSystemHealth();
  startRealDataPolling();
  fetchAlerts();

  // Set initial time
  const initTimeEl = document.getElementById('chatInitTime');
  if (initTimeEl) {
    initTimeEl.textContent = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' });
  }

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
          label: 'Temp (C)',
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

// Push New Telemetry (display only — no data generation)
function pushTelemetry(temp, ax, ay, az, mag, sound, timestamp) {
  let timeStr;
  if (timestamp) {
    timeStr = new Date(timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } else {
    timeStr = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

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

  // Update Live Values in Copilot Header
  const chatLiveTemp = document.getElementById('chatLiveTemp');
  const chatLiveVib = document.getElementById('chatLiveVib');
  if (chatLiveTemp) chatLiveTemp.textContent = `${temp.toFixed(1)}°C`;
  if (chatLiveVib) chatLiveVib.textContent = `${mag.toFixed(2)}g`;

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

// Real Data Polling — fetch actual sensor readings from the database
function startRealDataPolling() {
  if (pollInterval) clearInterval(pollInterval);

  // Initial fetch to populate charts with historical data
  fetchRealTelemetry(true);

  // Poll every 3 seconds for new readings
  pollInterval = setInterval(() => {
    fetchRealTelemetry(false);
  }, 3000);
}

async function fetchRealTelemetry(isInitial) {
  try {
    const limit = isInitial ? MAX_DATA_POINTS : 5;
    const res = await fetch(`${API_BASE}/api/equipment/${activeEquipmentId}/readings?limit=${limit}`);
    if (!res.ok) return;
    const readings = await res.json();

    if (!readings || readings.length === 0) {
      if (isInitial) {
        document.getElementById('tempVal').textContent = '--';
        document.getElementById('vibVal').textContent = '--';
        document.getElementById('soundVal').textContent = '--';
        document.getElementById('axisReadout').textContent = 'AWAITING SENSOR DATA';
        document.getElementById('lastUpdated').textContent = 'NO READINGS YET';
      }
      return;
    }

    // Readings come newest-first, reverse for chronological chart display
    const sorted = isInitial ? readings.reverse() : readings.reverse();

    for (const r of sorted) {
      // Skip if we've already displayed this reading
      if (lastReadingTimestamp && r.timestamp <= lastReadingTimestamp && !isInitial) {
        continue;
      }
      // Use actual stored axis values if available, otherwise derive from magnitude
      const ax = r.vibration_x !== undefined ? r.vibration_x : r.vibration * 0.5;
      const ay = r.vibration_y !== undefined ? r.vibration_y : r.vibration * 0.4;
      const az = r.vibration_z !== undefined ? r.vibration_z : r.vibration * 0.7;
      const mag = r.vibration || r.vibration_magnitude || 0;
      pushTelemetry(r.temperature, ax, ay, az, mag, r.sound, r.timestamp);
    }

    // Track the latest timestamp to avoid duplicate display
    if (sorted.length > 0) {
      lastReadingTimestamp = sorted[sorted.length - 1].timestamp;
    }
  } catch (e) {
    // Backend may be offline — display will hold last known values
  }
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
      const isConn = waData.status === 'connected';
      const pill = document.getElementById('whatsappPill');
      const pillDot = pill ? pill.querySelector('.status-dot') : null;
      const pillVal = pill ? pill.querySelector('.status-value') : null;

      if (pillDot) {
        pillDot.className = isConn ? 'status-dot dot-active' : 'status-dot dot-warn';
      }
      if (pillVal) {
        if (isConn && waData.connectedPhone) {
          pillVal.textContent = `+${waData.connectedPhone}`;
        } else if (!isConn) {
          pillVal.textContent = 'PAIR BOT';
        }
      }
    }
  } catch (e) {
    const pill = document.getElementById('whatsappPill');
    const pillDot = pill ? pill.querySelector('.status-dot') : null;
    const pillVal = pill ? pill.querySelector('.status-value') : null;
    if (pillDot) pillDot.className = 'status-dot dot-neutral';
    if (pillVal) pillVal.textContent = 'OFFLINE';
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
  // Equipment Select — restart real data polling for new equipment
  document.getElementById('equipmentSelect').addEventListener('change', (e) => {
    activeEquipmentId = +e.target.value;
    const node = e.target.options[e.target.selectedIndex].getAttribute('data-node');
    document.getElementById('nodeIdLabel').textContent = `NODE: ${node}`;
    // Clear existing data and re-fetch for new equipment
    timeLabels.length = 0;
    vibXData.length = 0;
    vibYData.length = 0;
    vibZData.length = 0;
    vibMagData.length = 0;
    tempData.length = 0;
    soundData.length = 0;
    lastReadingTimestamp = null;
    startRealDataPolling();
  });

  // Sync DB Button — force refresh from backend
  document.getElementById('btnRefresh').addEventListener('click', async () => {
    lastReadingTimestamp = null;
    timeLabels.length = 0;
    vibXData.length = 0;
    vibYData.length = 0;
    vibZData.length = 0;
    vibMagData.length = 0;
    tempData.length = 0;
    soundData.length = 0;
    await fetchRealTelemetry(true);
  });

  // Quick Prompt Chips — send query immediately
  document.querySelectorAll('.quick-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const promptText = btn.getAttribute('data-prompt');
      document.getElementById('aiInput').value = promptText;
      document.getElementById('aiChatForm').dispatchEvent(new Event('submit'));
    });
  });

  // Reset Chat History Button
  const btnReset = document.getElementById('btnResetChat');
  if (btnReset) {
    btnReset.addEventListener('click', () => {
      const container = document.getElementById('chatContainer');
      const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' });
      const currentTemp = document.getElementById('tempVal').textContent;
      const currentVib = document.getElementById('vibVal').textContent;
      container.innerHTML = `
        <div class="wa-system-pill">
          <span>CONVERSATION RESET · LIVE TELEMETRY ACTIVE</span>
        </div>
        <div class="wa-bubble wa-bubble-ai">
          <div class="wa-sender-tag">
            <span class="wa-sender-name">MECHMIND ENGINE</span>
            <span class="wa-model-badge">LLAMA 3.1:8B</span>
          </div>
          <div class="wa-message-text">
            Diagnostic session refreshed.<br><br>
            • <strong>Temp:</strong> <span id="chatLiveTemp">${currentTemp}°C</span><br>
            • <strong>Vibration:</strong> <span id="chatLiveVib">${currentVib}g</span><br><br>
            Ask about live dashboard statistics, fleet metrics, fault codes, or attach a component photo for visual triage.
          </div>
          <div class="wa-msg-meta">
            <span class="wa-time">${time}</span>
          </div>
        </div>
      `;
    });
  }

  // Diagnostic Chat Submission (Supports Text & Photo Uploads)
  document.getElementById('aiChatForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('aiInput');
    const msg = input.value.trim();
    
    // Check if we have an attached photo or text
    if (!msg && !currentAttachedFile) return;

    input.value = '';

    // If an image was attached, submit via multimodal image diagnostic endpoint
    if (currentAttachedFile) {
      const fileToUpload = currentAttachedFile;
      const dataUrlPreview = currentAttachedDataUrl;
      const captionText = msg || 'Visual inspection of machinery component';

      // Clear the attachment bar preview
      const removeBtn = document.getElementById('btnRemoveAttachment');
      if (removeBtn) removeBtn.click();

      // Append user bubble with image thumbnail
      appendWhatsAppMessage('OPERATOR', captionText, true, dataUrlPreview);

      // Typing indicator (animated dots)
      const typingId = showTypingIndicator();

      try {
        const formData = new FormData();
        formData.append('file', fileToUpload);
        formData.append('phone_number', '+2347010299562');
        formData.append('caption', captionText);
        formData.append('equipment_id', activeEquipmentId);

        const res = await fetch(`${API_BASE}/api/diagnose/image`, {
          method: 'POST',
          body: formData
        });

        const data = await res.json();
        removeMessage(typingId);
        appendWhatsAppMessage('MECHMIND ENGINE', data.response || data.analysis || 'Visual inspection complete.', false);
      } catch (err) {
        removeMessage(typingId);
        appendWhatsAppMessage('MECHMIND ENGINE', 'Vision inference error. Verify local Ollama service is active.', false);
      }
      return;
    }

    // Text-only submission
    appendWhatsAppMessage('OPERATOR', msg, true);

    // Show typing indicator (animated dots — simulates natural typing)
    const typingId = showTypingIndicator();

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
      appendWhatsAppMessage('MECHMIND ENGINE', data.response || 'No diagnostic output returned.', false);
    } catch (err) {
      removeMessage(typingId);
      appendWhatsAppMessage('MECHMIND ENGINE', 'Diagnostic API unreachable. Confirm FastAPI backend is active on port 8080.', false);
    }
  });

  // Setup Interactive WhatsApp Modal
  setupWhatsAppModal();
}

// Image Attachment Controller
let currentAttachedFile = null;
let currentAttachedDataUrl = null;

function setupImageAttachment() {
  const btnAttach = document.getElementById('btnAttachPhoto');
  const fileInput = document.getElementById('aiImageInput');
  const previewBar = document.getElementById('attachedImageBar');
  const previewThumb = document.getElementById('attachedImageThumb');
  const previewName = document.getElementById('attachedImageName');
  const btnRemove = document.getElementById('btnRemoveAttachment');

  if (btnAttach && fileInput) {
    btnAttach.addEventListener('click', () => {
      fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;

      currentAttachedFile = file;
      if (previewName) previewName.textContent = file.name;

      const reader = new FileReader();
      reader.onload = (ev) => {
        currentAttachedDataUrl = ev.target.result;
        if (previewThumb) previewThumb.src = currentAttachedDataUrl;
        if (previewBar) previewBar.style.display = 'flex';
      };
      reader.readAsDataURL(file);
    });
  }

  if (btnRemove) {
    btnRemove.addEventListener('click', () => {
      currentAttachedFile = null;
      currentAttachedDataUrl = null;
      if (fileInput) fileInput.value = '';
      if (previewBar) previewBar.style.display = 'none';
      if (previewThumb) previewThumb.src = '';
    });
  }
}

// Mobile Bottom Navigation Bar (Tab Switcher)
function setupMobileTabs() {
  const navItems = document.querySelectorAll('.mobile-bottom-nav .nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetTab = item.getAttribute('data-tab');
      document.body.setAttribute('data-active-tab', targetTab);
      navItems.forEach(i => i.classList.toggle('active', i === item));
      
      // Auto-scroll to top of newly selected tab
      window.scrollTo({ top: 0, behavior: 'smooth' });

      // Trigger chart resize if navigating to Waveforms tab
      if (targetTab === 'waveforms') {
        setTimeout(() => {
          if (vibrationChart) vibrationChart.resize();
          if (tempChart) tempChart.resize();
        }, 100);
      }
    });
  });
}

// Markdown Formatter for WhatsApp Messages
function formatMarkdown(text) {
  if (!text) return '';
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Bold **text**
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // Italic *text*
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Inline Code `code`
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Bullet Points
  html = html.replace(/^[•\-\*]\s+(.*)$/gm, '• $1');

  // Newlines
  html = html.replace(/\n/g, '<br>');
  return html;
}

// Append WhatsApp Message Bubble
// Show typing indicator with animated dots (simulates natural typing)
function showTypingIndicator() {
  const container = document.getElementById('chatContainer');
  const div = document.createElement('div');
  const id = 'typing-' + Date.now();
  div.id = id;
  div.className = 'wa-bubble wa-bubble-ai wa-typing-bubble';
  div.innerHTML = `
    <div class="wa-sender-tag">
      <span class="wa-sender-name">MECHMIND ENGINE</span>
      <span class="wa-model-badge">LLAMA 3.1:8B</span>
    </div>
    <div class="wa-typing-indicator">
      <span class="wa-typing-dot"></span>
      <span class="wa-typing-dot"></span>
      <span class="wa-typing-dot"></span>
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return id;
}

function appendWhatsAppMessage(sender, text, isUser = false, imageUrl = null) {
  const container = document.getElementById('chatContainer');
  const div = document.createElement('div');
  const id = 'msg-' + Date.now() + '-' + Math.random().toString(36).substring(2, 6);
  div.id = id;

  const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' });

  if (isUser) {
    div.className = 'wa-bubble wa-bubble-user';
    let imageHtml = imageUrl ? `<img src="${imageUrl}" class="chat-msg-img" alt="Attached machinery photo">` : '';
    div.innerHTML = `
      <div class="wa-sender-tag">
        <span class="wa-sender-name">OPERATOR</span>
      </div>
      ${imageHtml}
      <div class="wa-message-text">${formatMarkdown(text)}</div>
      <div class="wa-msg-meta">
        <span class="wa-time">${time}</span>
        <span class="wa-ticks">✓✓</span>
      </div>
    `;
  } else {
    div.className = 'wa-bubble wa-bubble-ai';
    div.innerHTML = `
      <div class="wa-sender-tag">
        <span class="wa-sender-name">MECHMIND ENGINE</span>
        <span class="wa-model-badge">LLAMA 3.1:8B</span>
      </div>
      <div class="wa-message-text">${formatMarkdown(text)}</div>
      <div class="wa-msg-meta">
        <span class="wa-time">${time}</span>
      </div>
    `;
  }

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeMessage(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// ==========================================================
// WhatsApp Modal Controller (Pairing Code & Live QR)
// ==========================================================
let waModalInterval = null;
let currentActiveCode = null;

function setupWhatsAppModal() {
  const modal = document.getElementById('qrModal');
  const openBtn = document.getElementById('openQrModalBtn');
  const closeBtn = document.getElementById('closeQrModalBtn');
  const headerPill = document.getElementById('whatsappPill');

  if (openBtn) openBtn.addEventListener('click', openModal);
  if (headerPill) {
    headerPill.style.cursor = 'pointer';
    headerPill.addEventListener('click', openModal);
  }
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });
  }

  function openModal() {
    if (!modal) return;
    modal.classList.add('open');
    pollWhatsAppModalStatus();
    if (waModalInterval) clearInterval(waModalInterval);
    waModalInterval = setInterval(pollWhatsAppModalStatus, 3000);
  }

  function closeModal() {
    if (!modal) return;
    modal.classList.remove('open');
    if (waModalInterval) {
      clearInterval(waModalInterval);
      waModalInterval = null;
    }
  }

  // Tab switching
  const tabPairing = document.getElementById('tabBtnPairing');
  const tabQr = document.getElementById('tabBtnQr');
  const contentPairing = document.getElementById('tabContentPairing');
  const contentQr = document.getElementById('tabContentQr');

  if (tabPairing && tabQr) {
    tabPairing.addEventListener('click', () => {
      tabPairing.classList.add('active');
      tabQr.classList.remove('active');
      if (contentPairing) contentPairing.style.display = 'flex';
      if (contentQr) contentQr.style.display = 'none';
    });

    tabQr.addEventListener('click', () => {
      tabQr.classList.add('active');
      tabPairing.classList.remove('active');
      if (contentPairing) contentPairing.style.display = 'none';
      if (contentQr) contentQr.style.display = 'flex';
      fetchLiveQr();
    });
  }

  // Request Pairing Code
  const btnGetCode = document.getElementById('btnGetPairingCode');
  const phoneInput = document.getElementById('waPhoneInput');
  const copyBtn = document.getElementById('btnCopyPairingCode');

  if (btnGetCode) {
    btnGetCode.addEventListener('click', async () => {
      const rawPhone = phoneInput ? phoneInput.value.trim() : '2347010299562';
      const cleanPhone = rawPhone.replace(/\D/g, '');
      if (!cleanPhone || cleanPhone.length < 9) {
        alert('Please enter a valid WhatsApp phone number with country code (e.g. 2347010299562).');
        return;
      }

      btnGetCode.disabled = true;
      btnGetCode.textContent = 'REQUESTING...';

      try {
        const res = await fetch('http://localhost:3001/api/pairing-code', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phone: cleanPhone })
        });

        const data = await res.json();
        if (data.code) {
          currentActiveCode = data.code;
          displayPairingCode(data.code);
        } else if (data.status === 'connected') {
          showConnectedState(data.phone || cleanPhone);
        } else {
          alert(data.error || 'Could not generate code. Make sure bot is active on port 3001.');
        }
      } catch (err) {
        alert('Error contacting bot daemon at localhost:3001.');
      } finally {
        btnGetCode.disabled = false;
        btnGetCode.textContent = 'GENERATE CODE';
      }
    });
  }

  // Copy Code
  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      if (!currentActiveCode) return;
      navigator.clipboard.writeText(currentActiveCode).then(() => {
        copyBtn.textContent = 'COPIED ✓';
        setTimeout(() => { copyBtn.textContent = 'COPY'; }, 2000);
      });
    });
  }

  // Refresh QR
  const refreshQrBtn = document.getElementById('btnRefreshQr');
  if (refreshQrBtn) {
    refreshQrBtn.addEventListener('click', fetchLiveQr);
  }

  // Reset Session
  const resetBtn = document.getElementById('btnResetWaSession');
  if (resetBtn) {
    resetBtn.addEventListener('click', async () => {
      if (!confirm('Reset WhatsApp session and start fresh connection socket?')) return;
      resetBtn.textContent = 'RESETTING...';
      try {
        await fetch('http://localhost:3001/api/reset', { method: 'POST' });
        const codeBox = document.getElementById('pairingCodeDisplayBox');
        if (codeBox) codeBox.style.display = 'none';
        currentActiveCode = null;
        setTimeout(pollWhatsAppModalStatus, 1500);
      } catch (e) {
        alert('Could not trigger session reset on port 3001.');
      } finally {
        setTimeout(() => { resetBtn.textContent = 'RESET'; }, 2000);
      }
    });
  }
}

function displayPairingCode(rawCode) {
  const codeBox = document.getElementById('pairingCodeDisplayBox');
  const codeText = document.getElementById('pairingCodeText');
  if (!codeBox || !codeText) return;

  currentActiveCode = rawCode;
  let formatted = rawCode;
  if (rawCode.length === 8) {
    formatted = `${rawCode.slice(0, 4)} - ${rawCode.slice(4)}`;
  }
  codeText.textContent = formatted;
  codeBox.style.display = 'flex';
}

async function fetchLiveQr() {
  const qrImg = document.getElementById('waQrImage');
  const qrLoader = document.getElementById('qrLoader');
  const qrLoaderText = document.getElementById('qrLoaderText');
  const timerLabel = document.getElementById('qrTimerLabel');

  try {
    const res = await fetch('http://localhost:3001/api/qr');
    if (!res.ok) return;
    const data = await res.json();

    if (data.status === 'connected') {
      showConnectedState(data.phone);
    } else if (data.status === 'ready' && data.qr) {
      if (qrImg && qrLoader) {
        qrImg.src = data.qr;
        qrImg.style.display = 'block';
        qrLoader.style.display = 'none';
      }
      if (timerLabel) timerLabel.textContent = 'Live QR active';
    } else {
      if (qrImg && qrLoader) {
        qrImg.style.display = 'none';
        qrLoader.style.display = 'flex';
        if (qrLoaderText) qrLoaderText.textContent = 'Waiting for QR generation...';
      }
    }
  } catch (err) {
    if (qrLoaderText) qrLoaderText.textContent = 'Bot daemon offline on port 3001.';
  }
}

async function pollWhatsAppModalStatus() {
  const statusLabel = document.getElementById('botStatusModalText');
  const statusPhone = document.getElementById('botConnectedPhone');
  const statusDot = document.getElementById('waStatusDot');

  try {
    const res = await fetch('http://localhost:3001/health');
    if (!res.ok) throw new Error('Daemon unreachable');
    const data = await res.json();

    if (data.status === 'connected') {
      showConnectedState(data.connectedPhone);
    } else {
      if (statusDot) {
        statusDot.className = 'terminal-dot dot-waiting';
      }
      if (statusLabel) statusLabel.textContent = 'DAEMON ACTIVE — READY TO PAIR';
      if (statusPhone) statusPhone.textContent = '';

      if (data.pairingCode && !currentActiveCode) {
        displayPairingCode(data.pairingCode);
      }

      const tabQr = document.getElementById('tabBtnQr');
      if (tabQr && tabQr.classList.contains('active')) {
        fetchLiveQr();
      }
    }
  } catch (e) {
    if (statusDot) statusDot.className = 'terminal-dot dot-offline';
    if (statusLabel) statusLabel.textContent = 'DAEMON OFFLINE — PORT 3001';
    if (statusPhone) statusPhone.textContent = '';
  }
}

function showConnectedState(phone) {
  const statusLabel = document.getElementById('botStatusModalText');
  const statusPhone = document.getElementById('botConnectedPhone');
  const statusDot = document.getElementById('waStatusDot');
  const codeBox = document.getElementById('pairingCodeDisplayBox');
  const qrImg = document.getElementById('waQrImage');
  const qrLoader = document.getElementById('qrLoader');
  const qrLoaderText = document.getElementById('qrLoaderText');

  if (statusDot) statusDot.className = 'terminal-dot';
  if (statusLabel) statusLabel.textContent = 'CONNECTED ✓';
  if (statusPhone) statusPhone.textContent = phone ? `(+${phone})` : '';

  if (codeBox) {
    codeBox.style.display = 'flex';
    document.getElementById('pairingCodeText').textContent = 'CONNECTED';
    document.getElementById('pairingCodeNote').textContent = 'Device successfully paired to MechMind AI!';
  }

  if (qrImg && qrLoader) {
    qrImg.style.display = 'none';
    qrLoader.style.display = 'flex';
    if (qrLoaderText) qrLoaderText.textContent = 'Device is already connected.';
  }
}
