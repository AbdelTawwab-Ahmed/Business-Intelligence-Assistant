# 📊 NileMart BI Assistant

An Arabic-first, multi-agent Business Intelligence assistant. Ask questions about retail data in **English, Modern Standard Arabic, Egyptian Arabic, or Franco-Arabic** and get verified answers backed by live SQL, with optional on-demand dashboards.

> **Status:** Phase 1 complete, Phase 2 in progress. See [Roadmap](#roadmap).

---

## Features

- **Natural-language to SQL:** an analyst agent writes and self-corrects PostgreSQL queries, then answers in the user's own language and dialect.
- **Dynamic schema discovery:** the schema, keys, valid category values, date ranges, and NULL statistics are read from the database at runtime. Only the business rules are static.
- **Verifiable answers:** every response exposes the exact SQL used and the raw rows returned by the database (with CSV download).
- **On-demand dashboards:** a visualization agent builds 2-4 Plotly charts only when the user clicks **📊 Show dashboard**, so simple questions stay fast and cheap.
- **Supervisor routing:** greetings are answered directly, data questions go to the SQL analyst, and out-of-scope or data-modifying requests are politely declined.
- **Conversation memory:** follow-up questions work within a thread (LangGraph checkpointer).
- **Model resilience:** Gemini 2.5 Flash as the primary model, with Groq `gpt-oss-120b` as an automatic fallback for the worker agents.

## Architecture

```mermaid
flowchart TD
    UI[Streamlit UI] -->|question| SUP[Supervisor]
    SUP -->|greeting / out of scope| UI
    SUP -->|data question| SQL[SQL Analyst agent]
    SQL <-->|MCP stdio| MCP[Database MCP server]
    MCP --> DB[(PostgreSQL on Railway)]
    SQL -->|answer + SQL + rows| UI
    UI -->|"📊 button"| VIZ[Visualizer agent]
    VIZ -->|get_schema_info| MCP
    VIZ -->|create_chart| CH[Chart tool, Plotly]
    CH -->|read-only query| DB
    VIZ -->|figures| UI
```

**Design decisions**

- **Supervisor with specialist workers**, built with LangChain `create_agent` and `langgraph-supervisor`. The data flow is mostly fixed, so routing is deterministic and cheap, not an LLM-invented plan.
- **Charts are built from queries, not copied numbers.** The Viz agent sends a SQL query and column names to a tool, which executes it and builds the figure. This prevents number-copying errors and saves tokens.
- **The dashboard is UI-triggered**, not a supervisor route, so the user decides whether to pay for it.

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph, LangChain (`create_agent`), `langgraph-supervisor` |
| Tools protocol | Model Context Protocol (MCP) via `langchain-mcp-adapters` |
| LLMs | Gemini 2.5 Flash (primary), Groq `openai/gpt-oss-120b` (fallback) |
| Database | PostgreSQL (Railway) |
| Visualization | Plotly |
| UI | Streamlit |

## Dataset

A synthetic retail database for **NileMart**, an Egyptian retail chain: 11 tables (orders, order_items, products, categories, customers, branches, payments, inventory, inventory_movements, returns, return_items), about 20,000 orders from Jan 2024 to Sep 2026, 8 branches, in-store and online channels.

Business rules encoded for the agents:
- Revenue = `quantity × unit_price − discount_amount` (discount is per line), excluding cancelled orders.
- Profit = gross profit using `order_items.unit_cost` (cost at time of sale).
- Refunds come from `return_items.refund_amount`.
- Online orders have no `branch_id`, so branch analysis uses `COALESCE(branch_id, fulfillment_branch_id)`.
- Relative dates ("last month") are anchored to the latest order date in the data.

## Safety

The database MCP server enforces three layers: only `SELECT`/`WITH` statements (keyword and multi-statement filter), a **read-only database session**, and a 10-second statement timeout, plus a 200-row cap per query. Agents receive errors as text so they can correct their own SQL.

## Project Structure

```
bi-assistant/
├── app.py                    # Streamlit UI (chat, raw data, dashboard button)
├── agents/
│   ├── graph.py              # Supervisor graph assembly
│   ├── sql_analyst.py        # SQL analyst worker + shared models
│   ├── visualizer_agent.py          # Dashboard worker
│   └── visualizer_tools.py          # create_chart tool (Plotly)
├── mcp_servers/
│   └── database_server.py    # MCP server: get_schema_info, run_sql_query
├── tests/            # Smoke test for the DB tools
├── requirements.txt
├── .env.example
└── README.md
```

## Getting Started

**Prerequisites:** Python 3.10+, a PostgreSQL database with the NileMart schema, a Google AI Studio API key, and a Groq API key.

```bash
git clone <your-repo-url>
cd bi-assistant
python -m venv venv
venv\Scripts\activate          # Windows  (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
```

Create a `.env` file:

```env
GOOGLE_API_KEY=your_google_key
GROQ_API_KEY=your_groq_key
DATABASE_URL=postgresql://user:password@host:port/dbname
```

Run:

```bash
streamlit run app.py
```

## Example Questions

- `What are the top 5 products by profit?`
- `إيه أكتر فرع بيرتجع منتجات؟`
- `3ayez a3raf ad eh el revenue bta3 el online vs in_store?`
- `Show monthly revenue for 2025` (then click **📊 Show dashboard**)

## Roadmap

**Done (Phase 1 and part of Phase 2)**
- [x] Database MCP server with live schema introspection and read-only safeguards
- [x] SQL analyst agent with multilingual and Arabic dialect support and model fallback
- [x] Supervisor with routing, refusal handling, and per-thread memory
- [x] Streamlit chat UI with SQL transparency and raw-data table with CSV export
- [x] Visualization agent and chart tool, triggered by a dashboard button

**Planned**
- [ ] Insights agent for open-ended "why" questions (trends, anomalies, recommendations)
- [ ] Verification step that cross-checks answer figures against query results
- [ ] Typed chart requests routed through the supervisor
- [ ] Model fallback for the supervisor itself
- [ ] Persistent conversation storage (replace the in-memory checkpointer)
- [ ] Visualization and filesystem MCP servers
- [ ] Bring-your-own-data: connection-string UI and file upload (CSV/Excel)
- [ ] Docker packaging and deployment
- [ ] Automated evaluation set for SQL accuracy across languages

## Known Limitations

- Conversation state is lost when the app restarts (in-memory checkpointer).
- Business rules are specific to the NileMart schema; new datasets need their own rules.
- Query results are capped at 200 rows, and charts are meant for aggregated data.
- The supervisor model has no fallback yet (only the workers do).

## Author

**Abdel-Tawwab Ahmed**, AI Engineer · [GitHub](https://github.com/AbdelTawwab-Ahmed/Business-Intelligence-Assistant.git)