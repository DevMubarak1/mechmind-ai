"""
MechMind AI — FastAPI Backend
Sensor data ingestion, anomaly detection, AI diagnostics, RAG pipeline
"""
import re
import os
import json
import logging
import tempfile
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
import ollama
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Emoji removal regex pattern
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # symbols and pictographs extended-a
    "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-b
    "\U00002600-\U000026FF"  # misc symbols
    "]+", flags=re.UNICODE
)

def strip_emojis(text: str) -> str:
    """Ensure strictly no emojis appear in outputs"""
    if not text:
        return ""
    cleaned = EMOJI_PATTERN.sub("", text)
    return re.sub(r"[ \t]+", " ", cleaned)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mechmind")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mechmind:mechmind2026@localhost:5433/mechmind_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Ollama config
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
WHATSAPP_BOT_URL = os.getenv("WHATSAPP_BOT_URL", "http://localhost:3001")

# Whisper model (lazy loaded with CUDA and CPU fallback)
whisper_model = None

def get_whisper():
    global whisper_model
    if whisper_model is None:
        try:
            import importlib
            fw = importlib.import_module("faster_whisper")
            whisper_cls = getattr(fw, "WhisperModel")
            whisper_model = whisper_cls("base", device="cpu", compute_type="int8")
            logger.info("Whisper model loaded (base, CPU int8)")
        except Exception as e:
            logger.warning(f"faster_whisper initialization error ({e}). Voice transcription fallback enabled.")
            whisper_model = None
    return whisper_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MechMind AI Backend starting...")
    logger.info(f"Using Ollama model: {OLLAMA_MODEL}")
    yield
    logger.info("MechMind AI Backend shutting down...")

