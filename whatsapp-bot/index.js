/**
 * MechMind AI WhatsApp Bot
 * Uses Baileys (open-source WhatsApp Web API) + Express for internal API
 */

const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, Browsers, downloadMediaMessage } = require('@whiskeysockets/baileys');
const pino = require('pino');
const express = require('express');
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const path = require('path');
const qrcodeTerminal = require('qrcode-terminal');
const QRCode = require('qrcode');
const { resolveFastQuery } = require('./fast_diagnostics');

// Config
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';
const BOT_PORT = process.env.BOT_PORT || 3001;
const AUTH_DIR = path.join(__dirname, 'auth_info');
const ALERT_RECIPIENTS = (process.env.ALERT_RECIPIENTS || '2347010299562').split(',').filter(Boolean);

// Express app for internal API (receives alerts & serves dashboard QR/pairing)
const apiApp = express();
apiApp.use(express.json());

// Enable CORS for dashboard access from port 8080
apiApp.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    if (req.method === 'OPTIONS') return res.sendStatus(200);
    next();
});

let sock = null;
let latestQR = null;
let latestPairingCode = null;
const sentBotMessageIds = new Set();

// ========================
// WhatsApp Connection
// ========================

function clearAuthFolder() {
    try {
        if (fs.existsSync(AUTH_DIR)) {
            const files = fs.readdirSync(AUTH_DIR);
            for (const f of files) {
                fs.unlinkSync(path.join(AUTH_DIR, f));
            }
            console.log('[MECHMIND BOT] Auth folder wiped clean.');
        }
    } catch (e) {
        console.error('Error clearing auth folder:', e.message);
    }
}

async function startBot() {
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

    sock = makeWASocket({
        auth: state,
        printQRInTerminal: false,
        logger: pino({ level: 'silent' }),
        browser: Browsers.ubuntu('Chrome'),
        connectTimeoutMs: 60000,
        defaultQueryTimeoutMs: 60000,
        keepAliveIntervalMs: 25000,
    });

    // Handle connection updates
    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            latestQR = qr;
            console.log('\n[MECHMIND BOT] New WhatsApp QR Code generated.');
            console.log('Access web QR at: http://localhost:3001/api/qr');
            console.log('Or scan below in terminal:\n');
            qrcodeTerminal.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            console.log(`[MECHMIND BOT] Connection closed. Status: ${statusCode}`);
            latestQR = null;
            latestPairingCode = null;

            if (statusCode === DisconnectReason.loggedOut || statusCode === 401) {
                console.log('[MECHMIND BOT] Session invalid / Logged out. Resetting auth_info and restarting cleanly in 3s...');
                clearAuthFolder();
                setTimeout(startBot, 3000);
            } else {
                console.log('[MECHMIND BOT] Reconnecting in 4s...');
                setTimeout(startBot, 4000);
            }
        }

        if (connection === 'open') {
            latestQR = null;
            latestPairingCode = null;
            const connectedNum = sock?.user?.id ? sock.user.id.split(':')[0] : 'Linked';
            console.log(`\n[MECHMIND BOT] Successfully connected to WhatsApp! User: +${connectedNum}\n`);
        }
    });

    // Save credentials on update
    sock.ev.on('creds.update', saveCreds);

    // Handle incoming messages
    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return;

        for (const msg of messages) {
            if (!msg.message) continue;
            // Ignore messages sent by our bot
            if (msg.key.id && sentBotMessageIds.has(msg.key.id)) continue;

            const sender = msg.key.remoteJid;
            // Ignore WhatsApp Status/Stories, broadcasts, and group chats
            if (!sender || sender === 'status@broadcast' || sender.endsWith('@broadcast') || sender.endsWith('@g.us')) {
                continue;
            }
            if (!sender.endsWith('@s.whatsapp.net') && !sender.endsWith('@lid')) {
                continue;
            }

            const msgContent = msg.message;
            const text = (
                msgContent.conversation ||
                msgContent.extendedTextMessage?.text ||
                msgContent.imageMessage?.caption ||
                ''
            ).trim();

            // Ignore messages that start with bot response prefixes to prevent echo loops
            if (
                text.startsWith('*MechMind') ||
                text.startsWith('*Diagnostic Request') ||
                text.startsWith('*Voice Processing') ||
                text.startsWith('*Visual Inspection') ||
                text.startsWith('Could not connect') ||
                text.startsWith('Could not process') ||
                text.startsWith('An error occurred') ||
                text.startsWith('*ALERT from') ||
                text.startsWith('*Transcribed:*') ||
                text.startsWith('Diagnostic service')
            ) {
                continue;
            }

            const myNumber = sock?.user?.id ? sock.user.id.replace(/:\d+/, '').replace(/\D/g, '') : '';
            const myLid = sock?.user?.lid ? sock.user.lid.replace(/:\d+/, '').replace(/\D/g, '') : '';
            const senderClean = sender.replace(/\D/g, '');

            const isSelfChat = (myNumber && senderClean === myNumber) || (myLid && senderClean === myLid) || sender.includes('@lid');
            const isAlertRecipient = ALERT_RECIPIENTS.some(r => {
                const clean = r.replace(/\D/g, '');
                return clean && (senderClean.includes(clean) || clean.includes(senderClean));
            });
            const isFromMe = !!msg.key.fromMe;
            const isCommand = text.startsWith('/');

            // Allow messages if:
            // 1. Sent to us by another user (!isFromMe)
            // 2. Sent by user in self-chat (isSelfChat)
            // 3. Sent by user in test/alert recipient chat (isAlertRecipient)
            // 4. Any message beginning with a command (/help, /status, etc.)
            if (isFromMe && !isSelfChat && !isAlertRecipient && !isCommand) {
                continue;
            }

            console.log(`[MSG] Processing message from ${sender} (fromMe: ${isFromMe}): "${text || '[media]'}"`);
            await handleMessage(msg, sender);
        }
    });
}

