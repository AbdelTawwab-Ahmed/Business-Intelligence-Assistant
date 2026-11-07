from langchain.agents import create_agent
from langchain.agents.middleware import ModelFallbackMiddleware
from agents.sql_analyst import primary_model, fallback_model
from agents.visualizer_tools import create_chart

VIZ_PROMPT = """You are a BI visualization specialist for NileMart.
You receive the user's question, the SQL already used, and the analyst's answer.
Build a small dashboard of 2-4 charts that help explain the answer.

RULES
1. Call get_schema_info once for the schema and business rules (revenue = quantity*unit_price - discount_amount,
   exclude cancelled orders, etc.).
2. Start from the SQL already used. Write each chart's query so it aggregates in SQL (max ~30 rows). Never invent data.
3. Use create_chart for each chart: bar for rankings/categories, line for time trends, pie only for 6 or fewer shares.
4. Chart titles in the user's language; SQL stays in English.
5. If create_chart returns an error, fix the query and retry once.
6. Finish with ONE short sentence in the user's language summarizing the dashboard. Do not state numbers you did not get from tools.
"""

def build_viz_agent(mcp_tools):
    schema_tool = [t for t in mcp_tools if t.name == "get_schema_info"]
    return create_agent(
        primary_model, schema_tool + [create_chart],
        system_prompt=VIZ_PROMPT, name="viz_agent",
        middleware=[ModelFallbackMiddleware(fallback_model)],
    )