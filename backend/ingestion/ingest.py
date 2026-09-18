#!/usr/bin/env python3
"""
MechMind AI - Automated Document Ingestion CLI
Processes OEM manuals (PDFs) into semantic chunks, extracts tables,
generates embeddings, and upserts into ChromaDB with manifest tracking.

Usage:
  python ingest.py --folder ./manuals/xcmg
  python ingest.py --file ./manuals/sany_sy215c.pdf --model "SANY SY215C"
  python ingest.py --status
  python ingest.py --test-query "boom cylinder drifting under load"
"""

import os
import sys
import glob
import argparse
import logging
import time
from typing import List

# Add parent directory to path so imports work cleanly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from ingestion.pdf_parser import parse_pdf_manual
from ingestion.chroma_storage import ChromaStorage, ManifestManager, calculate_file_hash, DEFAULT_COLLECTION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("mechmind.ingest")


def print_banner():
    print("=" * 70)
    print("      MECHMIND AI - OEM MANUAL INGESTION PIPELINE (PHASE 1)")
    print("=" * 70)


def process_single_pdf(
    pdf_path: str,
    storage: ChromaStorage,
    manifest: ManifestManager,
    model_override: str = None,
    force: bool = False,
    dry_run: bool = False
) -> dict:
    filename = os.path.basename(pdf_path)
    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    print(f"\n[FILE] Processing: {filename} ({file_size_mb:.2f} MB)")

    # Check manifest for deduplication
    already_ingested, current_hash = manifest.is_already_ingested(pdf_path)
    if already_ingested and not force and not dry_run:
        prev_info = manifest.data["files"][filename]
        print(f"  --> [SKIP] Already ingested on {prev_info.get('ingested_at')}")
        print(f"      Recorded chunks: {prev_info.get('chunks')} | SHA-256: {current_hash[:12]}...")
        print(f"      (Use --force to re-process)")
        return {"status": "skipped", "chunks": prev_info.get("chunks", 0)}

    # Parse and chunk PDF
    t0 = time.time()
    try:
        chunks, stats = parse_pdf_manual(pdf_path, equipment_model_override=model_override)
    except Exception as e:
        print(f"  --> [ERROR] Failed to parse PDF: {e}")
        logger.exception(e)
        return {"status": "error", "error": str(e)}

    parse_duration = time.time() - t0
    print(f"  --> Extracted {len(chunks)} semantic chunks across {stats['total_pages']} pages in {parse_duration:.2f}s")
    print(f"      Equipment Model: {stats['equipment_model']}")
    print(f"      Tables Preserved: {stats['total_tables_extracted']}")

    if dry_run:
        print("  --> [DRY RUN] Skipping ChromaDB upsert. Sample chunk preview:")
        if chunks:
            sample = chunks[0]
            print("-" * 50)
            print(f"Sample Chunk ID: {sample['id']}")
            print(f"Metadata: {sample['metadata']}")
            print(f"Text Snippet:\n{sample['text'][:350]}...")
            print("-" * 50)
        return {"status": "dry_run", "chunks": len(chunks)}

    # Upsert to ChromaDB
    t1 = time.time()
    try:
        upserted = storage.upsert_chunks(chunks)
    except Exception as e:
        print(f"  --> [ERROR] Failed ChromaDB upsert: {e}")
        logger.exception(e)
        return {"status": "error", "error": str(e)}

    upsert_duration = time.time() - t1
    print(f"  --> Successfully upserted {upserted} chunks into ChromaDB in {upsert_duration:.2f}s")

    # Record in manifest
    manifest.record_ingestion(
        filepath=pdf_path,
        file_hash=current_hash or calculate_file_hash(pdf_path),
        pages=stats["total_pages"],
        chunks=len(chunks),
        model=stats["equipment_model"]
    )
    print(f"  --> Recorded in manifest.json")
    return {"status": "success", "chunks": len(chunks)}


def show_status(storage: ChromaStorage, manifest: ManifestManager):
    print_banner()
    print("\n--- INGESTION MANIFEST STATUS ---")
    files = manifest.data.get("files", {})
    if not files:
        print("No files have been recorded in manifest.json yet.")
    else:
        print(f"Total Files Ingested: {len(files)}")
        print(f"Total Chunks Tracked in Manifest: {manifest.data.get('total_chunks_indexed', 0)}")
        print(f"Last Manifest Update: {manifest.data.get('last_updated', 'Never')}\n")
        print(f"{'Filename':<35} | {'Model':<15} | {'Pages':<6} | {'Chunks':<7} | {'Ingested Date'}")
        print("-" * 90)
        for fname, info in files.items():
            dt = info.get("ingested_at", "")[:19].replace("T", " ")
            print(f"{fname[:34]:<35} | {info.get('equipment_model', 'N/A')[:14]:<15} | {info.get('pages', 0):<6} | {info.get('chunks', 0):<7} | {dt}")

    print("\n--- CHROMADB STATUS ---")
    try:
        count = storage.count()
        print(f"Connected to ChromaDB collection: '{storage.collection_name}'")
        print(f"Current vectors in collection: {count}")
    except Exception as e:
        print(f"ChromaDB connection check failed: {e}")