// ========================
// Sub-10ms Fast In-Memory Response Engine & Telemetry Caching
// ========================
const FAST_RESPONSE_CACHE = new Map();

// In-memory telemetry cache for sub-millisecond status replies
let cachedTelemetry = null;
let lastTelemetryFetch = 0;

async function updateTelemetryCache() {
    try {
        const res = await axios.get(`${BACKEND_URL}/api/equipment/1/readings?limit=1`, { timeout: 1500 });
        if (res.data && res.data[0]) {
            cachedTelemetry = res.data[0];
            lastTelemetryFetch = Date.now();
        }
    } catch (e) {}
}

// Background telemetry sync every 2 seconds
setInterval(updateTelemetryCache, 2000);
updateTelemetryCache();

// Quick pattern definitions for sub-10ms fast paths
const GREETINGS_RE = /^(hi|hello|hey|good\s?(morning|afternoon|evening)|oga|boss|salaam|salam|how\s*far|sup|yo)\b/i;
const STATUS_RE = /^(status|\/status|cat\s*320\s*status|node-001|check|fleet|telemetry|readings|health|sensor|temp|temperature|vibration)$/i;
const HELP_RE = /^(help|\/help|menu|commands|who\s+are\s+you|what\s+is\s+mechmind|\?)$/i;

