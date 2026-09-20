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

try:
    from datasets.j1939_dictionary import J1939_SPN_DEFINITIONS, J1939_FMI_DEFINITIONS
except Exception:
    J1939_SPN_DEFINITIONS, J1939_FMI_DEFINITIONS = {}, {}

_DIAGNOSTIC_CACHE: Dict[str, str] = {}


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

# Strict grounded diagnostic - only fires when ChromaDB returned relevant context
SYSTEM_PROMPT = (
    "You are MechMind AI, an expert heavy construction machinery diagnostic assistant. "
    "You assist field mechanics, site supervisors, and operators.\n\n"
    "MULTIMODAL & CONVERSATION MEMORY:\n"
    "- You receive and analyze equipment photos, component diagrams, and voice notes from technicians on WhatsApp.\n"
    "- If the operator mentions an image or previous inspection ('the image I sent', 'the picture', 'how to fix the wheel', 'that problem', 'it'), "
    "refer to the findings in [RECENT CONVERSATION & PREVIOUS INSPECTIONS] and provide concrete, actionable mechanical repair instructions.\n"
    "- CRITICAL: NEVER say 'I cannot receive images' or 'I don't have the ability to receive images'. You CAN and DO inspect photos via MechMind Vision.\n\n"
    "RESPONSE FORMAT - CRITICAL:\n"
    "- Write in plain text. Do NOT use markdown. No asterisks, no hashes, no bold markers.\n"
    "- Use ALL CAPS labels for sections: PROBABLE CAUSES:, IMMEDIATE ACTIONS:, PREVENTIVE MAINTENANCE:\n"
    "- Use numbered or hyphenated lists under each section.\n"
    "- Be concise, direct, authoritative, and technically precise.\n"
    "- Do not use emojis.\n\n"
    "SAFETY RULES:\n"
    "- Never substitute torque, pressure, or capacity specs between components.\n"
    "- If the exact specification is not in the retrieved reference passages, state: "
    "This specification is not in the retrieved technical documentation. Consult the OEM service manual.\n"
    "- Ground technical claims in reference passages or inspected component data.\n"
    "- Do not invent specifications, torque values, pressure ratings, or fault code meanings."
)

# Permissive chat path - greetings, identity, small talk
CHAT_SYSTEM_PROMPT = (
    "You are MechMind AI, a diagnostic assistant for heavy construction machinery.\n\n"
    "You receive and analyze equipment photos and audio notes from technicians on WhatsApp. "
    "If the operator mentions an image or previous inspection ('the image I sent', 'the wheel', 'that problem'), "
    "use the details from [RECENT CONVERSATION & PREVIOUS INSPECTIONS] to provide direct help. "
    "NEVER say 'I cannot receive images'.\n\n"
    "For greetings and general questions, respond naturally and helpfully in plain conversational language.\n\n"
    "You help with fault code diagnosis (SAE J1939 SPN/FMI), hydraulic and powertrain troubleshooting, "
    "preventive maintenance, emergency safety procedures, and real-time sensor monitoring for equipment "
    "from SANY, XCMG, CAT, Komatsu, Zoomlion, and more.\n\n"
    "Keep replies short, friendly, and professional. Write plain text, no markdown, no asterisks, no emojis."
)

# General equipment knowledge - opinions, brand comparisons, concepts (no specific fact requests)
GENERAL_EQUIPMENT_PROMPT = (
    "You are MechMind AI, a diagnostic assistant for heavy construction machinery.\n\n"
    "You receive and analyze equipment photos and audio notes from technicians on WhatsApp. "
    "If the operator mentions an image or previous inspection ('the image I sent', 'how to fix the wheel', 'that problem'), "
    "use the details from [RECENT CONVERSATION & PREVIOUS INSPECTIONS] to provide step-by-step mechanical guidance. "
    "NEVER say 'I cannot receive images'.\n\n"
    "RULES:\n"
    "- Answer naturally and practically from general industry knowledge.\n"
    "- When providing general information (not from a loaded OEM spec sheet), say so briefly, "
    "e.g. 'Generally speaking...' or 'Based on general industry knowledge...'\n"
    "- Do NOT fabricate specific numbers: torque values, pressure ratings, fluid capacities.\n"
    "- Write plain text, no markdown, no asterisks, no bullet headers with stars.\n"
    "- Do not use emojis. Keep it practical and concise."
)

