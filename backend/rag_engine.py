"""
MechMind AI - RAG Diagnostic Engine
Retrieval-Augmented Generation for Heavy Machinery Maintenance and Telemetry Analysis.
Uses ChromaDB vector store + all-MiniLM-L6-v2 embeddings + Ollama (Llama 3.1 8B).
"""

import os
import re
import glob
import logging
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.utils import embedding_functions
import ollama

logger = logging.getLogger("mechmind.rag")

CHROMA_URL = os.getenv("CHROMA_URL", "http://localhost:8100")
OLLAMA_MODEL = "llama3.1:8b"
KNOWLEDGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "knowledge"))
COLLECTION_NAME = "mechmind_machinery_knowledge"

_chroma_client = None
_collection = None
_embedding_fn = None


def get_embedding_function():
    global _embedding_fn
    if _embedding_fn is None:
        try:
            _embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        except Exception as e:
            logger.error(f"Error initializing DefaultEmbeddingFunction: {e}")
            _embedding_fn = None
    return _embedding_fn


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        try:
            host = "localhost"
            port = 8100
            if "://" in CHROMA_URL:
                parts = CHROMA_URL.split("://")[1].split(":")
                host = parts[0]
                if len(parts) > 1:
                    port = int(parts[1].split("/")[0])
            _chroma_client = chromadb.HttpClient(host=host, port=port)
            _chroma_client.heartbeat()
            logger.info(f"Connected to ChromaDB HTTP at {host}:{port}")
        except Exception as e:
            logger.warning(f"Could not connect to ChromaDB HTTP ({e}), using local PersistentClient")
            local_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "chroma_data"))
            _chroma_client = chromadb.PersistentClient(path=local_db_path)
    return _chroma_client


def get_or_create_collection():
    global _collection
    if _collection is not None:
        return _collection
    client = get_chroma_client()
    emb_fn = get_embedding_function()
    try:
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=emb_fn,
            metadata={"description": "Heavy Machinery Diagnostic Manuals and Fault Codes"}
        )
        count = _collection.count()
        logger.info(f"Collection ready. Count: {count}")
    except Exception as e:
        logger.error(f"Failed to get/create ChromaDB collection: {e}")
        _collection = None
    return _collection


def chunk_document(content: str, filename: str) -> List[Dict[str, Any]]:
    chunks = []
    sections = re.split(r'\n(?=#{2,4}\s)', content)
    doc_title = os.path.splitext(filename)[0].replace("_", " ").title()
    for idx, sec in enumerate(sections):
        sec_text = sec.strip()
        if not sec_text or len(sec_text) < 40:
            continue
        first_line = sec_text.split("\n")[0].strip("# ")
        if len(sec_text) > 1200:
            paragraphs = sec_text.split("\n\n")
            sub_chunk = ""
            sub_idx = 0
            for p in paragraphs:
                if len(sub_chunk) + len(p) < 900:
                    sub_chunk += "\n\n" + p
                else:
                    if sub_chunk.strip():
                        chunks.append({
                            "id": f"{filename}_{idx}_{sub_idx}",
                            "text": f"Source: {doc_title} - {first_line}\n\n{sub_chunk.strip()}",
                            "metadata": {"source": filename, "title": first_line, "doc_title": doc_title}
                        })
                        sub_idx += 1
                    sub_chunk = p
            if sub_chunk.strip():
                chunks.append({
                    "id": f"{filename}_{idx}_{sub_idx}",
                    "text": f"Source: {doc_title} - {first_line}\n\n{sub_chunk.strip()}",
                    "metadata": {"source": filename, "title": first_line, "doc_title": doc_title}
                })
        else:
            chunks.append({
                "id": f"{filename}_{idx}",
                "text": f"Source: {doc_title} - {first_line}\n\n{sec_text}",
                "metadata": {"source": filename, "title": first_line, "doc_title": doc_title}
            })
    return chunks


