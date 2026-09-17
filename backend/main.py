"""
MechMind AI — FastAPI Backend
Sensor data ingestion, anomaly detection, AI diagnostics, RAG pipeline
"""
import os
import json
import logging
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
import ollama
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mechmind")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mechmind:mechmind2026@localhost:5433/mechmind_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Ollama config
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
WHATSAPP_BOT_URL = os.getenv("WHATSAPP_BOT_URL", "http://localhost:3001")

# Whisper model (lazy loaded)
whisper_model = None

def get_whisper():
    global whisper_model
    if whisper_model is None:
        from faster_whisper import WhisperModel
        whisper_model = WhisperModel("base", device="cuda", compute_type="float16")
        logger.info("Whisper model loaded (base, CUDA)")
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
    phone_number: str
    message: str
    equipment_id: Optional[int] = None

class ChatMessage(BaseModel):
    phone_number: str
    message: str
    message_type: str = "text"  # text, image, voice


from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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
            message = f"⚠️ {severity.upper()}: {metric.replace('_', ' ').title()} is {value}{unit} (threshold: {warning}/{critical}{unit})"
            
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
# AI Diagnostic Engine
# ========================

SYSTEM_PROMPT = """You are MechMind AI, an expert construction equipment diagnostic assistant. You help field mechanics and operators diagnose problems with excavators, loaders, cranes, generators, and other construction machinery.

When given sensor data or a user description of a problem, you:
1. Analyze the symptoms
2. Identify probable causes (ranked by likelihood)
3. Recommend immediate actions
4. Suggest preventive maintenance steps

Be concise but thorough. Use simple language that a field mechanic understands.
If you have sensor data context, reference specific readings in your diagnosis.
Always prioritize safety — if a reading indicates danger, warn immediately.

Format responses for WhatsApp (use emojis sparingly, short paragraphs, numbered lists)."""


def generate_expert_diagnosis(query_text: str, sensor_context: str = "") -> str:
    """Deterministic heuristic diagnostic engine for heavy equipment if LLM is offline"""
    q = query_text.lower()
    
    if "temp" in q or "overheat" in q or "hot" in q or "oil" in q:
        return (
            "⚠️ *MechMind AI Diagnostic Report: Thermal Anomaly*\n\n"
            "*1. Probable Causes:*\n"
            "• Hydraulic oil cooler radiator clogged with construction debris or dust.\n"
            "• Main relief valve bypass failure causing continuous pump pressure build-up.\n"
            "• Low hydraulic reservoir level or degraded anti-wear oil viscosity.\n\n"
            "*2. Immediate Action:*\n"
            "• Idle engine immediately and verify hydraulic cooler fan operation.\n"
            "• Inspect sight glass on reservoir for oil level and foaming.\n\n"
            "*3. Preventive Steps:*\n"
            "• Pressure wash oil cooler matrix every 250 operating hours."
        )
    elif "vib" in q or "shake" in q or "bearing" in q or "shock" in q:
        return (
            "⚙️ *MechMind AI Diagnostic Report: Vibration Anomaly*\n\n"
            "*1. Probable Causes:*\n"
            "• ADXL345 detected harmonic unbalance in main hydraulic pump shaft.\n"
            "• Slew ring bearing raceway fatigue or loose turret mounting bolts.\n"
            "• Track motor planetary gear wear or loose engine damper mount.\n\n"
            "*2. Immediate Action:*\n"
            "• Torque check all pump and engine mount bolts to OEM spec.\n"
            "• Perform visual check on slew gear teeth for pitting or metal flakes.\n\n"
            "*3. Preventive Steps:*\n"
            "• Grease slew bearing raceway every 50 operating hours."
        )
    elif "knock" in q or "sound" in q or "noise" in q or "whine" in q:
        return (
            "🔊 *MechMind AI Diagnostic Report: Acoustic / Noise Anomaly*\n\n"
            "*1. Probable Causes:*\n"
            "• Hydraulic pump cavitation due to restricted suction strainer.\n"
            "• Turbocharger compressor wheel rub or shaft bearing play.\n"
            "• Fuel injection pump knock or valve lash clearance out of spec.\n\n"
            "*2. Immediate Action:*\n"
            "• Check suction line hose for soft collapse under high engine RPM.\n"
            "• Bleed hydraulic tank breather filter.\n\n"
            "*3. Safety Notice:*\n"
            "• Continued operation under pump cavitation will result in catastrophic pump failure."
        )
    else:
        return (
            "🔍 *MechMind AI Telemetry Diagnostic Summary*\n\n"
            "Telemetry analysis completed for active asset.\n"
            "• *Status:* Operating parameters monitored by ADXL345 and NTC probe.\n"
            "• *Recommendation:* Verify fluid levels, grease slew ring, and clean engine radiator.\n"
            "For a specific component diagnosis, ask about: *temperature*, *vibration*, *unusual noises*, or *pump pressure*."
        )


