"""
MechMind AI - PDF Ingestion & Semantic Chunking Engine
Extracts text and tables from heavy machinery service manuals (PDFs)
with table preservation, OCR fallback for scanned pages, and domain-aware chunking.
"""

import os
import re
import io
import logging
from typing import List, Dict, Any, Optional, Tuple

import fitz  # PyMuPDF
import pdfplumber
from PIL import Image

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

logger = logging.getLogger("mechmind.ingestion.pdf")

# Regex patterns for equipment models and section headers
EQUIPMENT_PATTERNS = [
    r"\b(SANY\s+[A-Z0-9\-]+)\b",
    r"\b(XCMG\s+[A-Z0-9\-]+)\b",
    r"\b(SHANTUI\s+[A-Z0-9\-]+)\b",
    r"\b(CAT(?:ERPILLAR)?\s+[A-Z0-9\-]+)\b",
    r"\b(KOMATSU\s+[A-Z0-9\-]+)\b",
    r"\b(CUMMINS\s+[A-Z0-9\-]+)\b",
    r"\b(SY\d{3}[A-Z0-9\-]*)\b",
    r"\b(XE\d{3}[A-Z0-9\-]*)\b",
    r"\b(SD\d{2}[A-Z0-9\-]*)\b",
    r"\b(PC\d{3}[A-Z0-9\-]*)\b",
]

HEADER_PATTERNS = [
    r"^(?:CHAPTER|SECTION|SYSTEM|GROUP|DISASSEMBLY|ASSEMBLY|TROUBLESHOOTING)\s+.*$",
    r"^(?:SPN\s+\d+|FMI\s+\d+|DTC\s+[A-Z0-9\-]+|FAULT\s+CODE\b.*)$",
    r"^(?:SPECIFICATIONS|TORQUE\s+VALUES|PRESSURE\s+SETTINGS|MAINTENANCE\s+SCHEDULE)\b.*$",
    r"^#{1,4}\s+.*$",
]


KNOWN_OEM_BRANDS = [
    "SANY", "XCMG", "SHANTUI", "KOMATSU", "CATERPILLAR", "CAT", 
    "VOLVO", "HITACHI", "LIUGONG", "SDLG", "ZOOMLION", "DOOSAN", "HYUNDAI"
]

CHINESE_OEM_BRANDS = {
    "三一": "SANY",
    "徐工": "XCMG",
    "山推": "SHANTUI",
    "卡特": "CATERPILLAR",
    "小松": "KOMATSU",
    "柳工": "LIUGONG",
    "临工": "SDLG"
}

MODEL_PREFIX_MAP = {
    "SY": "SANY",
    "XE": "XCMG",
    "SD": "SHANTUI",
    "DH": "SHANTUI",
    "PC": "KOMATSU",
    "EC": "VOLVO",
    "ZX": "HITACHI",
    "CLG": "LIUGONG"
}

def detect_equipment_model(filename: str, first_pages_text: str = "") -> str:
    """
    Infer equipment model with robust hierarchy:
    1. Parse filename including Chinese OEM brands and non-ASCII boundaries
    2. Check model prefix map (SY -> SANY, XE -> XCMG, CLG -> LIUGONG, PC -> KOMATSU)
    3. Parse Page 1 cover/title banner (first 600 chars only)
    4. Fallback to sanitized filename
    """
    base_name = os.path.splitext(os.path.basename(filename))[0]
    clean_base = re.sub(r"[_\-]+", " ", base_name).strip()
    
    # 1. Check Chinese OEM Brands in filename
    for c_brand, en_brand in CHINESE_OEM_BRANDS.items():
        if c_brand in filename:
            m = re.search(r"(?<![A-Za-z0-9])([A-Za-z]{1,3}\d{2,4}[A-Za-z0-9]*(?:-\d+)?)(?![A-Za-z0-9])", filename)
            if m:
                return f"{en_brand} {m.group(1).upper()}"
            return en_brand

    # 2. Check English OEM Brand in filename
    brand_match = None
    for b in KNOWN_OEM_BRANDS:
        if re.search(rf"(?<![A-Za-z0-9]){b}(?![A-Za-z0-9])", clean_base, re.IGNORECASE):
            brand_match = "CATERPILLAR" if b.upper() == "CAT" else b.upper()
            break
            
    # 3. Check Alphanumeric Model Code in filename
    m = re.search(r"(?<![A-Za-z0-9])([A-Za-z]{1,3}\d{2,4}[A-Za-z0-9]*(?:-\d+)?|\b3\d{2}[A-Za-z0-9\-]*)(?![A-Za-z0-9])", clean_base, re.IGNORECASE)
    if m:
        code = m.group(1).upper()
        for prefix, oem in MODEL_PREFIX_MAP.items():
            if code.startswith(prefix):
                return f"{oem} {code}"
        if brand_match:
            return f"{brand_match} {code}"
        if code.startswith("3") and len(code) >= 3 and code[:3].isdigit():
            return f"CATERPILLAR {code}"
        return code

    if brand_match:
        return brand_match

    # 4. COVER PAGE HEADER PARSING (First 600 chars of Page 1 only)
    cover_snippet = first_pages_text[:600] if first_pages_text else ""
    for c_brand, en_brand in CHINESE_OEM_BRANDS.items():
        if c_brand in cover_snippet:
            m = re.search(r"(?<![A-Za-z0-9])([A-Za-z]{1,3}\d{2,4}[A-Za-z0-9]*(?:-\d+)?)(?![A-Za-z0-9])", cover_snippet)
            if m:
                return f"{en_brand} {m.group(1).upper()}"
            return en_brand

    title_match = re.search(
        r"(?:SERVICE\s+MANUAL|SHOP\s+MANUAL|MAINTENANCE\s+MANUAL|REPAIR\s+MANUAL)[\s:]+([A-Z0-9\s\-]{3,30})",
        cover_snippet,
        re.IGNORECASE
    )
    if title_match:
        cand = title_match.group(1).strip()
        for b in KNOWN_OEM_BRANDS:
            if b in cand.upper():
                m_code = re.search(r"(?<![A-Za-z0-9])([A-Za-z]{1,3}\d{2,4}[A-Za-z0-9]*(?:-\d+)?|\b3\d{2}[A-Za-z0-9\-]*)(?![A-Za-z0-9])", cand, re.IGNORECASE)
                if m_code:
                    return f"{b} {m_code.group(1).upper()}"
                return cand.title()

    for b in KNOWN_OEM_BRANDS:
        b_pat = rf"(?<![A-Za-z0-9]){b}\s+([A-Za-z]{1,3}\d{2,4}[A-Za-z0-9]*(?:-\d+)?|\b3\d{2}[A-Za-z0-9\-]*)(?![A-Za-z0-9])"
        m = re.search(b_pat, cover_snippet, re.IGNORECASE)
        if m:
            found_b = "CATERPILLAR" if b == "CAT" else b
            return f"{found_b} {m.group(1).upper()}"

    # 5. SANITIZED FILENAME FALLBACK
    return clean_base.title()