def ingest_knowledge_base() -> Dict[str, Any]:
    collection = get_or_create_collection()
    if not collection:
        return {"status": "error", "message": "ChromaDB collection unavailable"}
    md_files = glob.glob(os.path.join(KNOWLEDGE_DIR, "*.md")) + glob.glob(os.path.join(KNOWLEDGE_DIR, "*.txt"))
    if not md_files:
        return {"status": "warning", "message": "No files found", "files": 0, "chunks": 0}
    all_chunks = []
    for fpath in md_files:
        fname = os.path.basename(fpath)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content_txt = f.read()
            all_chunks.extend(chunk_document(content_txt, fname))
        except Exception as e:
            logger.error(f"Error reading file {fpath}: {e}")
    if not all_chunks:
        return {"status": "warning", "message": "No chunks extracted", "chunks": 0}
    batch_size = 50
    upserted_count = 0
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        try:
            collection.upsert(
                ids=[c["id"] for c in batch],
                documents=[c["text"] for c in batch],
                metadatas=[c["metadata"] for c in batch]
            )
            upserted_count += len(batch)
        except Exception as e:
            logger.error(f"Error upserting batch: {e}")
    logger.info(f"Ingested {upserted_count} chunks from {len(md_files)} files")
    return {"status": "success", "files_ingested": len(md_files), "chunks_upserted": upserted_count, "total_collection_count": collection.count()}


def retrieve_context(query: str, top_k: int = 4) -> str:
    collection = get_or_create_collection()
    if not collection:
        return ""
    try:
        exact_docs = []
        exact_ids = set()
        spn_fmi_match = re.search(r'SPN\s*(\d+)\s*(?:FMI|\/)\s*(\d+)', query, re.IGNORECASE)
        if spn_fmi_match:
            target_id = f"j1939_spn_{spn_fmi_match.group(1)}_fmi_{spn_fmi_match.group(2)}"
            try:
                matched_item = collection.get(ids=[target_id])
                if matched_item and matched_item.get("documents") and len(matched_item["documents"]) > 0:
                    exact_docs.append(matched_item["documents"][0])
                    exact_ids.add(target_id)
                    logger.info(f"Pinned exact alphanumeric fault code match: {target_id}")
            except Exception as id_err:
                logger.debug(f"Direct ID lookup yielded no match: {id_err}")
        q_lower = query.lower()
        excluded_brand = None
        if "sany" in q_lower or "sy215" in q_lower:
            excluded_brand = "XCMG"
        elif "xcmg" in q_lower or "xe215" in q_lower:
            excluded_brand = "SANY"
        query_k = min(max(1, top_k - len(exact_docs)) + len(exact_ids) + 6, collection.count())
        results = collection.query(query_texts=[query], n_results=query_k)
        raw_docs = results.get("documents", [[]])[0]
        raw_ids = results.get("ids", [[]])[0]
        raw_metas = results.get("metadatas", [[]])[0]
        final_docs = list(exact_docs)
        for doc_text, doc_id, meta in zip(raw_docs, raw_ids, raw_metas):
            if doc_id in exact_ids:
                continue
            if excluded_brand:
                if (excluded_brand in str(meta.get("equipment_model", "")).upper() or
                        excluded_brand in str(meta.get("source", "")).upper() or
                        excluded_brand in str(doc_id).upper() or
                        excluded_brand in str(doc_text[:200]).upper()):
                    continue
            if doc_text not in final_docs:
                final_docs.append(doc_text)
            if len(final_docs) >= top_k:
                break
        if not final_docs:
            return ""
        parts = []
        for i, doc in enumerate(final_docs, 1):
            parts.append(f"--- REFERENCE PASSAGE {i} ---\n{doc.strip()}")
        return "\n\n".join(parts)
    except Exception as e:
        logger.error(f"ChromaDB retrieval query failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# SYSTEM PROMPTS
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are MechMind AI, an expert heavy construction machinery diagnostic assistant. "
    "You assist field mechanics, site supervisors, and operators in troubleshooting excavators, "
    "wheel loaders, tower cranes, and diesel powertrains.\n\n"
    "When given sensor telemetry, fault codes, or symptom descriptions:\n"
    "1. Analyze the mechanical symptoms, telemetry parameters, and physics.\n"
    "2. Formulate probable root causes (ranked by likelihood).\n"
    "3. Recommend immediate corrective and inspection actions.\n"
    "4. Suggest preventive maintenance steps with specific service intervals (hours).\n"
    "5. Ground your answer strictly in the provided engineering reference passages when available.\n\n"
    "CRITICAL SPECIFICATION INTEGRITY AND SAFETY RULES (ANTI-CROSS-WIRING):\n"
    "- COMPONENT INTEGRITY: Never transfer, assume, or substitute a torque specification, pressure rating, "
    "fluid capacity, or electrical tolerance from one component to another.\n"
    "- FASTENER AND COMPONENT SPECIFICATION INTEGRITY: Track shoe bolts, drive sprocket bolts, track roller bolts, "
    "cylinder pin bolts, and pump flange bolts are distinct mechanical components. NEVER substitute torque or "
    "pressure ratings between component types. If the exact queried component is not in the retrieved documentation, "
    "you MUST refuse and abstain immediately.\n"
    "- CANONICAL ACRONYM AND SYNONYM EQUIVALENCE: Treat standard machinery abbreviations as identical to full names "
    "(MCV=Main Control Valve, MRV=Main Relief Valve, CAC=Charge Air Cooler, HPFP=High Pressure Fuel Pump, "
    "DPF=Diesel Particulate Filter, ECM/ECU=Electronic Control Module).\n"
    "- TABLE SPECIFICATION DISAMBIGUATION: Match the exact component row in specification tables. "
    "Do not substitute values from narrative text.\n"
    "- MANDATORY ABSTENTION ON MISSING SPECIFICATIONS: If the requested specification is not in the retrieved "
    "passages, state exactly: 'This specification is not listed in the retrieved technical reference documentation. "
    "Do not substitute torque or pressure ratings from other components, as under- or over-torquing can cause "
    "catastrophic failure or injury. Consult the official OEM service manual.'\n"
    "- DISTRACTOR SUPPRESSION: When abstaining, NEVER cite numeric values from other components.\n\n"
    "STRICT FORMATTING RULES:\n"
    "- DO NOT USE EMOJIS ANYWHERE IN YOUR RESPONSE.\n"
    "- Use clean Markdown headers (*Probable Causes:*, *Immediate Actions:*, *Preventive Maintenance:*).\n"
    "- Use hyphenated bullet lists.\n"
    "- Be concise, direct, authoritative, and technically precise."
)

