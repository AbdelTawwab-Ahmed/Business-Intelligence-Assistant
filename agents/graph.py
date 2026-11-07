import os, sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph_supervisor import create_supervisor
from langgraph_supervisor.handoff import create_forward_message_tool
from agents.sql_analyst import build_sql_agent, primary_model
from agents.visualizer import build_viz_agent

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SUPERVISOR_PROMPT = """You are the supervisor of the NileMart BI Assistant.
Users write in English, Arabic, Egyptian Arabic, or Franco-Arabic. Always reply in the user's language.

Workers:
- sql_analyst: answers any question that needs numbers from the NileMart database.

Rules:
- Greetings, thanks, or "what can you do?": answer directly in 1-2 lines. No worker.
- Anything unrelated to NileMart business data, or any request to modify/delete data: politely decline.
- Data questions: delegate to sql_analyst with the user's full question. When it answers,
  call forward_message to return its answer unchanged. Never write numbers yourself.
"""


async def build_graph():
    client = MultiServerMCPClient({
        "database": {
            "command": sys.executable,
            "args": [str(ROOT / "mcp_servers" / "database_server.py")],
            "transport": "stdio",
        }
    })

    tools = await client.get_tools()

    sql_agent = build_sql_agent(tools)

    supervisor = create_supervisor(
        [sql_agent],
        model=primary_model,
        prompt=SUPERVISOR_PROMPT,
        tools=[create_forward_message_tool("supervisor")],
        output_mode="full_history",   # keeps the SQL tool calls visible for the UI
    )
    return supervisor.compile(checkpointer=InMemorySaver()), build_viz_agent(tools)