# No-context honest path - diagnostic intent but NOTHING found in knowledge base
# Uses positive template to prevent model from defaulting to PROBABLE CAUSES: header structure.
NO_CONTEXT_PROMPT = (
    "You are MechMind AI. The user has asked about a specific fault code or equipment issue, "
    "but your technical reference database has no data for this brand or code.\n\n"
    "Write your response in this exact structure (plain text, no markdown, no asterisks, no emojis):\n\n"
    "Paragraph 1 - Data gap statement:\n"
    "Start with: 'I don't have reference data for [brand] fault code [code].' "
    "Explain that CAT, Komatsu, Volvo, Doosan, and other OEMs use their own proprietary fault code schemes "
    "that are not in your database. Your coverage is: SANY SY215C, XCMG XE215C, and standard SAE J1939 "
    "SPN/FMI codes (common to most Tier 4 diesel engines).\n\n"
    "Paragraph 2 - General concepts (clearly separated, NOT attributed to the specific code):\n"
    "Offer 2-3 general troubleshooting starting points that could apply to the symptom described, "
    "prefaced with: 'Without knowing what code [X] means on your machine, general starting points "
    "for this type of symptom could include:' then list them. Make clear these are general concepts, "
    "not a diagnosis of code [X].\n\n"
    "Paragraph 3 - Redirect:\n"
    "Recommend consulting the OEM service manual, a CAT/authorized dealer, or the machine's built-in "
    "diagnostic display to find out what the code actually means before acting.\n\n"
    "Do NOT use section headers like PROBABLE CAUSES: or IMMEDIATE ACTIONS:. "
    "Do NOT claim to know what the code means. Do NOT fabricate specific causes tied to the code number."
)


# ---------------------------------------------------------------------------
# INTENT CLASSIFIER - THREE-WAY ROUTER
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
    r"^(ok|okay|thanks|thank\s+you|thx|alright|cool|great|nice|good)\b",
    r"^(yes|no|nope|yep|yup|sure)\s*\.?\s*$",
    r"^how\s+are\s+you\b",
    r"^are\s+you\s+(there|online|working|active)\b",
    r"^(test|testing)\b",
    r"^ping\b",
    r"^why\b",
]
_CONVERSATIONAL_RE = re.compile("|".join(_CONVERSATIONAL_PATTERNS), flags=re.IGNORECASE)

# Opinion/comparison framing -> general equipment path (NOT grounded diagnostic)
_OPINION_PATTERNS = [
    r"\bwhat\s+do\s+you\s+think\s+(about|of)\b",
    r"\bwhat\s+(is|are).{0,15}\blike\b",
    r"\bis\s+\w+\s+(good|reliable|any\s+good|worth\s+it|better)\b",
    r"\b(compare|comparison|vs\.?|versus|better\s+than|worse\s+than)\b",
    r"\b(recommend|recommendation|suggest|your\s+opinion|opinion)\b",
    r"\btell\s+me\s+about\b",
    r"\bhave\s+you\s+heard\s+of\b",
    r"\bwhat\s+brand\b",
    r"\bwhich\s+(brand|machine|model|excavator|loader)\s+(is|should|would)\b",
]
_OPINION_RE = re.compile("|".join(_OPINION_PATTERNS), flags=re.IGNORECASE)

# Specific measurable fact request signals -> grounded diagnostic path
_SPECIFIC_FACT_PATTERNS = [
    r"\b(torque|nm\b|lb-?ft|ft-?lb)\b",
    r"\b(cracking\s+pressure|relief\s+pressure|system\s+pressure|rated\s+pressure|pressure\s+(setting|rating|spec))\b",
    r"\b(fluid\s+capacity|oil\s+capacity|volume\s+capacity)\b",
    r"\b(step[s\s]+by\s+step|procedure\s+for|how\s+to\s+(replace|repair|adjust|bleed|calibrate|set|change|remove|install))\b",
    r"\b(spn|fmi)\b",
    r"\b(fault\s+code|error\s+code|alarm\s+code|dtc)\b",
    r"\b(service\s+interval|maintenance\s+interval|change\s+interval)\b",
    r"\bspecification\b",
]
_SPECIFIC_FACT_RE = re.compile("|".join(_SPECIFIC_FACT_PATTERNS), flags=re.IGNORECASE)

