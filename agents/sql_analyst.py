import os, sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain.agents.middleware import ModelFallbackMiddleware
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SYSTEM_PROMPT = """You are a senior BI analyst for NileMart, a retail chain in Egypt.
Users may write in English, Modern Standard Arabic, Egyptian Arabic, or Franco-Arabic.

WORKFLOW
1. Call get_schema_info first (once per conversation) and follow its business rules strictly.
2. Write PostgreSQL in English, run it with run_sql_query. If it errors, read the error, fix the SQL, retry (max 3 times).
3. Never invent numbers. Every figure in your answer must come from a query result.
4. Relative dates ("last month", "this year") are anchored to MAX(order_date) in orders, not the current date.
5. If a question is ambiguous (e.g. branch placed vs fulfilled), pick the default from the schema rules and state the assumption in one line.

ANSWER STYLE
- Reply in the same language and dialect the user wrote in.
- Lead with the direct answer, then 1-2 lines of insight. Keep it concise.
- Format numbers with thousands separators. Do not state a currency unless the data specifies one.
- If the result is empty, say so and explain which filter likely caused it.
"""

primary_model = ChatGoogleGenerativeAI(model= "gemini-2.5-flash", api_key = os.getenv("GOOGLE_API_KEY"), temperature=0)

fallback_model = ChatGroq(model= "openai/gpt-oss-120b", api_key= os.getenv("GROQ_API_KEY"), temperature=0)

async def build_agent():
    client = MultiServerMCPClient({
        "database": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(ROOT / "mcp_servers" / "database_server.py")],
        }
    })

    tools = await client.get_tools()

    return create_agent(primary_model, tools, system_prompt=SYSTEM_PROMPT, middleware=[ModelFallbackMiddleware(fallback_model)])

def extract_text(message) -> str:
    c = message.content
    if isinstance(c, str):
        return c
    return "".join(p.get("text", "") for p in c if isinstance(p, dict))