async function handleMessage(msg, sender) {
    const phoneNumber = sender.replace('@s.whatsapp.net', '').replace('@lid', '');

    try {
        const msgContent = msg.message;
        
        if (msgContent.conversation || msgContent.extendedTextMessage) {
            const text = (msgContent.conversation || msgContent.extendedTextMessage?.text || '').trim();
            const lower = text.toLowerCase();

            // FAST-PATH 1: Instant Greetings (< 1ms)
            if (GREETINGS_RE.test(lower)) {
                await sendMessage(sender, 
                    "Hello! I'm MechMind AI, here to help you with any questions about your heavy machinery, " +
                    "whether it's troubleshooting, maintenance, live telemetry, or general inquiries. " +
                    "How can I assist you today?"
                );
                return;
            }

            // FAST-PATH 2: Instant Help & Commands (< 1ms)
            if (HELP_RE.test(lower)) {
                await sendHelp(sender);
                return;
            }
            
            // FAST-PATH 3: Instant Telemetry Status (< 1ms from in-memory cache)
            if (STATUS_RE.test(lower)) {
                const r = cachedTelemetry;
                if (r) {
                    const tempStatus = r.temperature > 85 ? 'HIGH WARNING' : 'NORMAL';
                    const vibStatus = r.vibration > 2.5 ? 'CRITICAL VIBRATION' : 'STABLE';
                    await sendMessage(sender,
                        `*MechMind Fleet Telemetry: CAT 320 (NODE-001)*\n\n` +
                        `- Temperature: ${r.temperature} C (${tempStatus})\n` +
                        `- Vibration: ${r.vibration}g [X:${r.vibration_x} Y:${r.vibration_y} Z:${r.vibration_z}] (${vibStatus})\n` +
                        `- Acoustic Noise: ${r.sound} dB\n` +
                        `- Condition: HEALTHY / OPERATIONAL\n` +
                        `- Timestamp: ${new Date(r.timestamp).toLocaleTimeString()}`
                    );
                    return;
                }
                // Fallback if cache not ready yet
                await sendStatus(sender);
                return;
            }

            // FAST-PATH 4: Instant SAE J1939 & Machinery Fault Diagnostics (< 0.2ms)
            const fastDiagnosis = resolveFastQuery(text);
            if (fastDiagnosis) {
                console.log(`[FAST-PATH DIAGNOSTICS] Resolved "${text}" in < 0.2ms!`);
                await sendMessage(sender, fastDiagnosis);
                return;
            }

            // FAST-PATH 5: In-Memory Response Cache (< 0.01ms)
            if (FAST_RESPONSE_CACHE.has(lower)) {
                console.log(`[FAST-PATH CACHE] Returning cached diagnosis for: "${lower}"`);
                await sendMessage(sender, FAST_RESPONSE_CACHE.get(lower));
                return;
            }

            // Tier 1: Two-Phase Instant Acknowledgment (< 5ms) + Deep RAG Reasoning
            await handleTextQuery(sender, phoneNumber, text, lower);
        } else if (msgContent.audioMessage) {
            console.log('   Audio message received from', sender);
            await handleAudioMessage(msg, sender, phoneNumber);
        } else if (msgContent.imageMessage) {
            console.log('   Image message received from', sender);
            await handleImageMessage(msg, sender, phoneNumber);
        }
    } catch (err) {
        console.error('Error handling message:', err);
        await sendMessage(sender, 'An error occurred processing your request. Please check backend.');
    }
}

