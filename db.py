import hashlib
import sqlite3
from contextlib import closing
from schemas import ExtractedInvoice

DB_PATH = "invoices.db"

def hash_document(raw_text: str) -> str:
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

def init_db() -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS invoices (
                    document_hash  TEXT PRIMARY KEY,   -- SHA-256 of raw text => uniqueness
                    vendor_name    TEXT NOT NULL,
                    invoice_number TEXT,
                    issue_date     TEXT NOT NULL,      -- ISO format: YYYY-MM-DD
                    due_date       TEXT NOT NULL,
                    currency       TEXT NOT NULL,
                    subtotal       REAL NOT NULL,
                    tax            REAL NOT NULL,
                    total_amount   REAL NOT NULL,
                    created_at     TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS line_items (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_hash TEXT NOT NULL REFERENCES invoices(document_hash),
                    description   TEXT NOT NULL,
                    quantity      REAL NOT NULL,
                    unit_price    REAL NOT NULL,
                    line_total    REAL NOT NULL
                )
                """
            )

def document_exists(raw_text: str) -> bool:
    doc_hash = hash_document(raw_text)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        row = conn.execute(
            "SELECT 1 FROM invoices WHERE document_hash = ?", (doc_hash,)
        ).fetchone()
    return row is not None

def save_invoice(raw_text: str, invoice: ExtractedInvoice) -> bool:
    doc_hash = hash_document(raw_text)

    if document_exists(raw_text):
        return False

    try:
        with closing(sqlite3.connect(DB_PATH)) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO invoices
                        (document_hash, vendor_name, invoice_number, issue_date,
                         due_date, currency, subtotal, tax, total_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_hash,
                        invoice.vendor_name,
                        invoice.invoice_number,
                        invoice.issue_date.isoformat(),
                        invoice.due_date.isoformat(),
                        invoice.currency,
                        float(invoice.subtotal),
                        float(invoice.tax),
                        float(invoice.total),
                    ),
                )

                conn.executemany(
                    """
                    INSERT INTO line_items
                        (document_hash, description, quantity, unit_price, line_total)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            doc_hash,
                            item.description,
                            float(item.quantity),
                            float(item.unit_price),
                            float(item.line_total),
                        )
                        for item in invoice.line_items
                    ],
                )
        return True

    except sqlite3.IntegrityError:
        return False