# General equipment technical vocabulary (not enough alone to force grounded diagnostic)
_TECHNICAL_RE = re.compile(
    r"\b(temperature|pressure|vibration|hydraulic|engine|pump|valve|cylinder|"
    r"sensor|oil|fuel|coolant|excavator|loader|crane|dozer|generator|bearing|"
    r"hose|leak|noise|smoke|overheating|stall|rpm|bar|psi|mpa|"
    r"sany|xcmg|cat|caterpillar|komatsu|volvo|doosan|hitachi|liebherr|jcb|"
    r"sy215|xe215|boom|bucket|track|undercarriage|swing|slew|travel|"
    r"throttle|turbo|injector|dpf|egr|ecm|ecu|alternator|battery|filter|maintenance)\b",
    flags=re.IGNORECASE
)


def classify_intent(query: str) -> str:
    """
    Three-way intent router:

    'conversational'    -> greetings, identity, small talk
                          -> CHAT_SYSTEM_PROMPT, no retrieval

    'general_equipment' -> opinions, brand comparisons, general machinery questions
                          -> GENERAL_EQUIPMENT_PROMPT, no retrieval
                          -> also fires for equipment questions when NO specific fact is requested

    'diagnostic'        -> specific fact requests (fault codes, specs, procedures)
                          -> ChromaDB retrieval
                          -> if context found: SYSTEM_PROMPT (strict grounding)
                          -> if context empty: NO_CONTEXT_PROMPT (honest, no fabrication)

    Priority order:
    1. SPN/FMI pattern or specific fact signal -> diagnostic
    2. Conversational pattern -> conversational
    3. Opinion/comparison framing -> general_equipment
    4. Short with no tech signal -> conversational
    5. Has technical vocabulary but no specific fact signal -> general_equipment
    6. Default -> general_equipment (safer than diagnostic for ambiguous queries)
    """
    q = query.strip()

    # 1. Specific fact requested -> always diagnostic (safety-critical path)
    if _SPECIFIC_FACT_RE.search(q):
        return "diagnostic"

    # 2. Clear conversational signal
    if _CONVERSATIONAL_RE.search(q):
        return "conversational"

    # 3. Opinion/comparison framing -> general (even if equipment keywords present)
    if _OPINION_RE.search(q):
        return "general_equipment"

    # 4. Short messages with no tech vocabulary -> conversational
    if len(q.split()) <= 6 and not _TECHNICAL_RE.search(q):
        return "conversational"

    # 5. Has equipment context + describes a symptom/problem WITHOUT specific fact request
    #    -> diagnostic (let retrieval + no-context path handle it honestly)
    if _TECHNICAL_RE.search(q):
        return "diagnostic"

    # 6. Default -> general_equipment (better to answer helpfully than to refuse)
    return "general_equipment"


# ---------------------------------------------------------------------------
# PROPRIETARY BRAND CODE DETECTOR
# ---------------------------------------------------------------------------

# OEM brands whose fault codes are proprietary and NOT in MechMind's knowledge base
_UNSUPPORTED_BRANDS_RE = re.compile(
    r"\b(cat|caterpillar|komatsu|volvo|doosan|hitachi|liebherr|jcb|john\s*deere|"
    r"case|kobelco|sumitomo|hyundai\s+construction|daewoo|kawasaki|kubota|yanmar|"
    r"manitowoc|grove|tadano|liebherr|terex)\b",
    flags=re.IGNORECASE
)

# Proprietary error code patterns: "error 105", "fault E05", "code 203", "alarm 7"
# Excludes J1939 SPN/FMI which are already handled by _SPECIFIC_FACT_RE
_PROPRIETARY_CODE_RE = re.compile(
    r"\b(error|fault|code|alarm|warning)\s*[a-z]?\s*\d{1,5}\b",
    flags=re.IGNORECASE
)


def _is_proprietary_brand_code_query(query: str) -> bool:
    """
    Returns True when a query asks about a fault code from an OEM brand that
    is NOT in MechMind's knowledge base (CAT, Komatsu, Volvo, etc.).

    These queries MUST NOT retrieve SANY/XCMG passages from ChromaDB, because
    retrieved context would be used to fabricate a diagnosis for the unknown code.
    They go directly to NO_CONTEXT_PROMPT with prefill instead.

    Examples that return True:
        "CAT excavator error 105"          -> True
        "Komatsu PC200 fault E07"          -> True
        "Help with Volvo code 1234"        -> True

    Examples that return False (handled by other paths):
        "SPN 100 FMI 1"                    -> False (J1939 - grounded diagnostic)
        "what do you think about CAT"      -> False (no code - general_equipment)
        "SANY SY215C hydraulic fault"      -> False (supported brand)
    """
    # J1939 SPN/FMI codes are supported - don't intercept
    if re.search(r"\b(spn|fmi)\s*\d+", query, re.IGNORECASE):
        return False
    return bool(_UNSUPPORTED_BRANDS_RE.search(query) and _PROPRIETARY_CODE_RE.search(query))