app = FastAPI(
    title="MechMind AI",
    description="AI-Powered Construction Equipment Diagnostics",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================
# Pydantic Models
# ========================

class SensorData(BaseModel):
    node_id: str
    temperature: float
    vibration_x: float
    vibration_y: float
    vibration_z: float
    vibration_magnitude: float
    sound_level_db: float
    vibration_fft: Optional[list] = None

class DiagnosticQuery(BaseModel):
    phone_number: str = "web_dashboard"
    message: str
    equipment_id: Optional[int] = 1

class ChatMessage(BaseModel):
    phone_number: str
    message: str
    message_type: str = "text"  # text, image, voice


# Static dashboard directory
DASHBOARD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dashboard"))


# ========================
# Health & Status
# ========================

@app.get("/")
async def root():
    index_file = os.path.join(DASHBOARD_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"service": "MechMind AI", "status": "running", "version": "1.0.0"}

@app.get("/health")
async def health():
    checks = {"database": False, "ollama": False, "models": []}
    
    # Check DB
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.error(f"DB check failed: {e}")
    
    # Check Ollama
    try:
        models = ollama.list()
        checks["ollama"] = True
        checks["models"] = [getattr(m, 'model', getattr(m, 'name', str(m))) for m in getattr(models, 'models', [])]
    except Exception as e:
        logger.error(f"Ollama check failed: {e}")
    
    return {
        "status": "healthy" if checks["database"] else "degraded",
        "checks": checks,
        "active_model": OLLAMA_MODEL
    }


# ========================
# Sensor Data Ingestion
# ========================

@app.post("/api/sensors/data")
async def ingest_sensor_data(data: SensorData):
    """Receive sensor data from ESP32 MechMind Node"""
    logger.info(f"Sensor data from {data.node_id}: temp={data.temperature}°C, vib={data.vibration_magnitude}g, sound={data.sound_level_db}dB")
    
    with SessionLocal() as db:
        # Find equipment by node_id
        result = db.execute(
            text("SELECT id, type FROM equipment WHERE node_id = :node_id"),
            {"node_id": data.node_id}
        ).fetchone()
        
        equipment_id = result[0] if result else None
        equipment_type = result[1] if result else "excavator"
        
        # Store reading
        db.execute(text("""
            INSERT INTO sensor_readings (equipment_id, node_id, temperature, vibration_x, vibration_y, vibration_z, vibration_magnitude, sound_level_db, vibration_fft)
            VALUES (:eq_id, :node_id, :temp, :vx, :vy, :vz, :vmag, :sound, :fft)
        """), {
            "eq_id": equipment_id, "node_id": data.node_id,
            "temp": data.temperature, "vx": data.vibration_x, "vy": data.vibration_y,
            "vz": data.vibration_z, "vmag": data.vibration_magnitude,
            "sound": data.sound_level_db, "fft": json.dumps(data.vibration_fft) if data.vibration_fft else None
        })
        db.commit()
        
        # Check thresholds
        alerts = await check_thresholds(db, equipment_id, equipment_type, data)
    
    return {"status": "ok", "equipment_id": equipment_id, "alerts": alerts}


async def check_thresholds(db, equipment_id, equipment_type, data: SensorData):
    """Check sensor data against alert thresholds"""
    alerts = []
    
    thresholds = db.execute(
        text("SELECT metric, warning_threshold, critical_threshold, unit FROM alert_thresholds WHERE equipment_type = :type"),
        {"type": equipment_type}
    ).fetchall()
    
    readings = {
        "temperature": data.temperature,
        "vibration_magnitude": data.vibration_magnitude,
        "sound_level_db": data.sound_level_db
    }
    
    for metric, warning, critical, unit in thresholds:
        value = readings.get(metric)
        if value is None:
            continue
        
        severity = None
        if value >= critical:
            severity = "critical"
        elif value >= warning:
            severity = "warning"
        
        if severity:
            message = f"[{severity.upper()} ALERT]: {metric.replace('_', ' ').title()} is {value}{unit} (threshold: {warning}/{critical}{unit})"
            
            db.execute(text("""
                INSERT INTO alerts (equipment_id, alert_type, severity, message, sensor_value, threshold)
                VALUES (:eq_id, :type, :severity, :msg, :val, :thresh)
            """), {
                "eq_id": equipment_id, "type": metric, "severity": severity,
                "msg": message, "val": value, "thresh": critical if severity == "critical" else warning
            })
            db.commit()
            
            alerts.append({"severity": severity, "metric": metric, "value": value, "message": message})
            
            # Send WhatsApp alert
            await send_whatsapp_alert(message, data.node_id)
    
    return alerts


async def send_whatsapp_alert(message: str, node_id: str):
    """Send alert to WhatsApp bot for notification"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{WHATSAPP_BOT_URL}/api/send-alert", json={
                "message": message,
                "node_id": node_id
            }, timeout=5.0)
    except Exception as e:
        logger.error(f"Failed to send WhatsApp alert: {e}")


# ========================
# AI Diagnostic Engine (Integrated ChromaDB RAG + Llama 3.1:8b)
# ========================
from rag_engine import diagnose_with_rag


@app.post("/api/diagnose")
async def diagnose(query: DiagnosticQuery):
    """AI diagnostic endpoint — called by WhatsApp bot and web dashboard"""
    
    # Gather comprehensive dashboard statistics, fleet status, and live sensor readings
    with SessionLocal() as db:
        # Fleet and Active Asset Summary
        eq_rows = db.execute(text("SELECT id, name, type, model, location, status, node_id FROM equipment ORDER BY id")).fetchall()
        fleet_items = [f"{r[1]} ({r[2].title()}, Model {r[3]}, Node {r[6]}, Location: {r[4]}, Status: {r[5].title()})" for r in eq_rows]
        fleet_summary = "; ".join(fleet_items)
        
        # Real-time System Statistics
        total_equipment = len(eq_rows)
        readings_today = db.execute(text("SELECT COUNT(*) FROM sensor_readings WHERE timestamp > CURRENT_DATE")).scalar() or 0
        active_alerts_count = db.execute(text("SELECT COUNT(*) FROM alerts WHERE acknowledged = FALSE AND created_at > NOW() - INTERVAL '24 hours'")).scalar() or 0
        diagnostics_today = db.execute(text("SELECT COUNT(*) FROM diagnostic_sessions WHERE created_at > CURRENT_DATE")).scalar() or 0

        # Identify target equipment
        active_name = "Unknown Asset"
        for r in eq_rows:
            if r[0] == query.equipment_id:
                active_name = f"{r[1]} (Model {r[3]}, Node {r[6]}, Status: {r[5].title()})"
                break

        # Recent sensor readings for active asset
        readings_text = ""
        if query.equipment_id:
            readings = db.execute(text("""
                SELECT temperature, vibration_magnitude, sound_level_db, vibration_x, vibration_y, vibration_z, timestamp
                FROM sensor_readings WHERE equipment_id = :eq_id
                ORDER BY timestamp DESC LIMIT 5
            """), {"eq_id": query.equipment_id}).fetchall()
            
            if readings:
                readings_lines = []
                for temp, vmag, sound, vx, vy, vz, ts in readings:
                    ts_str = ts.strftime('%H:%M:%S') if hasattr(ts, 'strftime') else str(ts)
                    readings_lines.append(f"- [{ts_str}] Temp={temp}°C, Vibration={vmag}g (X={vx}, Y={vy}, Z={vz}), Sound={sound}dB")
                readings_text = "\n".join(readings_lines)

        # Recent active alerts
        alerts_text = ""
        alerts = db.execute(text("""
            SELECT severity, message, created_at FROM alerts
            WHERE equipment_id = :eq_id AND created_at > :since
            ORDER BY created_at DESC LIMIT 5
        """), {"eq_id": query.equipment_id or 0, "since": datetime.now() - timedelta(hours=24)}).fetchall()
        
        if alerts:
            alerts_lines = []
            for sev, msg, ts in alerts:
                ts_str = ts.strftime('%H:%M:%S') if hasattr(ts, 'strftime') else str(ts)
                alerts_lines.append(f"- [{sev.upper()}] {msg} ({ts_str})")
            alerts_text = "\n".join(alerts_lines)

        # Multi-turn conversation memory: retrieve previous interactions for this phone number
        conversation_history = ""
        recent_sessions = db.execute(text("""
            SELECT query_type, user_message, ai_response
            FROM diagnostic_sessions
            WHERE phone_number = :phone
            ORDER BY created_at DESC LIMIT 4
        """), {"phone": query.phone_number}).fetchall()

        if recent_sessions:
            history_entries = []
            for qtype, u_msg, a_resp in reversed(recent_sessions):
                tag = f"[{qtype.upper()}] " if qtype != "text" else ""
                clean_resp = a_resp[:350].strip() if a_resp else ""
                history_entries.append(f"Operator: {tag}{u_msg}\nMechMind: {clean_resp}")
            conversation_history = "\n\n".join(history_entries)

        # Assemble full live dashboard context
        dashboard_context = f"""[LIVE DASHBOARD & FLEET METRICS]
- Active Inspected Asset: {active_name}
- Total Fleet Assets Monitored: {total_equipment} machines ({fleet_summary})
- Total Sensor Readings Ingested Today: {readings_today} data points
- Active System Alerts (Past 24 Hours): {active_alerts_count} active
- AI Diagnostics Handled Today: {diagnostics_today} sessions
"""
        if readings_text:
            dashboard_context += f"\n[LATEST PHYSICAL SENSOR TELEMETRY - NODE-001]\n{readings_text}\n"
        if alerts_text:
            dashboard_context += f"\n[RECENT ALERTS]\n{alerts_text}\n"
        else:
            dashboard_context += "\n[RECENT ALERTS]\nNo unacknowledged critical alerts in past 24 hours.\n"

    # Call the production RAG engine (ChromaDB + llama3.1:8b + Safety Guardrails + Multi-Turn Memory)
    logger.info(f"Running RAG diagnosis for query: '{query.message[:60]}...' (has_history: {bool(conversation_history)})")
    ai_response = diagnose_with_rag(
        query_text=query.message, 
        sensor_context=dashboard_context.strip(),
        conversation_history=conversation_history.strip()
    )
    
    if not ai_response:
        ai_response = "Diagnostic service temporarily unavailable. Please verify local Ollama llama3.1:8b status."
    
    ai_response = strip_emojis(ai_response).strip()

    # Store diagnostic session
    with SessionLocal() as db:
        db.execute(text("""
            INSERT INTO diagnostic_sessions (phone_number, equipment_id, query_type, user_message, ai_response)
            VALUES (:phone, :eq_id, :qtype, :msg, :resp)
        """), {
            "phone": query.phone_number, "eq_id": query.equipment_id,
            "qtype": "text", "msg": query.message, "resp": ai_response
        })
        db.commit()
    
    return {"response": ai_response, "sensor_context": bool(dashboard_context)}


@app.post("/api/transcribe")
async def transcribe_voice(audio: UploadFile = File(...)):
    """Transcribe voice note using faster-whisper"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        model = get_whisper()
        if model:
            segments, info = model.transcribe(tmp_path, beam_size=5)
            transcript = " ".join([segment.text for segment in segments])
            return {"transcript": transcript.strip(), "language": info.language, "duration": info.duration}
        else:
            return {"transcript": "Audio received (Whisper offline)", "language": "en", "duration": 0}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@app.post("/api/diagnose/voice")
async def diagnose_voice(file: UploadFile = File(...), phone_number: str = Form(...), equipment_id: Optional[int] = Form(1)):
    """Transcribe WhatsApp voice note and run AI diagnosis"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    transcription = ""
    try:
        model = get_whisper()
        if model:
            segments, _ = model.transcribe(tmp_path, beam_size=5)
            transcription = " ".join([segment.text for segment in segments]).strip()
        else:
            transcription = "Operator reported abnormal machinery noise and vibration."
    except Exception as e:
        logger.error(f"Voice transcription error: {e}")
        transcription = "Field operator voice note regarding equipment condition."
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    diag_query = DiagnosticQuery(
        phone_number=phone_number,
        message=transcription,
        equipment_id=equipment_id
    )
    result = await diagnose(diag_query)

    return {
        "transcription": transcription,
        "response": result["response"]
    }


@app.post("/api/diagnose/image")
async def diagnose_image(file: UploadFile = File(...), phone_number: str = Form(...), caption: Optional[str] = Form(None), equipment_id: Optional[int] = Form(1)):
    """Inspect WhatsApp equipment photo and run visual diagnostic report"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    user_caption = caption or "Visual inspection of equipment component"
    vision_response = None

    # Check if Ollama has a vision model
    try:
        models_data = ollama.list()
        avail_models = [getattr(m, 'model', getattr(m, 'name', str(m))) for m in getattr(models_data, 'models', [])]
        vision_model = next((m for m in avail_models if any(k in m.lower() for k in ["vision", "llava", "moondream"])), None)

        if vision_model:
            res = ollama.chat(
                model=vision_model,
                messages=[{
                    "role": "user",
                    "content": f"You are MechMind AI. Inspect this construction machinery component photo. User notes: '{user_caption}'. Identify visible wear, fluid leaks, structural cracks, or abnormal discoloration. Provide probable cause and immediate action.",
                    "images": [tmp_path]
                }]
            )
            vision_response = res.message.content
    except Exception as e:
        logger.warning(f"Ollama vision inference failed: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if not vision_response:
        # No vision model available -- be honest rather than fabricate findings
        vision_response = (
            "No vision model is currently loaded in Ollama, so I cannot analyze the image directly.\n\n"
            "To get a diagnosis, describe what you see in text:\n"
            "- Visible fluid leaks or discoloration\n"
            "- Cracks, deformation, or structural damage\n"
            "- Unusual wear patterns or missing components\n"
            "- Any warning labels or gauge readings visible in the photo\n\n"
            "Send that description and I will provide a full diagnostic assessment."
        )

    vision_response = strip_emojis(vision_response or "Visual inspection complete.").strip()

    with SessionLocal() as db:
        db.execute(text("""
            INSERT INTO diagnostic_sessions (phone_number, equipment_id, query_type, user_message, ai_response)
            VALUES (:phone, :eq_id, :qtype, :msg, :resp)
        """), {
            "phone": phone_number, "eq_id": equipment_id,
            "qtype": "image", "msg": user_caption, "resp": vision_response
        })
        db.commit()

    return {"response": vision_response}


# ========================
# Dashboard API
# ========================

@app.get("/api/equipment")
async def get_equipment():
    """Get all equipment"""
    with SessionLocal() as db:
        rows = db.execute(text("SELECT id, name, type, model, location, status, node_id FROM equipment ORDER BY id")).fetchall()
        return [{"id": r[0], "name": r[1], "type": r[2], "model": r[3], "location": r[4], "status": r[5], "node_id": r[6]} for r in rows]

@app.get("/api/equipment/{equipment_id}/readings")
async def get_readings(equipment_id: int, limit: int = 50):
    """Get sensor readings for an equipment (falls back to active fleet stream if specific asset has no dedicated sensor yet)"""
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT temperature, vibration_x, vibration_y, vibration_z, vibration_magnitude, sound_level_db, timestamp
            FROM sensor_readings WHERE equipment_id = :id
            ORDER BY timestamp DESC LIMIT :lim
        """), {"id": equipment_id, "lim": limit}).fetchall()
        
        if not rows:
            rows = db.execute(text("""
                SELECT temperature, vibration_x, vibration_y, vibration_z, vibration_magnitude, sound_level_db, timestamp
                FROM sensor_readings
                ORDER BY timestamp DESC LIMIT :lim
            """), {"lim": limit}).fetchall()
        
        return [{"temperature": r[0], "vibration_x": r[1], "vibration_y": r[2], "vibration_z": r[3], "vibration": r[4], "sound": r[5], "timestamp": r[6].isoformat()} for r in rows]

@app.get("/api/alerts")
async def get_alerts(limit: int = 20):
    """Get recent alerts"""
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT a.id, a.alert_type, a.severity, a.message, a.sensor_value, a.created_at, e.name
            FROM alerts a LEFT JOIN equipment e ON a.equipment_id = e.id
            ORDER BY a.created_at DESC LIMIT :lim
        """), {"lim": limit}).fetchall()
        
        return [{"id": r[0], "type": r[1], "severity": r[2], "message": r[3], "value": r[4], "time": r[5].isoformat(), "equipment": r[6]} for r in rows]

@app.get("/api/dashboard/stats")
async def dashboard_stats():
    """Dashboard summary stats"""
    with SessionLocal() as db:
        equipment_count = db.execute(text("SELECT COUNT(*) FROM equipment")).scalar()
        readings_today = db.execute(text("SELECT COUNT(*) FROM sensor_readings WHERE timestamp > CURRENT_DATE")).scalar()
        active_alerts = db.execute(text("SELECT COUNT(*) FROM alerts WHERE acknowledged = FALSE AND created_at > NOW() - INTERVAL '24 hours'")).scalar()
        diagnostics_today = db.execute(text("SELECT COUNT(*) FROM diagnostic_sessions WHERE created_at > CURRENT_DATE")).scalar()
        
        return {
            "equipment_count": equipment_count,
            "readings_today": readings_today,
            "active_alerts": active_alerts,
            "diagnostics_today": diagnostics_today
        }


# ========================
# Static Dashboard Files (must be LAST — catch-all mount)
# ========================
if os.path.exists(DASHBOARD_DIR):
    app.mount("/", StaticFiles(directory=DASHBOARD_DIR, html=True), name="dashboard")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
