from itertools import chain
import os
import psycopg2

from mcp.server.fastmcp import FastMCP

from service.utilities import Utility
from data.pgsql_queries import (
    TOTAL_AMOUNT,
    MISSING_PARCELS,
    DUPLICATE_PARCELS,
    MISMATCHED_PARCELS,
    FAILED_PARCELS
)
from service.chromadb_service import ChromaDB

mcp = FastMCP("invoice-reconciliation")

@mcp.tool()
def get_excel_total(file_path: str) -> dict:
    """
    Calculate the total invoice amount from a vendor Excel file.
    """

    total_amount = Utility.ingest_vendor_excel(file_path)

    return {
        "file_path": file_path,
        "excel_total": float(total_amount)
    }

@mcp.tool()
def get_system_total(invoice_id: str) -> dict:
    """
    Retrieve invoice total from the database.
    """

    with psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        database=os.getenv("SUPABASE_DB_NAME"),
        user=os.getenv("SUPABASE_DB_USER"),
        password=os.getenv("SUPABASE_DB_PASSWORD"),
        port=os.getenv("SUPABASE_DB_PORT"),
    ) as conn:
        with conn.cursor() as cursor:

            cursor.execute(
                TOTAL_AMOUNT,
                (invoice_id,)
            )

            total = cursor.fetchone()[0] or 0.0

    return {
        "invoice_id": invoice_id,
        "system_total": float(total)
    }

@mcp.tool()
def compare_totals(
    excel_total: float,
    system_total: float
) -> dict:
    """
    Compare Excel and system totals.
    """

    difference = excel_total - system_total

    return {
        "excel_total": excel_total,
        "system_total": system_total,
        "difference": difference,
        "status": (
            "MATCH"
            if abs(difference) < 1e-6
            else "MISMATCH"
        )
    }

@mcp.tool()
def get_missing_tracking(invoice_id: str) -> list:
    """
    Retrieve invoices with missing tracking numbers.
    """

    with psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        database=os.getenv("SUPABASE_DB_NAME"),
        user=os.getenv("SUPABASE_DB_USER"),
        password=os.getenv("SUPABASE_DB_PASSWORD"),
        port=os.getenv("SUPABASE_DB_PORT"),
    ) as conn:
        with conn.cursor() as cur:

            cur.execute(
                MISSING_PARCELS,
                (invoice_id,)
            )

            return [
                {
                    "invoiceNumber": row[0],
                    "missing_count": row[1]
                }
                for row in cur.fetchall()
            ]
        
@mcp.tool()
def get_duplicate_tracking(invoice_id: str) -> list:
    """
    Retrieve duplicate tracking records.
    """

    with psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        database=os.getenv("SUPABASE_DB_NAME"),
        user=os.getenv("SUPABASE_DB_USER"),
        password=os.getenv("SUPABASE_DB_PASSWORD"),
        port=os.getenv("SUPABASE_DB_PORT"),
    ) as conn:
        with conn.cursor() as cur:

            cur.execute(
                DUPLICATE_PARCELS,
                (invoice_id,)
            )

            return [
                {
                    "invoiceId": r[0],
                    "status": r[1],
                    "statusMsg": r[2],
                    "chargeType": r[3],
                    "duplicate_count": r[4]
                }
                for r in cur.fetchall()
            ]
        
@mcp.tool()
def get_mismatched_invoicelines(invoice_id: str) -> list:
    """
    Retrieve mismatched invoice lines.
    """

    with psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        database=os.getenv("SUPABASE_DB_NAME"),
        user=os.getenv("SUPABASE_DB_USER"),
        password=os.getenv("SUPABASE_DB_PASSWORD"),
        port=os.getenv("SUPABASE_DB_PORT"),
    ) as conn:
        with conn.cursor() as cur:

            cur.execute(
                MISMATCHED_PARCELS,
                (invoice_id,)
            )

            return [
                {
                    "invoiceId": r[0],
                    "status": r[1],
                    "statusMsg": r[2],
                    "count_lines": r[3]
                }
                for r in cur.fetchall()
            ]
        
@mcp.tool()
def get_failed_invoicelines(invoice_id: str) -> list:
    """
    Retrieve failed invoice line records.
    """

    with psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        database=os.getenv("SUPABASE_DB_NAME"),
        user=os.getenv("SUPABASE_DB_USER"),
        password=os.getenv("SUPABASE_DB_PASSWORD"),
        port=os.getenv("SUPABASE_DB_PORT"),
    ) as conn:
        with conn.cursor() as cur:

            cur.execute(
                FAILED_PARCELS,
                (invoice_id,)
            )

            return [
                {
                    "invoiceId": r[0],
                    "statusMsg": r[1],
                    "failedCount": r[2]
                }
                for r in cur.fetchall()
            ]
        
@mcp.tool()
def get_discrepancies(invoice_id: str) -> dict:
    """
    Retrieve all invoice discrepancies.
    """

    with psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        database=os.getenv("SUPABASE_DB_NAME"),
        user=os.getenv("SUPABASE_DB_USER"),
        password=os.getenv("SUPABASE_DB_PASSWORD"),
        port=os.getenv("SUPABASE_DB_PORT"),
    ) as conn:
        with conn.cursor() as cur:

            cur.execute(MISSING_PARCELS, (invoice_id,))
            missing = [
                {
                    "invoiceNumber": r[0],
                    "missing_count": r[1]
                }
                for r in cur.fetchall()
            ]

            cur.execute(DUPLICATE_PARCELS, (invoice_id,))
            duplicate = [
                {
                    "invoiceId": r[0],
                    "status": r[1],
                    "statusMsg": r[2],
                    "chargeType": r[3],
                    "duplicate_count": r[4]
                }
                for r in cur.fetchall()
            ]

            cur.execute(MISMATCHED_PARCELS, (invoice_id,))
            mismatched = [
                {
                    "invoiceId": r[0],
                    "status": r[1],
                    "statusMsg": r[2],
                    "count_lines": r[3]
                }
                for r in cur.fetchall()
            ]

            cur.execute(FAILED_PARCELS, (invoice_id,))
            failed = [
                {
                    "invoiceId": r[0],
                    "statusMsg": r[1],
                    "failedCount": r[2]
                }
                for r in cur.fetchall()
            ]

    return {
        "invoice_id": invoice_id,
        "missing_tracking": missing,
        "duplicate_tracking": duplicate,
        "mismatched_invoicelines": mismatched,
        "failed_invoicelines": failed
    }

@mcp.tool()
def suggest_business_rules(
    status_messages: list[str]
) -> dict:
    """
    Retrieve business rules relevant to invoice failures.
    """

    query = (
        "suggest invoicing error rules based on "
        "the following discrepancies"
    )

    results = ChromaDB.retrieve(
        collection_name="invoice_reconciliation_rules",
        query=[query] + status_messages,
        n_results=5
    )

    docs = list(
        chain.from_iterable(
            results["documents"]
        )
    )

    return {
        "business_rules": docs
    }

if __name__ == "__main__":
    mcp.run()