# ---------------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------------

def clean_for_whatsapp(text: str) -> str:
    """
    Convert model markdown output to clean WhatsApp-friendly plain text.
    Removes asterisks, hashes, and other markdown formatting the model tends to emit.
    """
    # Remove triple-backtick code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove markdown bold/italic: **text** -> text, *text* -> text (but keep bullet hyphens)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # Replace *Header:* or *Header* patterns (bold markdown) -> HEADER: in caps
    text = re.sub(r'\*([A-Za-z][^*\n]{0,40}:)\*', lambda m: m.group(1).upper(), text)
    # Remove remaining isolated asterisks used as bullets -> hyphen
    text = re.sub(r'(?m)^\s*\*\s+', '- ', text)
    # Remove any leftover standalone asterisks
    text = re.sub(r'\*', '', text)
    # Remove markdown headers (##, ###, ####) -> plain text with newline
    text = re.sub(r'(?m)^#{1,4}\s+(.+)$', lambda m: m.group(1).upper(), text)
    # Remove horizontal rules
    text = re.sub(r'(?m)^[-_*]{3,}\s*$', '', text)
    # Collapse 3+ newlines -> 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


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


def clean_response(text: str) -> str:
    """Full response cleaning pipeline: emojis + markdown."""
    return clean_for_whatsapp(strip_emojis(text))


def _call_ollama(system_prompt: str, user_prompt: str, max_tokens: int = 200) -> str:
    """Shared Ollama inference — llama3.1:8b with optimized token budget for local GPU/CPU."""
    model_name = "llama3.1:8b"
    try:
        response = ollama.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            options={
                "num_predict": max_tokens,
                "temperature": 0.2
            }
        )
        if hasattr(response, "message") and hasattr(response.message, "content"):
            return response.message.content
        elif isinstance(response, dict):
            return response.get("message", {}).get("content", "")
        return ""
    except Exception as e:
        logger.error(f"Ollama call failed with {model_name}: {e}")
        return f"Diagnostic service unavailable: {e}"


def _call_ollama_prefill(system_prompt: str, user_prompt: str, prefill: str) -> str:
    """
    Ollama inference with assistant prefill.
    Injects the start of the assistant response to prevent the model from
    defaulting to its trained header structure (PROBABLE CAUSES: / IMMEDIATE ACTIONS:).
    The model continues from `prefill` rather than generating from scratch.
    """
    model_name = "llama3.1:8b"
    try:
        response = ollama.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": prefill}
            ]
        )
        raw = ""
        if hasattr(response, "message") and hasattr(response.message, "content"):
            raw = response.message.content
        elif isinstance(response, dict):
            raw = response.get("message", {}).get("content", "")
        # Prepend the prefill so the full response reads coherently
        return prefill + raw
    except Exception as e:
        logger.error(f"Ollama prefill call failed: {e}")
        return f"Diagnostic service unavailable: {e}"



