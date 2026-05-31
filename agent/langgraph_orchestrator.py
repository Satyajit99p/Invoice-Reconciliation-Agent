import os
from typing import TypedDict, List, Dict, Any
from itertools import chain
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
import pandas as pd
import psycopg2

from data.chromadb_da import ChromaDB
from data.pgsql_queries import DUPLICATE_PARCELS, FAILED_PARCELS, MISMATCHED_PARCELS, TOTAL_AMOUNT,MISSING_PARCELS
from service.utilities import Utility
from service.chromadb_service import RagHelper

class InvoiceState(TypedDict):
    invoice_id: str
    file_path: str
    
    # computed
    excel_total: float
    system_total: float
    status: str  # MATCH / MISMATCH
    
    # discrepancies
    missing_tracking: List[Dict[str, Any]]
    duplicate_tracking: List[Dict[str, Any]]
    mismatched_invoicelines: List[Dict[str, Any]]
    failed_invoicelines: List[Dict[str, Any]]
    
    # rules + llm output
    business_rules: List[str]
    analysis: Any
    
    final_report: Dict[str, Any]


def ingest_excel(state: InvoiceState):

    total_amount = Utility.ingest_vendor_excel(state["file_path"])

    return {
        **state,
        "excel_total": float(total_amount)
    }

def compute_totals(state: InvoiceState):
    with psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        database=os.getenv("SUPABASE_DB_NAME"),
        user=os.getenv("SUPABASE_DB_USER"),
        password=os.getenv("SUPABASE_DB_PASSWORD"),
        port=os.getenv("SUPABASE_DB_PORT"),
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(TOTAL_AMOUNT, (state["invoice_id"],))

            system_total = cursor.fetchone()[0] or 0.0

    return {
        **state,
        "system_total": float(system_total)
    }

def check_mismatch(state: InvoiceState):
    if abs(state["excel_total"] - state["system_total"]) < 1e-6:
        return {**state, "status": "MATCH"}
    return {**state, "status": "MISMATCH"}

def fetch_discrepancies(state: InvoiceState):
    with psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        database=os.getenv("SUPABASE_DB_NAME"),
        user=os.getenv("SUPABASE_DB_USER"),
        password=os.getenv("SUPABASE_DB_PASSWORD"),
        port=os.getenv("SUPABASE_DB_PORT"),
    ) as conn:
        with conn.cursor() as cur:
            # Missing tracking
            cur.execute(MISSING_PARCELS, (state["invoice_id"],))

            missing = [{"invoiceNumber": r[0], "missing_count": r[1]} for r in cur.fetchall()]

            # duplicate tracking
            cur.execute(DUPLICATE_PARCELS, (state["invoice_id"],))

            duplicate = [
                {
                    "invoiceId": r[0],
                    "status": r[1],
                    "statusMsg": r[2],
                    "chargeType": r[3],
                    "duplicate_count": r[4],
                }
                for r in cur.fetchall()
            ]

            # mismatched invoicelines
            cur.execute(MISMATCHED_PARCELS, (state["invoice_id"],))

            mismatched = [
                {
                    "invoiceId": r[0],
                    "status": r[1],
                    "statusMsg": r[2],
                    "count_lines": r[3],
                }
                for r in cur.fetchall()
            ]

            # failed invoicelines
            cur.execute(FAILED_PARCELS, (state["invoice_id"],))

            failed = [{"invoiceId": r[0], "statusMsg": r[1], "failedCount": r[2]} for r in cur.fetchall()]
    
    return {
        **state,
        "missing_tracking": missing,
        "duplicate_tracking": duplicate,
        "mismatched_invoicelines": mismatched,
        "failed_invoicelines": failed
    }

def retrieve_rules(state: InvoiceState):

    query = "suggest invoicing error rules based on the following discrepancies: "
    
    status_messages = [d["statusMsg"] for d in state["failed_invoicelines"]]

    results = ChromaDB.retrieve(
    collection_name="invoice_reconciliation_rules",
    query=[query] + status_messages,
    n_results=5)
    
    retrieved_documents = list(chain.from_iterable(results["documents"]))

    rules = "\n".join(retrieved_documents)

    return {
        **state,
        "business_rules": rules
    }

def llm_analysis(state: InvoiceState):

    llm_localhost = ChatOllama(model="llama3.2", 
            base_url="http://localhost:11434",
            validate_model_on_init=True)

    prompt = f"""
    You are an invoice reconciliation engine.

    Missing tracking numbers: {state['missing_tracking']}
    Duplicate tracking numbers: {state['duplicate_tracking']}
    Mismatched invoicelines: {state['mismatched_invoicelines']}
    Failed invoicelines: {state['failed_invoicelines']}

    Rules:
    {state['business_rules']}

    Provide structured JSON with:
    - issue classification
    - root cause
    - recommended fixes
    """
    
    response = llm_localhost.invoke(prompt)
    
    return {
        **state,
        "analysis": response.content
    }

def generate_report(state: InvoiceState):
    return {
        **state,
        "final_report": {
            "invoice_id": state["invoice_id"],
            "status": state["status"],
            "summary": {
                "excel_total": state["excel_total"],
                "system_total": state["system_total"],
                "difference": state["excel_total"] - state["system_total"]
            },
            "issues": {
                "missing_tracking": len(state["missing_tracking"]),
                "duplicate_tracking": len(state["duplicate_tracking"]),
                "mismatched_invoicelines": len(state["mismatched_invoicelines"]),
                "failed_invoicelines": len(state["failed_invoicelines"])
            },
            "analysis": state["analysis"]
        }
    }

def build_graph():

    builder = StateGraph(InvoiceState)

    # Nodes
    builder.add_node("ingest_excel", ingest_excel)
    builder.add_node("compute_totals", compute_totals)
    builder.add_node("check_mismatch", check_mismatch)
    builder.add_node("fetch_discrepancies", fetch_discrepancies)
    builder.add_node("retrieve_rules", retrieve_rules)
    builder.add_node("llm_analysis", llm_analysis)
    builder.add_node("generate_report", generate_report)

    # Flow
    builder.set_entry_point("ingest_excel")

    builder.add_edge("ingest_excel", "compute_totals")
    builder.add_edge("compute_totals", "check_mismatch")

    # Conditional branch
    def route(state):
        return state["status"]

    builder.add_conditional_edges(
        "check_mismatch",
        route,
        {
            "MATCH": "generate_report",
            "MISMATCH": "fetch_discrepancies"
        }
    )

    builder.add_edge("fetch_discrepancies", "retrieve_rules")
    builder.add_edge("retrieve_rules", "llm_analysis")
    builder.add_edge("llm_analysis", "generate_report")

    builder.add_edge("generate_report", END)

    graph = builder.compile()

    return graph

if __name__ == "__main__":

    RagHelper.save_vector_embeddings(
        file_path="rules.txt",collection_name="invoice_reconciliation_rules")

    graph = build_graph()

    result = graph.invoke({
        "invoice_id": "INV-001",
        "file_path": "./test/assets/vendor_invoice_line.xlsx"
    })

    print(result["final_report"])