def format_table_as_markdown(table: List[List[Optional[str]]]) -> str:
    """Convert raw 2D table grid into a clean, aligned Markdown table"""
    if not table or len(table) < 2:
        return ""
    
    # Clean cells
    cleaned = []
    max_cols = max(len(row) for row in table)
    for row in table:
        cleaned_row = []
        for cell in row:
            val = str(cell).strip().replace("\n", " ") if cell is not None else ""
            val = re.sub(r"\s+", " ", val)
            cleaned_row.append(val)
        while len(cleaned_row) < max_cols:
            cleaned_row.append("")
        cleaned.append(cleaned_row)
    
    # Header and separator
    header = "| " + " | ".join(cleaned[0]) + " |"
    separator = "| " + " | ".join(["---"] * max_cols) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in cleaned[1:] if any(row)]
    
    return "\n".join([header, separator] + rows)


def extract_page_with_ocr(fitz_page) -> str:
    """Fallback OCR for scanned or image-based PDF pages using pytesseract"""
    if not HAS_TESSERACT:
        return ""
    
    try:
        pix = fitz_page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes))
        ocr_text = pytesseract.image_to_string(img)
        return ocr_text.strip()
    except Exception as e:
        logger.debug(f"OCR extraction failed or Tesseract not installed: {e}")
        return ""


def extract_page_content(
    pdfplumber_page, 
    fitz_page, 
    page_num: int
) -> Tuple[str, List[str]]:
    """
    Extract text and preserve table structures for a single page.
    Returns (full_page_text, list_of_markdown_tables).
    """
    tables_md: List[str] = []
    
    # 1. Extract tables using pdfplumber
    try:
        tables = pdfplumber_page.extract_tables()
        for tbl in tables:
            md_table = format_table_as_markdown(tbl)
            if md_table:
                tables_md.append(md_table)
    except Exception as e:
        logger.debug(f"Table extraction failed on page {page_num}: {e}")

    # 2. Extract plain text
    text = ""
    try:
        text = pdfplumber_page.extract_text(layout=True) or ""
    except Exception:
        pass
    
    if not text.strip():
        # Fallback to PyMuPDF text
        try:
            text = fitz_page.get_text("text") or ""
        except Exception:
            pass
    
    # 3. If text is virtually empty, page is likely a scan -> try OCR
    if len(text.strip()) < 40:
        ocr_res = extract_page_with_ocr(fitz_page)
        if ocr_res:
            text = f"[OCR Extracted Page {page_num}]\n" + ocr_res
    
    # 4. Integrate preserved tables into the flow if not already clearly represented
    if tables_md:
        table_block = "\n\n### Extracted Tables & Specifications:\n" + "\n\n".join(tables_md)
        text = text.strip() + "\n" + table_block

    return text.strip(), tables_md