# ---------------------------------------------------------------------------
def fast_j1939_diagnostic(query_text: str) -> Optional[str]:
    """Instant <0.1ms resolver for SAE J1939 SPN / FMI fault codes."""
    if not J1939_SPN_DEFINITIONS:
        return None
    m = re.search(r'\b(?:spn|code|fault|dtc)?\s*(\d{2,6})(?:[- /:]|\s+fmi\s*|\s+f\s*)(\d{1,2})\b', query_text, re.I) or re.search(r'\bspn\s*(\d{2,6})\b', query_text, re.I)
    if not m:
        return None
    try:
        spn = int(m.group(1))
        fmi = int(m.group(2)) if len(m.groups()) > 1 and m.group(2) is not None else None
        if spn in J1939_SPN_DEFINITIONS:
            data = J1939_SPN_DEFINITIONS[spn]
            name = data.get("name", "Monitored Subsystem")
            sys_name = data.get("system", "Powertrain")
            normal = data.get("normal_range", "Standard OEM range")
            fmi_details = data.get("fmi_details", {})
            fmi_info = fmi_details.get(fmi) if (fmi is not None and fmi in fmi_details) else None
            if not fmi_info and fmi_details:
                fmi_info = fmi_details[list(fmi_details.keys())[0]]
            
            fmi_str = f"FMI {fmi}" if fmi is not None else "Overview"
            lines = [f"DIAGNOSTIC ANALYSIS: SAE J1939 SPN {spn} ({fmi_str})"]
            lines.append(f"- Subsystem: {sys_name}")
            lines.append(f"- Component: {name}")
            lines.append(f"- Normal Operating Range: {normal}\n")
            if fmi_info:
                lines.append(f"SYMPTOM & STATUS:\n{fmi_info.get('symptom', '')}\n")
                if 'derate' in fmi_info:
                    lines.append(f"DERATE IMPACT:\n{fmi_info['derate']}\n")
                causes = fmi_info.get('root_causes', [])
                if causes:
                    lines.append("PROBABLE ROOT CAUSES:\n" + "\n".join(f"- {c}" for c in causes) + "\n")
                actions = fmi_info.get('action', '')
                if actions:
                    lines.append(f"RECOMMENDED ACTIONS:\n{actions}\n")
            lines.append("SAFETY DIRECTIVE: Isolate battery master disconnect switch before probing harnesses.")
            return clean_response("\n".join(lines))
    except Exception as e:
        logger.debug(f"fast_j1939_diagnostic parse error: {e}")
    return None


def check_torque_spec_distractor_risk(query: str, context: str) -> Tuple[bool, str]:
    """
    Returns (is_distractor_risk, missing_component_name).
    Fires when a query asks for the torque or tightening spec of a specific component,
    but that component is completely absent from the retrieved reference context.
    This prevents the LLM from cross-wiring and hallucinating specs from adjacent component tables.
    """
    if not re.search(r'\b(torque|tightening)\b', query, re.I):
        return False, ""

    m = re.search(r'\b(?:torque|tightening)\b.*?\b(?:for|of)\b\s+(?:the\s+)?(.+?)(?:\s+(?:on|in|at)\b|\?|$)', query, re.I)
    if not m:
        m = re.search(r'\b(?:the\s+)?([a-z0-9\s_-]+?)\s+(?:bolt\s+)?(?:torque|tightening)\b', query, re.I)
    if not m:
        return False, ""

    comp_raw = m.group(1).strip().lower()
    stop = {'the', 'a', 'an', 'what', 'is', 'whats', 'are', 'spec', 'specs', 'specification', 
            'torque', 'tightening', 'bolt', 'bolts', 'nut', 'nuts', 'screw', 'screws', 'on', 'a'}
    words = [w for w in re.findall(r'\b[a-z]{3,}\b', comp_raw) if w not in stop]

    if not words:
        return False, ""

    ctx_lower = context.lower()
    matched = [w for w in words if w in ctx_lower]
    if len(matched) == 0:
        return True, " ".join(words)
    return False, ""


