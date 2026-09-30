import argparse
import logging
import sys
from pathlib import Path

from db import document_exists, init_db, save_invoice
from pipeline import ExtractionFailedError, extract_data

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(description="Idempotent invoice ingestion pipeline")
    parser.add_argument("file", nargs="?", default="sample_invoice.txt",
                        help="path to a raw text invoice (default: sample_invoice.txt)")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}")
        return 1
    raw_text = path.read_text(encoding="utf-8")

    init_db()
    if document_exists(raw_text):
        print("Duplicate found, skipping (no LLM call made).")
        return 0
    try:
        invoice = extract_data(raw_text)
    except ExtractionFailedError as exc:
        print(f"Extraction failed; nothing saved.\n{exc}")
        return 1

    if save_invoice(raw_text, invoice):
        print(
            f"Saved invoice from '{invoice.vendor_name}' "
            f"(total {invoice.total} {invoice.currency}, "
            f"{len(invoice.line_items)} line items)."
        )
    else:
        print("Duplicate found, skipping.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