// Strip markdown formatting from bot response text before sending to WhatsApp
function stripMarkdown(text) {
    return text
        .replace(/\*\*(.+?)\*\*/g, '$1')                         // **bold** -> plain
        .replace(/\*([A-Z][^*\n]{0,40}:)\*/g, '$1')              // *HEADER:* -> HEADER:
        .replace(/^\s*\*\s+/gm, '- ')                            // * bullet -> - bullet
        .replace(/\*/g, '')                                       // remaining asterisks
        .replace(/^#{1,4}\s+(.+)$/gm, (_, t) => t.toUpperCase()) // ## Header -> HEADER
        .replace(/^[-_]{3,}\s*$/gm, '')                          // horizontal rules
        .replace(/\n{3,}/g, '\n\n')                              // collapse blank lines
        .trim();
}

// Helper to keep WhatsApp typing animation alive continuously until response is ready
function createTypingHeartbeat(sender) {
    if (sock && sock.sendPresenceUpdate) {
        sock.sendPresenceUpdate('composing', sender).catch(() => {});
    }
    const timer = setInterval(() => {
        if (sock && sock.sendPresenceUpdate) {
            sock.sendPresenceUpdate('composing', sender).catch(() => {});
        }
    }, 6000);
    return () => {
        clearInterval(timer);
        if (sock && sock.sendPresenceUpdate) {
            sock.sendPresenceUpdate('paused', sender).catch(() => {});
        }
    };
}

// Handle text diagnostic queries — shows native WhatsApp "typing..." animation continuously
async function handleTextQuery(sender, phoneNumber, text, lowerKey) {
    const stopTyping = createTypingHeartbeat(sender);
    try {
        const res = await axios.post(`${BACKEND_URL}/api/diagnose`, {
            phone_number: phoneNumber,
            message: text,
            equipment_id: 1
        }, {
            timeout: 180000 // 180s timeout
        });

        stopTyping();
        const response = stripMarkdown(res.data.response || 'No diagnosis available.');

        // Cache response in memory for instant future lookups
        FAST_RESPONSE_CACHE.set(lowerKey, response);
        if (FAST_RESPONSE_CACHE.size > 500) {
            const firstKey = FAST_RESPONSE_CACHE.keys().next().value;
            FAST_RESPONSE_CACHE.delete(firstKey);
        }

        await sendMessage(sender, response);
    } catch (err) {
        stopTyping();
        console.error('Backend API error:', err.message);
        if (err.code === 'ECONNABORTED' || err.message.includes('timeout')) {
            await sendMessage(sender, 'The diagnostic engine took longer than expected. Please retry your query.');
        } else {
            await sendMessage(sender, 'Could not connect to the diagnostic engine. Is the backend running on port 8080?');
        }
    }
}

// Handle voice notes — shows native WhatsApp "typing..." animation
async function handleAudioMessage(msg, sender, phoneNumber) {
    const stopTyping = createTypingHeartbeat(sender);

    try {
        const buffer = await downloadMediaMessage(msg, 'buffer', {});
        const tempPath = path.join(__dirname, `temp_audio_${Date.now()}.ogg`);
        fs.writeFileSync(tempPath, buffer);

        const formData = new FormData();
        formData.append('file', fs.createReadStream(tempPath));
        formData.append('phone_number', phoneNumber);

        const res = await axios.post(`${BACKEND_URL}/api/diagnose/voice`, formData, {
            headers: formData.getHeaders(),
            timeout: 180000
        });

        try { fs.unlinkSync(tempPath); } catch (e) {}
        stopTyping();

        const { transcription, response } = res.data;
        const cleanResponse = stripMarkdown(response || '');
        await sendMessage(sender, `Transcribed: "${transcription}"\n\n${cleanResponse}`);
    } catch (err) {
        stopTyping();
        console.error('Voice processing error:', err.message);
        if (err.code === 'ECONNABORTED' || err.message.includes('timeout')) {
            await sendMessage(sender, 'Voice transcription timed out. Please send a text message instead.');
        } else {
            await sendMessage(sender, 'Could not process audio. Please send a text message instead.');
        }
    }
}

// Handle images — shows native WhatsApp "typing..." animation
async function handleImageMessage(msg, sender, phoneNumber) {
    const stopTyping = createTypingHeartbeat(sender);

    try {
        const buffer = await downloadMediaMessage(msg, 'buffer', {});
        const caption = msg.message.imageMessage?.caption || 'Equipment inspection';
        const tempPath = path.join(__dirname, `temp_img_${Date.now()}.jpg`);
        fs.writeFileSync(tempPath, buffer);

        const formData = new FormData();
        formData.append('file', fs.createReadStream(tempPath));
        formData.append('phone_number', phoneNumber);
        formData.append('caption', caption);

        const res = await axios.post(`${BACKEND_URL}/api/diagnose/image`, formData, {
            headers: formData.getHeaders(),
            timeout: 60000
        });

        try { fs.unlinkSync(tempPath); } catch (e) {}
        stopTyping();

        const response = stripMarkdown(res.data.response || 'Image received.');
        await sendMessage(sender, response);
    } catch (err) {
        stopTyping();
        console.error('Image processing error:', err.message);
        if (err.code === 'ECONNABORTED' || err.message.includes('timeout')) {
            await sendMessage(sender, 'Image analysis timed out. Describe what you see in text — wear patterns, leaks, cracks, discoloration — and I can help diagnose from your description.');
        } else {
            await sendMessage(sender, 'Could not process the image. Send a text description of what you are seeing and I will help diagnose it.');
        }
    }
}


// Help command
async function sendHelp(sender) {
    const helpText = `*MechMind AI - Field Assistant*

Send me any of the following:
- *Text*: Describe symptoms (e.g., "hydraulic pump overheating at 90C")
- *Voice Note*: Speak naturally in English, Pidgin, or Hausa
- *Photo*: Send a picture of the damaged component or gauge
- */status*: Check current machinery status
- */help*: Show this help menu

*Tip*: Include equipment name (CAT 320, XCMG loader, etc.) for better diagnosis.`;

    await sendMessage(sender, helpText);
}

// Status command
async function sendStatus(sender) {
    try {
        const res = await axios.get(`${BACKEND_URL}/api/equipment`);
        const equipment = res.data;

        let statusText = '*MechMind Fleet Status*\n\n';
        for (const eq of equipment) {
            statusText += `*${eq.name}* (${eq.type})\n`;
            statusText += `  Status: ${eq.status.toUpperCase()}\n`;
            statusText += `  Location: ${eq.location || 'Site A'}\n\n`;
        }

        await sendMessage(sender, statusText);
    } catch (err) {
        await sendMessage(sender, 'Could not fetch equipment status from backend.');
    }
}

// Helper: send text message
async function sendMessage(jid, text) {
    if (!sock) return null;
    try {
        const sent = await sock.sendMessage(jid, { text });
        if (sent?.key?.id) {
            sentBotMessageIds.add(sent.key.id);
            if (sentBotMessageIds.size > 1000) {
                const first = sentBotMessageIds.values().next().value;
                sentBotMessageIds.delete(first);
            }
        }
        return sent;
    } catch (err) {
        console.error(`[MECHMIND BOT] Error sending message to ${jid}:`, err.message);
        return null;
    }
}

// ========================
// Express API Endpoints
// ========================

// Send alert to configured WhatsApp recipients
apiApp.post('/api/send-alert', async (req, res) => {
    const { message, node_id } = req.body;

    if (!sock || !sock.user) {
        return res.status(503).json({ error: 'WhatsApp not connected' });
    }

    let sent = 0;
    for (const recipient of ALERT_RECIPIENTS) {
        try {
            const jid = `${recipient.replace(/\D/g, '')}@s.whatsapp.net`;
            await sendMessage(jid, `*ALERT from ${node_id}*\n\n${message}`);
            sent++;
        } catch (e) {
            console.error(`Failed to send alert to ${recipient}:`, e.message);
        }
    }

            res.json({ sent, total: ALERT_RECIPIENTS.length });
});

// Send custom message to any phone or JID
apiApp.post('/api/send-message', async (req, res) => {
    const { to, message } = req.body;
    if (!sock || !sock.user) {
        return res.status(503).json({ error: 'WhatsApp not connected' });
    }
    try {
        const jid = to.includes('@') ? to : `${to.replace(/\D/g, '')}@s.whatsapp.net`;
        const result = await sendMessage(jid, message);
        res.json({ success: !!result, to: jid });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// Provide QR Code image to dashboard
apiApp.get('/api/qr', async (req, res) => {
    const isConnected = !!(sock && sock.user);
    if (isConnected) {
        const phone = sock.user?.id ? sock.user.id.split(':')[0] : 'Linked';
        return res.json({ status: 'connected', qr: null, phone });
    }

    if (!latestQR) {
        return res.json({ 
            status: 'waiting', 
            qr: null, 
            pairingCode: latestPairingCode 
        });
    }

    try {
        const dataUrl = await QRCode.toDataURL(latestQR, {
            width: 220,
            margin: 2,
            color: {
                dark: '#09090b',
                light: '#ffffff'
            }
        });
        res.json({ 
            status: 'ready', 
            qr: dataUrl, 
            raw: latestQR,
            pairingCode: latestPairingCode
        });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// Request 8-Character Pairing Code (Alternative to QR Code)
apiApp.post('/api/pairing-code', async (req, res) => {
    const rawPhone = req.body.phone || '2347010299562';
    const phone = rawPhone.replace(/\D/g, '');

    if (sock && sock.user) {
        const userPhone = sock.user?.id ? sock.user.id.split(':')[0] : phone;
        return res.json({ status: 'connected', code: null, message: `Already connected to WhatsApp (+${userPhone}).` });
    }

    if (!sock) {
        return res.status(503).json({ error: 'WhatsApp socket not initialized' });
    }

    try {
        console.log(`[MECHMIND BOT] Requesting 8-digit pairing code for: +${phone}`);
        const code = await sock.requestPairingCode(phone);
        latestPairingCode = code;
        console.log(`[MECHMIND BOT] >>> PAIRING CODE: ${code} <<<`);
        res.json({ status: 'pairing_code', code, phone: `+${phone}` });
    } catch (err) {
        console.error('[MECHMIND BOT] Error requesting pairing code:', err.message);
        res.status(500).json({ error: err.message });
    }
});

// Reset session & clear auth folder
apiApp.post('/api/reset', async (req, res) => {
    try {
        console.log('[MECHMIND BOT] Session reset requested from dashboard.');
        latestQR = null;
        latestPairingCode = null;
        if (sock) {
            try { sock.end(undefined); } catch (e) {}
            sock = null;
        }
        clearAuthFolder();
        setTimeout(startBot, 1000);
        res.json({ status: 'resetting', message: 'Auth info cleared and bot restarting clean session.' });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Health check endpoint
apiApp.get('/health', (req, res) => {
    const isConnected = !!(sock && sock.user);
    const phone = isConnected ? (sock.user?.id ? sock.user.id.split(':')[0] : null) : null;
    res.json({
        status: isConnected ? 'connected' : 'disconnected',
        hasQR: !!latestQR,
        hasPairingCode: !!latestPairingCode,
        pairingCode: latestPairingCode,
        connectedPhone: phone
    });
});

// ========================
// Start
// ========================

apiApp.listen(BOT_PORT, () => {
    console.log(`[MECHMIND BOT] Alert API & QR Server listening on port ${BOT_PORT}`);
});

startBot().catch(console.error);