CHAT_SYSTEM_PROMPT = (
    "You are MechMind AI, an AI-powered diagnostic assistant for heavy construction machinery. "
    "You work with field mechanics, site supervisors, and equipment operators on construction sites.\n\n"
    "For greetings, introductions, and questions about what you can do, respond naturally and helpfully "
    "in plain conversational language.\n\n"
    "You can help with:\n"
    "- Diagnosing faults from fault codes (SPN/FMI J1939), symptoms, or sensor readings\n"
    "- Hydraulic, powertrain, and undercarriage troubleshooting\n"
    "- Preventive maintenance schedules and service intervals\n"
    "- Emergency safety procedures (boom hose burst, brake failure, overheating)\n"
    "- Equipment from SANY, XCMG, CAT, Komatsu, Zoomlion, and more\n"
    "- Real-time sensor alerts from on-site ESP32 monitoring nodes\n\n"
    "Keep replies short, friendly, and professional. Do not use emojis."
)


# ---------------------------------------------------------------------------
# INTENT CLASSIFIER
# ---------------------------------------------------------------------------

_CONVERSATIONAL_PATTERNS = [
    r"^(hi|hello|hey|howdy|good\s?(morning|afternoon|evening|day)|salaam|salam|oga|boss)\b",
    r"\bwho\s+are\s+(you|u)\b",
    r"\bwhat\s+are\s+you\b",
    r"\bwhat\s+is\s+(your\s+name|mechmind)\b",
    r"\byour\s+name\b",
    r"\bintroduce\s+yourself\b",
    r"\bwhat\s+can\s+you\s+do\b",
    r"\bwhat\s+do\s+you\s+do\b",
    r"\bhow\s+(can|do)\s+you\s+help\b",
    r"\bwhat\s+are\s+your\s+(capabilities|features|functions)\b",
    r"\bhelp\s+me\b",
    r"^(ok|okay|thanks|thank\s+you|thx|alright|cool|great|nice|good)\b",
    r"^(yes|no|nope|yep|yup|sure)\s*\.?\s*$",
    r"^how\s+are\s+you\b",
    r"^are\s+you\s+(there|online|working|active)\b",
    r"^(test|testing)\b",
    r"^ping\b",
]

_CONVERSATIONAL_RE = re.compile("|".join(_CONVERSATIONAL_PATTERNS), flags=re.IGNORECASE)