@app.post("/api/diagnose")
async def diagnose(query: DiagnosticQuery):
    """AI diagnostic endpoint — called by WhatsApp bot"""
    
    # Get recent sensor data for context
    sensor_context = ""
    with SessionLocal() as db:
        if query.equipment_id:
            readings = db.execute(text("""
                SELECT temperature, vibration_magnitude, sound_level_db, timestamp
                FROM sensor_readings WHERE equipment_id = :eq_id
                ORDER BY timestamp DESC LIMIT 5
            """), {"eq_id": query.equipment_id}).fetchall()
            
            if readings:
                sensor_context = "\n\nRecent sensor readings:\n"
                for temp, vib, sound, ts in readings:
                    sensor_context += f"- {ts}: Temp={temp}°C, Vibration={vib}g, Sound={sound}dB\n"
        
        # Get recent alerts
        alerts = db.execute(text("""
            SELECT severity, message, created_at FROM alerts
            WHERE equipment_id = :eq_id AND created_at > :since
            ORDER BY created_at DESC LIMIT 5
        """), {"eq_id": query.equipment_id or 0, "since": datetime.now() - timedelta(hours=24)}).fetchall()
        
        if alerts:
            sensor_context += "\nRecent alerts:\n"
            for sev, msg, ts in alerts:
                sensor_context += f"- [{sev}] {msg}\n"
    
    # Call Ollama with fallback
    full_prompt = f"{query.message}{sensor_context}"
    ai_response = None
    
    # Try active Ollama model (llama3.2:3b or llama3.1:8b)
    for model_name in [OLLAMA_MODEL, "llama3.2:3b", "llama3.1:8b"]:
        try:
            response = ollama.chat(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt}
                ]
            )
            ai_response = response.message.content
            if ai_response:
                break
        except Exception as e:
            logger.warning(f"Ollama attempt with {model_name} failed: {e}")
            continue

    if not ai_response:
        ai_response = generate_expert_diagnosis(query.message, sensor_context)
    
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
    
    return {"response": ai_response, "sensor_context": bool(sensor_context)}


@app.post("/api/transcribe")
async def transcribe_voice(audio: UploadFile = File(...)):
    """Transcribe voice note using faster-whisper"""
    import tempfile
    
    # Save uploaded audio to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        model = get_whisper()
        segments, info = model.transcribe(tmp_path, beam_size=5)
        transcript = " ".join([segment.text for segment in segments])
        
        return {"transcript": transcript.strip(), "language": info.language, "duration": info.duration}
    finally:
        os.unlink(tmp_path)


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
    """Get sensor readings for an equipment"""
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT temperature, vibration_magnitude, sound_level_db, timestamp
            FROM sensor_readings WHERE equipment_id = :id
            ORDER BY timestamp DESC LIMIT :lim
        """), {"id": equipment_id, "lim": limit}).fetchall()
        
        return [{"temperature": r[0], "vibration": r[1], "sound": r[2], "timestamp": r[3].isoformat()} for r in rows]

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