def is_header_line(line: str) -> bool:
    """Check if a line represents a section, chapter, or diagnostic code boundary"""
    clean = line.strip()
    if not clean or len(clean) > 120:
        return False
    for pat in HEADER_PATTERNS:
        if re.match(pat, clean, re.IGNORECASE):
            return True
    return False


def chunk_document_semantically(
    pages_data: List[Dict[str, Any]],
    source_manual: str,
    equipment_model: str,
    min_tokens: int = 300,
    max_tokens: int = 800
) -> List[Dict[str, Any]]:
    """
    Split document content into semantic chunks targeting 300-800 tokens.
    Preserves procedure boundaries, fault codes, and tables.
    """
    chunks: List[Dict[str, Any]] = []
    current_section = "General Information"
    current_chunk_lines: List[str] = []
    current_pages: List[int] = []
    current_has_table = False
    
    chunk_index = 0

    def finalize_chunk():
        nonlocal chunk_index, current_chunk_lines, current_pages, current_has_table
        if not current_chunk_lines:
            return
        
        chunk_text = "\n".join(current_chunk_lines).strip()
        if len(chunk_text) < 50:
            current_chunk_lines = []
            current_pages = []
            current_has_table = False
            return
        
        # Estimate token count (rough heuristic: 1 token ~ 4 chars / 0.75 words)
        est_tokens = int(len(chunk_text.split()) * 1.3)
        start_page = current_pages[0] if current_pages else 1
        end_page = current_pages[-1] if current_pages else start_page
        
        header_context = (
            f"MANUAL: {source_manual} | EQUIPMENT: {equipment_model}\n"
            f"SECTION: {current_section} | PAGE(S): {start_page}-{end_page}\n"
            f"----------------------------------------\n"
        )
        
        full_text = header_context + chunk_text
        
        chunk_id = f"{os.path.splitext(source_manual)[0]}_p{start_page}_{chunk_index:04d}"
        
        chunks.append({
            "id": chunk_id,
            "text": full_text,
            "metadata": {
                "source": source_manual,
                "equipment_model": equipment_model,
                "section_title": current_section,
                "page_number": start_page,
                "end_page": end_page,
                "has_table": current_has_table,
                "token_count": est_tokens,
                "chunk_index": chunk_index
            }
        })
        chunk_index += 1
        current_chunk_lines = []
        current_pages = []
        current_has_table = False

    for page in pages_data:
        p_num = page["page_num"]
        p_text = page["text"]
        p_has_table = bool(page.get("tables"))
        
        if not p_text:
            continue
        
        lines = p_text.split("\n")
        for line in lines:
            line_str = line.strip()
            
            # Detect section/procedure header
            if is_header_line(line_str):
                est_curr_tokens = int(len(" ".join(current_chunk_lines).split()) * 1.3)
                # If we already have accumulated content, finalize previous chunk
                if est_curr_tokens >= min_tokens:
                    finalize_chunk()
                current_section = re.sub(r"^[#\s\-*]+", "", line_str).strip()
            
            current_chunk_lines.append(line)
            if p_num not in current_pages:
                current_pages.append(p_num)
            if p_has_table:
                current_has_table = True
            
            # Check token threshold
            est_tokens = int(len(" ".join(current_chunk_lines).split()) * 1.3)
            if est_tokens >= max_tokens:
                finalize_chunk()

    # Finalize any remainder
    finalize_chunk()
    return chunks


def parse_pdf_manual(
    pdf_path: str,
    equipment_model_override: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse a complete OEM PDF manual into semantically chunked records with rich metadata.
    Returns (chunks, summary_stats).
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    filename = os.path.basename(pdf_path)
    logger.info(f"Starting parsing of PDF manual: {filename}")
    
    pages_data = []
    front_matter_text = ""
    
    # Open with both fitz (PyMuPDF) and pdfplumber
    fitz_doc = fitz.open(pdf_path)
    total_pages = len(fitz_doc)
    
    with pdfplumber.open(pdf_path) as plumber_pdf:
        for idx in range(total_pages):
            page_num = idx + 1
            plumber_page = plumber_pdf.pages[idx]
            fitz_page = fitz_doc[idx]
            
            text, tables = extract_page_content(plumber_page, fitz_page, page_num)
            
            if page_num <= 3:
                front_matter_text += " " + text
                
            pages_data.append({
                "page_num": page_num,
                "text": text,
                "tables": tables
            })
            
    fitz_doc.close()
    
    # Detect equipment model
    model = equipment_model_override or detect_equipment_model(filename, front_matter_text)
    
    # Chunk semantically
    chunks = chunk_document_semantically(
        pages_data=pages_data,
        source_manual=filename,
        equipment_model=model
    )
    
    stats = {
        "filename": filename,
        "total_pages": total_pages,
        "equipment_model": model,
        "chunks_extracted": len(chunks),
        "total_tables_extracted": sum(len(p["tables"]) for p in pages_data)
    }
    
    logger.info(
        f"Parsed {filename}: {total_pages} pages -> {len(chunks)} chunks "
        f"(Model: {model}, Tables: {stats['total_tables_extracted']})"
    )
    return chunks, stats
