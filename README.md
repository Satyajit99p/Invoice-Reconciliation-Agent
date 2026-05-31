# Invoice-Reconciliation-Agent

An autonomous invoice reconciliation agent for multi file type billing audits. It supports vendor invoice ingestion, database reconciliation, discrepancy analysis, and optional business-rule retrieval via a vector store.

## Features

- Ingest vendor invoices (CSV or Excel) and compute totals
- Compare vendor totals with system totals
- Identify missing, duplicate, mismatched, and failed invoice lines
- Retrieve relevant business rules using embeddings
- Expose reconciliation tools via an MCP server
- Orchestrate reconciliation with a LangGraph workflow

## Project Structure

- [agent/chat_agent.py](agent/chat_agent.py) - Tool registry and Ollama tool-calling loop
- [agent/mcp_server.py](agent/mcp_server.py) - MCP server exposing reconciliation tools
- [agent/langgraph_orchestrator.py](agent/langgraph_orchestrator.py) - LangGraph workflow orchestration
- [service/utilities.py](service/utilities.py) - Vendor invoice ingestion utilities
- [service/chromadb_service.py](service/chromadb_service.py) - Embedding and retrieval helper
- [data/pgsql_queries.py](data/pgsql_queries.py) - SQL queries for reconciliation

## Requirements

- Python 3.10+ recommended
- Ollama running locally if you use the chat agent or LLM analysis
- PostgreSQL / Supabase connection for reconciliation queries
- Chroma Cloud credentials if using embeddings

Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

Database:

- `SUPABASE_DB_HOST`
- `SUPABASE_DB_NAME`
- `SUPABASE_DB_USER`
- `SUPABASE_DB_PASSWORD`
- `SUPABASE_DB_PORT`

Supabase API (for vendor invoice line insert):

- `SUPABASE_URL`
- `SUPABASE_KEY`

Chroma Cloud (optional for embeddings):

- `CHROMA_API_KEY`
- `CHROMA_TENANT`
- `CHROMA_DATABASE`

## Usage

### MCP Server

Run the MCP tools server:

```bash
python -m agent.mcp_server
```

Available tools include totals comparison, tracking discrepancies, and business-rule suggestions.

### Chat Agent (Ollama tool-calling)

The chat agent registers all MCP tools and lets Ollama call them dynamically:

```bash
python -m agent.chat_agent
```

### LangGraph Orchestrator

Run the reconciliation workflow end-to-end:

```bash
python -m agent.langgraph_orchestrator
```

This uses the invoice ID and vendor file path specified in [agent/langgraph_orchestrator.py](agent/langgraph_orchestrator.py).

## Notes

- Vendor files should include a `ChargeAmount` column and tracking metadata expected by the database schema.
- The embeddings workflow reads rules from a text file and stores chunks in Chroma.