def run_test_query(storage: ChromaStorage, query_text: str, top_k: int = 3):
    print_banner()
    print(f"\n[QUERY TEST] Query: '{query_text}' (Top-{top_k} results)")
    t0 = time.time()
    results = storage.query(query_text, top_k=top_k)
    duration = (time.time() - t0) * 1000
    
    if not results:
        print("No matches found in ChromaDB collection.")
        return

    print(f"Retrieved {len(results)} chunks in {duration:.1f}ms:\n")
    for i, r in enumerate(results, 1):
        meta = r["metadata"]
        print(f"=== RESULT {i} (Distance: {r.get('distance', 0.0):.4f}) ===")
        print(f"Source: {meta.get('source')} | Model: {meta.get('equipment_model')} | Page: {meta.get('page_number')}")
        print(f"Section: {meta.get('section_title')}")
        print("-" * 60)
        print(r["text"][:500] + ("..." if len(r["text"]) > 500 else ""))
        print("\n")


def main():
    parser = argparse.ArgumentParser(
        description="MechMind AI - Automated OEM Service Manual Ingestion CLI"
    )
    parser.add_argument("--folder", type=str, help="Path to folder containing PDF manuals")
    parser.add_argument("--file", type=str, help="Path to a single PDF manual")
    parser.add_argument("--model", type=str, help="Override equipment model name (e.g. 'XCMG XE215C')")
    parser.add_argument("--collection", type=str, default=DEFAULT_COLLECTION, help="ChromaDB collection name")
    parser.add_argument("--force", action="store_true", help="Force re-ingestion even if in manifest.json")
    parser.add_argument("--dry-run", action="store_true", help="Parse and chunk only, do not write to ChromaDB")
    parser.add_argument("--status", action="store_true", help="Display manifest and ChromaDB status")
    parser.add_argument("--test-query", type=str, help="Execute a test search query against ChromaDB")

    args = parser.parse_args()

    # Initialize Chroma storage and Manifest
    try:
        storage = ChromaStorage(collection_name=args.collection)
    except Exception as e:
        print(f"[FATAL] Could not initialize Chroma storage: {e}")
        sys.exit(1)

    manifest = ManifestManager()

    if args.status:
        show_status(storage, manifest)
        return

    if args.test_query:
        run_test_query(storage, args.test_query)
        return

    # Determine files to process
    pdf_files: List[str] = []
    if args.file:
        if not os.path.exists(args.file):
            print(f"[ERROR] Specified file not found: {args.file}")
            sys.exit(1)
        pdf_files = [os.path.abspath(args.file)]
    elif args.folder:
        if not os.path.exists(args.folder):
            print(f"[ERROR] Specified folder not found: {args.folder}")
            sys.exit(1)
        pdf_files = sorted(glob.glob(os.path.join(args.folder, "**", "*.pdf"), recursive=True))
        if not pdf_files:
            print(f"[WARNING] No PDF files found in {args.folder}")
            return
    else:
        # Default: check backend/manuals
        default_manuals = os.path.abspath(os.path.join(current_dir, "..", "manuals"))
        if os.path.exists(default_manuals):
            pdf_files = sorted(glob.glob(os.path.join(default_manuals, "*.pdf")))
            if not pdf_files:
                parser.print_help()
                return
        else:
            parser.print_help()
            return

    print_banner()
    print(f"Found {len(pdf_files)} PDF manual(s) to process.")
    print(f"Target Collection: {args.collection}")
    print(f"Force Re-ingest: {args.force} | Dry Run: {args.dry_run}")

    total_chunks = 0
    success_count = 0

    for pdf_path in pdf_files:
        res = process_single_pdf(
            pdf_path=pdf_path,
            storage=storage,
            manifest=manifest,
            model_override=args.model,
            force=args.force,
            dry_run=args.dry_run
        )
        if res.get("status") in ["success", "dry_run", "skipped"]:
            success_count += 1
            total_chunks += res.get("chunks", 0)

    print("\n" + "=" * 70)
    print(f"INGESTION COMPLETE: Processed {success_count}/{len(pdf_files)} files.")
    print(f"Total Chunks in Index: {storage.count()}")
    print("=" * 70)


if __name__ == "__main__":
    main()