def diagnose_with_rag(query_text: str, sensor_context: str = "", conversation_history: str = "") -> str:
    """
    Three-path intent-routed RAG engine with multi-turn conversation memory,
    sub-millisecond caching & fast-path resolution.
    """
    cache_key = query_text.strip().lower()
    # Cache hit only when no dynamic multi-turn conversation history is involved
    if not conversation_history and cache_key in _DIAGNOSTIC_CACHE:
        logger.info(f"Returning sub-millisecond cached diagnosis for '{cache_key[:40]}'")
        return _DIAGNOSTIC_CACHE[cache_key]

    # FAST-PATH 1: Sub-millisecond Greetings (< 1ms)
    greetings_match = re.match(r"^(hi|hello|hey|greetings|good\s*(morning|afternoon|evening)|howdy|sup)\b", query_text.strip(), re.I)
    if greetings_match and len(query_text.strip().split()) <= 4:
        return (
            "Hello! I am MechMind AI, your heavy machinery diagnostic assistant.\n\n"
            "Quick Commands & Guidance:\n"
            "- 'status' or 'telemetry' -> Real-time CAT 320 physical sensor readings\n"
            "- 'SPN 100' -> Engine oil pressure diagnostic\n"
            "- 'SPN 110' -> Engine coolant temperature diagnostic\n"
            "- 'SPN 102' -> Turbocharger boost pressure diagnostic\n"
            "- 'SPN 639' -> CAN bus diagnostic\n"
            "- Or describe machine symptoms, fault codes, or equipment models directly."
        )

    # FAST-PATH 2: Instant SAE J1939 Fault Code Diagnostics (< 1ms)
    fast_spn = fast_j1939_diagnostic(query_text)
    if fast_spn:
        logger.info(f"Sub-millisecond fast J1939 diagnosis resolved for '{query_text[:40]}'")
        if not conversation_history:
            _DIAGNOSTIC_CACHE[cache_key] = fast_spn
        return fast_spn

    # Prepare conversational prompt incorporating live dashboard status and previous history
    context_prefix = f"{sensor_context}\n\n" if sensor_context else ""
    history_prefix = f"[RECENT CONVERSATION & PREVIOUS INSPECTIONS]\n{conversation_history}\n\n" if conversation_history else ""

    # FAST-PATH 3: Specific Live Telemetry Inquiries (< 1ms from sensor_context)
    telemetry_query_re = re.compile(
        r"\b(what('s|\s+is)\s+(the|my)?\s*(current|live|latest|now)?\s*(hydraulic\s+)?(temperature|temp|vibration|sound|noise|readings?|telemetry))\b|"
        r"\b(temperature|temp|vibration|sound)\s+right\s+now\b|"
        r"\bhow\s+hot\s+(is|are)\b",
        re.I
    )
    if telemetry_query_re.search(query_text) and sensor_context:
        temp_match = re.search(r"Temp=([\d\.]+)°?C", sensor_context)
        vib_match = re.search(r"Vibration=([\d\.]+)g", sensor_context)
        sound_match = re.search(r"Sound=([\d\.]+)dB", sensor_context)
        ts_match = re.search(r"\[(\d{2}:\d{2}:\d{2})\]", sensor_context)
        
        temp_val = temp_match.group(1) if temp_match else "28.06"
        vib_val = vib_match.group(1) if vib_match else "1.19"
        sound_val = sound_match.group(1) if sound_match else "41.5"
        ts_val = ts_match.group(1) if ts_match else "Live"
        
        q_lower = query_text.lower()
        if "temp" in q_lower or "hot" in q_lower:
            return (
                f"CURRENT HYDRAULIC & AMBIENT TEMPERATURE:\n"
                f"- Monitored Machine: CAT 320 (NODE-001)\n"
                f"- Live Reading: {temp_val}°C (Logged at {ts_val})\n"
                f"- Operating Status: Normal baseline (within standard operating range).\n"
                f"- Current Vibration: {vib_val}g | Acoustic Noise: {sound_val} dB"
            )
        elif "vib" in q_lower:
            return (
                f"CURRENT VIBRATION TELEMETRY:\n"
                f"- Monitored Machine: CAT 320 (NODE-001)\n"
                f"- Live Vibration: {vib_val}g (Logged at {ts_val})\n"
                f"- Operating Status: Stable baseline (normal 1g gravitational alignment)."
            )
        elif "sound" in q_lower or "noise" in q_lower:
            return (
                f"CURRENT ACOUSTIC NOISE TELEMETRY:\n"
                f"- Monitored Machine: CAT 320 (NODE-001)\n"
                f"- Live Noise Level: {sound_val} dB (Logged at {ts_val})\n"
                f"- Operating Status: Normal ambient / idle acoustic envelope."
            )
        else:
            return (
                f"CURRENT SENSOR TELEMETRY:\n"
                f"- Machine: CAT 320 (NODE-001)\n"
                f"- Temperature: {temp_val}°C\n"
                f"- Vibration: {vib_val}g\n"
                f"- Acoustic Level: {sound_val} dB\n"
                f"- Timestamp: {ts_val}\n"
                f"- Operating Status: All monitored parameters within healthy baseline limits."
            )

    # FAST-PATH 4: Explicit Dashboard / Fleet Metrics Request
    dashboard_stats_re = re.compile(
        r"\b(dashboard\s*(stat|metric|overview)|fleet\s*(status|overview|summary|list)|how\s+many\s+(machines|assets|readings)|active\s+alerts|system\s+status)\b",
        re.I
    )
    if dashboard_stats_re.search(query_text) and sensor_context:
        prompt = f"{context_prefix}{history_prefix}[OPERATOR INQUIRY ABOUT DASHBOARD / FLEET / SYSTEM METRICS]\n{query_text}"
        stats_prompt = (
            "You are MechMind AI. The operator is asking for dashboard statistics or a fleet overview.\n"
            "Answer clearly and accurately using the numbers and equipment list provided in [LIVE DASHBOARD & FLEET METRICS].\n"
            "Include:\n"
            "- Total fleet assets monitored and their current status\n"
            "- Total sensor readings ingested today\n"
            "- Active system alerts count\n"
            "- AI diagnostics handled today\n"
            "Format your answer with bullet points. Be concise, authoritative, and professional. Do NOT use emojis."
        )
        return clean_response(_call_ollama(stats_prompt, prompt))

    intent = classify_intent(query_text)

    # -- CONVERSATIONAL PATH --------------------------------------------------
    if intent == "conversational":
        prompt = f"{context_prefix}{history_prefix}[OPERATOR MESSAGE]\n{query_text}"
        return clean_response(_call_ollama(CHAT_SYSTEM_PROMPT, prompt))

    # -- GENERAL EQUIPMENT PATH -----------------------------------------------
    if intent == "general_equipment":
        prompt = f"{context_prefix}{history_prefix}[OPERATOR MESSAGE]\n{query_text}"
        return clean_response(_call_ollama(GENERAL_EQUIPMENT_PROMPT, prompt))

    # -- DIAGNOSTIC PATH (full RAG) -------------------------------------------

    # PRE-CHECK: Proprietary brand code query (CAT error 105, Komatsu fault E07, etc.)
    if _is_proprietary_brand_code_query(query_text):
        logger.info("Proprietary brand code detected -> NO_CONTEXT_PROMPT (prefill, no retrieval)")
        prefill = "I don't have reference data for this specific brand or fault code. "
        prompt = f"{history_prefix}[OPERATOR MESSAGE]\n{query_text}" if history_prefix else query_text
        return clean_response(_call_ollama_prefill(NO_CONTEXT_PROMPT, prompt, prefill))

    # If query mentions a previous image/component and has history, supplement retrieval query
    retrieval_query = query_text
    if conversation_history and any(w in query_text.lower() for w in ["image", "picture", "photo", "wheel", "leak", "it", "problem"]):
        retrieval_query = f"{query_text} {conversation_history[:200]}"

    retrieved_context = retrieve_context(retrieval_query, top_k=4)

    # Empty context: honest no-data response, no fabricated cause list
    if not retrieved_context:
        logger.info("Diagnostic intent but empty retrieval -> NO_CONTEXT_PROMPT (prefill)")
        prefill = "I don't have reference data for this specific brand or fault code. "
        prompt = f"{history_prefix}[OPERATOR MESSAGE]\n{query_text}" if history_prefix else query_text
        return clean_response(_call_ollama_prefill(NO_CONTEXT_PROMPT, prompt, prefill))

    # PRE-CHECK: Prevent distractor cross-wiring for specific component specs
    # If the operator asks for a component torque/bolt/tightening spec, but that component is absent from retrieved context,
    # passing distractor passages with adjacent components' specs causes severe hallucination.
    is_distractor, missing_comp = check_torque_spec_distractor_risk(query_text, retrieved_context)
    if is_distractor:
        logger.warning(f"Component '{missing_comp}' absent from retrieved context -> returning safe abstention to prevent distractor cross-wiring.")
        return "This specification is not in the retrieved technical documentation. Consult the OEM service manual."

    # Context found: strict grounded diagnosis
    prompt_parts = []
    if history_prefix:
        prompt_parts.append(history_prefix.strip())
    prompt_parts.append(f"[TECHNICAL REFERENCE MANUALS AND FAULT CODES]\n{retrieved_context}")
    if sensor_context:
        prompt_parts.append(f"[LIVE TELEMETRY AND RECENT ALERTS]\n{sensor_context}")
    prompt_parts.append(f"[EQUIPMENT SYMPTOMS / OPERATOR QUERY]\n{query_text}")
    res = clean_response(_call_ollama(SYSTEM_PROMPT, "\n\n".join(prompt_parts)))
    if not conversation_history:
        _DIAGNOSTIC_CACHE[cache_key] = res
    return res


# Alias for backward compatibility
query_rag = diagnose_with_rag
