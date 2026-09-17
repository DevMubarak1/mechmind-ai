/**
 * MechMind AI WhatsApp Bot
 * Uses Baileys (open-source WhatsApp Web API) + Express for internal API
 */

const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, downloadMediaMessage } = require('@whiskeysockets/baileys');
const pino = require('pino');
const express = require('express');
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const path = require('path');
const qrcode = require('qrcode-terminal');

// Config
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';
const BOT_PORT = process.env.BOT_PORT || 3001;
const AUTH_DIR = path.join(__dirname, 'auth_info');
const ALERT_RECIPIENTS = (process.env.ALERT_RECIPIENTS || '').split(',').filter(Boolean);

// Express app for internal API (receives alerts from backend)
const apiApp = express();
apiApp.use(express.json());

let sock = null;

// ========================
// WhatsApp Connection
// ========================

async function startBot() {
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

    sock = makeWASocket({
        auth: state,
        printQRInTerminal: false,
        logger: pino({ level: 'warn' }),
        browser: ['MechMind AI', 'Bot', '1.0.0'],
    });

    // Handle connection updates
    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log('\n╔══════════════════════════════════════╗');
            console.log('║     MECHMIND AI - WhatsApp Bot       ║');
            console.log('║                                      ║');
            console.log('║  Scan QR code with your phone:       ║');
            console.log('║  WhatsApp > Settings > Linked Devices ║');
            console.log('╚══════════════════════════════════════╝\n');
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
            console.log(`Connection closed. Status: ${statusCode}. Reconnecting: ${shouldReconnect}`);
            if (shouldReconnect) {
                setTimeout(startBot, 3000);
            } else {
                console.log('Logged out. Delete auth_info folder and restart to re-scan QR.');
            }
        }

        if (connection === 'open') {
            console.log('\n✅ MechMind AI Bot connected to WhatsApp!\n');
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
            
            // Skip group messages for now
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
    console.log(`📩 Message from ${phoneNumber}`);

    try {
        // Determine message type
        const msgContent = msg.message;
        
        if (msgContent.conversation || msgContent.extendedTextMessage) {
            // Text message
            const text = msgContent.conversation || msgContent.extendedTextMessage?.text || '';
            console.log(`   Text: ${text.substring(0, 100)}`);
            
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
            // Voice note
            console.log('   Type: Voice note');
            await handleVoiceNote(msg, sender, phoneNumber);

        } else if (msgContent.imageMessage) {
            // Photo
            console.log('   Type: Image');
            await handleImage(msg, sender, phoneNumber);

        } else {
            await sendMessage(sender, '🤖 I can help with:\n• *Text* — Describe a problem\n• *Voice note* — Speak your question\n• *Photo* — Show me the issue\n\nType */help* for more options.');
        }
    } catch (error) {
        console.error('Error handling message:', error);
        await sendMessage(sender, '❌ Sorry, something went wrong. Please try again.');
    }
}

async function handleTextQuery(sender, phoneNumber, text) {
    await sendMessage(sender, '🔍 Analyzing your question...');

    try {
        const response = await axios.post(`${BACKEND_URL}/api/diagnose`, {
            phone_number: phoneNumber,
            message: text,
            equipment_id: null
        }, { timeout: 60000 }); // 60s timeout for Ollama

        await sendMessage(sender, response.data.response);
    } catch (error) {
        console.error('Backend error:', error.message);
        await sendMessage(sender, '⚠️ AI engine is loading. Please wait 30 seconds and try again.');
    }
}

async function handleVoiceNote(msg, sender, phoneNumber) {
    await sendMessage(sender, '🎤 Transcribing your voice note...');

    try {
        // Download voice note
        const buffer = await downloadMediaMessage(msg, 'buffer', {});
        
        // Send to backend for transcription
        const form = new FormData();
        form.append('audio', buffer, { filename: 'voice.ogg', contentType: 'audio/ogg' });

        const transcribeRes = await axios.post(`${BACKEND_URL}/api/transcribe`, form, {
            headers: form.getHeaders(),
            timeout: 30000
        });

        const transcript = transcribeRes.data.transcript;
        await sendMessage(sender, `📝 I heard: _"${transcript}"_\n\n🔍 Getting diagnosis...`);

        // Now diagnose the transcript
        const diagRes = await axios.post(`${BACKEND_URL}/api/diagnose`, {
            phone_number: phoneNumber,
            message: transcript,
            equipment_id: null
        }, { timeout: 60000 });

        await sendMessage(sender, diagRes.data.response);

    } catch (error) {
        console.error('Voice processing error:', error.message);
        await sendMessage(sender, '⚠️ Could not process voice note. Try sending a text message instead.');
    }
}