_TECHNICAL_RE = re.compile(
    r"\b(spn|fmi|psi|mpa|rpm|bar|temperature|pressure|vibration|hydraulic|engine|"
    r"pump|valve|cylinder|fault|error|alarm|sensor|oil|fuel|coolant|torque|"
    r"excavator|loader|crane|dozer|generator|bearing|hose|leak|noise|smoke|"
    r"overheating|stall|start|code|diagnostic|maintenance|filter|battery|alternator|"
    r"sany|xcmg|cat|komatsu|zoomlion|sy215|xe215|boom|bucket|track|undercarriage|"
    r"swing|slew|travel|throttle|turbo|injector|dpf|egr|ecm|ecu)\b",
    flags=re.IGNORECASE
)


def classify_intent(query: str) -> str:
    """
    Route query to 'conversational' or 'diagnostic'.

    Priority:
    1. Technical keyword present  -> diagnostic
    2. Conversational pattern     -> conversational
    3. Short message (<= 6 words) -> conversational
    4. Default                    -> diagnostic
    """
    q = query.strip()
    if _TECHNICAL_RE.search(q):
        return "diagnostic"
    if _CONVERSATIONAL_RE.search(q):
        return "conversational"
    if len(q.split()) <= 6:
        return "conversational"
    return "diagnostic"


# ---------------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------------

def strip_emojis(text: str) -> str:
    emoji_pattern = re.compile(
        "[\U00010000-\U0010ffff"
        "\U00002600-\U000027bf"
        "\U00002300-\U000023ff"
        "\U00002b50-\U00002b55"
        "\U0000203c-\U00002049"
        "\U000025a0-\U000025ff"
        "\U00002700-\U000027bf"
        "\U0000fe00-\U0000fe0f"
        "\U0001f300-\U0001f5ff"
        "\U0001f600-\U0001f64f"
        "\U0001f680-\U0001f6ff"
        "\U0001f700-\U0001f77f"
        "\U0001f780-\U0001f7ff"
        "\U0001f800-\U0001f8ff"
        "\U0001f900-\U0001f9ff"
        "\U0001fa00-\U0001fa6f"
        "\U0001fa70-\U0001faff]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub("", text)


def _call_ollama(system_prompt: str, user_prompt: str) -> str:
    """Shared Ollama inference — llama3.1:8b only, zero cloud fallback."""
    model_name = "llama3.1:8b"
    try:
        response = ollama.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        if hasattr(response, "message") and hasattr(response.message, "content"):
            return response.message.content
        elif isinstance(response, dict):
            return response.get("message", {}).get("content", "")
        return ""
    except Exception as e:
        logger.error(f"Ollama call failed with {model_name}: {e}")
        return f"Diagnostic service unavailable: {e}"


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------

def diagnose_with_rag(query_text: str, sensor_context: str = "") -> str:
    """
    Intent-routed RAG engine.

    CONVERSATIONAL (greetings, identity, capability, small talk):
      - No ChromaDB retrieval
      - Permissive CHAT_SYSTEM_PROMPT, no abstention rules
      - Fast response path

    DIAGNOSTIC (fault codes, symptoms, specs, sensor data):
      - Full ChromaDB retrieval with SPN pinning and brand isolation
      - Strict SYSTEM_PROMPT with safety and abstention rules
      - Sensor telemetry context injected when available
    """
    intent = classify_intent(query_text)
    logger.info(f"Intent: '{intent}' | Query: '{query_text[:70]}'")

    # -- CONVERSATIONAL PATH --------------------------------------------------
    if intent == "conversational":
        return strip_emojis(_call_ollama(CHAT_SYSTEM_PROMPT, query_text)).strip()

    # -- DIAGNOSTIC PATH (full RAG) -------------------------------------------
    retrieved_context = retrieve_context(query_text, top_k=4)
    prompt_parts = []
    if retrieved_context:
        prompt_parts.append(f"[TECHNICAL REFERENCE MANUALS AND FAULT CODES]\n{retrieved_context}")
    if sensor_context:
        prompt_parts.append(f"[LIVE TELEMETRY AND RECENT ALERTS]\n{sensor_context}")
    prompt_parts.append(f"[EQUIPMENT SYMPTOMS / OPERATOR QUERY]\n{query_text}")
    return strip_emojis(_call_ollama(SYSTEM_PROMPT, "\n\n".join(prompt_parts))).strip()


# Alias for backward compatibility
query_rag = diagnose_with_rag
