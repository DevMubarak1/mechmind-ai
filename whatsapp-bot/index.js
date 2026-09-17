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
            if (msg.key.fromMe) continue; // Skip our own messages
            if (!msg.message) continue;

            const sender = msg.key.remoteJid;
            const isGroup = sender.endsWith('@g.us');
            
            // Skip group messages
            if (isGroup) continue;

            await handleMessage(msg, sender);
        }
    });
}

// ========================
// Message Handling
// ========================

async function handleMessage(msg, sender) {
    const phoneNumber = sender.replace('@s.whatsapp.net', '');
    console.log(`[MSG] Incoming message from ${phoneNumber}`);

    try {
        const msgContent = msg.message;
        
        if (msgContent.conversation || msgContent.extendedTextMessage) {
            const text = msgContent.conversation || msgContent.extendedTextMessage?.text || '';
            
            if (text.toLowerCase() === '/help' || text.toLowerCase() === 'help') {
                await sendHelp(sender);
                return;
            }
            
            if (text.toLowerCase() === '/status') {
                await sendStatus(sender);
                return;
            }

            await handleTextQuery(sender, phoneNumber, text);
        } else if (msgContent.audioMessage) {
            console.log('   Audio message received');
            await handleAudioMessage(msg, sender, phoneNumber);
        } else if (msgContent.imageMessage) {
            console.log('   Image message received');
            await handleImageMessage(msg, sender, phoneNumber);
        }
    } catch (err) {
        console.error('Error handling message:', err);
        await sendMessage(sender, 'Sorry, an error occurred processing your request. Please try again.');
    }
}

// Handle text diagnostic queries
async function handleTextQuery(sender, phoneNumber, text) {
    await sendMessage(sender, 'Thinking... Analyzing with MechMind AI...');

    try {
        const res = await axios.post(`${BACKEND_URL}/api/diagnose`, {
            phone_number: phoneNumber,
            message: text,
            equipment_id: 1 // Default to equipment 1, or parse from message
        });

        const response = res.data.response || 'No diagnosis available.';
        await sendMessage(sender, `*MechMind AI Diagnosis:*\n\n${response}`);
    } catch (err) {
        console.error('Backend API error:', err.message);
        await sendMessage(sender, 'Could not connect to the diagnostic engine. Is the backend running?');
    }
}

// Handle voice notes
async function handleAudioMessage(msg, sender, phoneNumber) {
    await sendMessage(sender, 'Transcribing your voice note...');

    try {
        const buffer = await downloadMediaMessage(msg, 'buffer', {});
        const tempPath = path.join(__dirname, `temp_audio_${Date.now()}.ogg`);
        fs.writeFileSync(tempPath, buffer);

        const formData = new FormData();
        formData.append('file', fs.createReadStream(tempPath));
        formData.append('phone_number', phoneNumber);

        const res = await axios.post(`${BACKEND_URL}/api/diagnose/voice`, formData, {
            headers: formData.getHeaders(),
            timeout: 60000
        });

        // Cleanup
        try { fs.unlinkSync(tempPath); } catch (e) {}

        const { transcription, response } = res.data;
        await sendMessage(sender, `*Transcribed:* "${transcription}"\n\n*MechMind AI Diagnosis:*\n\n${response}`);
    } catch (err) {
        console.error('Voice processing error:', err.message);
        await sendMessage(sender, 'Could not process audio. Please send a text message instead.');
    }
}

// Handle images
async function handleImageMessage(msg, sender, phoneNumber) {
    await sendMessage(sender, 'Analyzing your image...');

    try {
        const buffer = await downloadMediaMessage(msg, 'buffer', {});
        const caption = msg.message.imageMessage.caption || 'Equipment inspection';
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

        const response = res.data.response || 'Image analyzed.';
        await sendMessage(sender, `*Visual Inspection Analysis:*\n\n${response}`);
    } catch (err) {
        console.error('Image processing error:', err.message);
        await sendMessage(sender, 'Could not process image. Please try again.');
    }
}

// Help command
async function sendHelp(sender) {
    const helpText = `*MechMind AI - Field Assistant*

Send me any of the following:
• *Text*: Describe symptoms (e.g., "hydraulic pump overheating at 90C")
• *Voice Note*: Speak naturally in English, Pidgin, or Hausa
• *Photo*: Send a picture of the damaged component or gauge
• */status*: Check current machinery status
• */help*: Show this help menu

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
    if (!sock) return;
    await sock.sendMessage(jid, { text });
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