async function handleImage(msg, sender, phoneNumber) {
    const caption = msg.message.imageMessage.caption || 'What issue do you see in this image?';
    await sendMessage(sender, '📸 Analyzing your photo...');

    try {
        // Download image
        const buffer = await downloadMediaMessage(msg, 'buffer', {});
        
        // For now, describe the image context and use text diagnosis
        // (Vision analysis requires Gemini API - added as fallback)
        const diagRes = await axios.post(`${BACKEND_URL}/api/diagnose`, {
            phone_number: phoneNumber,
            message: `[User sent a photo of equipment with caption: "${caption}". Based on the description, provide diagnostic guidance.]`,
            equipment_id: null
        }, { timeout: 60000 });

        await sendMessage(sender, diagRes.data.response);

    } catch (error) {
        console.error('Image processing error:', error.message);
        await sendMessage(sender, '⚠️ Could not analyze photo. Please describe the issue in text.');
    }
}

// ========================
// Helper Functions
// ========================

async function sendMessage(jid, text) {
    if (!sock) return;
    await sock.sendMessage(jid, { text });
}

async function sendHelp(sender) {
    const helpText = `🤖 *MechMind AI — Equipment Diagnostic Bot*

I help field mechanics diagnose construction equipment problems using AI.

*Commands:*
📝 Just type your question — _"My excavator engine is overheating"_
🎤 Send a voice note — describe the problem by speaking
📸 Send a photo — show me the faulty part
/status — Check equipment sensor status
/help — Show this help message

*Example questions:*
• _"Hydraulic pump making grinding noise"_
• _"What causes high vibration in a wheel loader?"_
• _"Engine temperature keeps rising above 100°C"_
• _"Oil leak near the boom cylinder"_

💡 The more detail you give, the better my diagnosis.`;

    await sendMessage(sender, helpText);
}

async function sendStatus(sender) {
    try {
        const res = await axios.get(`${BACKEND_URL}/api/dashboard/stats`, { timeout: 5000 });
        const stats = res.data;

        const statusText = `📊 *MechMind System Status*

🏗️ Equipment monitored: ${stats.equipment_count}
📡 Readings today: ${stats.readings_today}
⚠️ Active alerts: ${stats.active_alerts}
🔍 Diagnostics today: ${stats.diagnostics_today}

_System is running normally._`;

        await sendMessage(sender, statusText);
    } catch (error) {
        await sendMessage(sender, '⚠️ Could not fetch system status. Backend may be offline.');
    }
}

// ========================
// Internal API (for backend to send alerts)
// ========================

apiApp.post('/api/send-alert', async (req, res) => {
    const { message, node_id } = req.body;

    if (!sock) {
        return res.status(503).json({ error: 'WhatsApp not connected' });
    }

    // Send alert to all recipients
    let sent = 0;
    for (const recipient of ALERT_RECIPIENTS) {
        try {
            const jid = `${recipient.replace(/\D/g, '')}@s.whatsapp.net`;
            await sendMessage(jid, `🚨 *ALERT from ${node_id}*\n\n${message}`);
            sent++;
        } catch (e) {
            console.error(`Failed to send alert to ${recipient}:`, e.message);
        }
    }

    res.json({ sent, total: ALERT_RECIPIENTS.length });
});

apiApp.get('/health', (req, res) => {
    res.json({ status: sock ? 'connected' : 'disconnected' });
});

// ========================
// Start
// ========================

apiApp.listen(BOT_PORT, () => {
    console.log(`📡 Alert API listening on port ${BOT_PORT}`);
});

startBot().catch(console.error);
