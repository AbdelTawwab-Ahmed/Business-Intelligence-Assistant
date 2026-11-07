import pandas as pd
import plotly.express as px
from langchain_core.tools import tool
from mcp_servers.database_server import execute_readonly

@tool(response_format="content_and_artifact")
def create_chart(query: str, chart_type: str, x: str, y: str, title: str, color: str | None = None):
    """Run a read-only SQL query and build a chart from its result.
    chart_type: bar | line | pie | scatter. x and y must be column names in the query result
    (pie: x = labels, y = values). color: optional column to split series.
    Aggregate in SQL (max 200 rows). The chart is shown to the user automatically."""
    try:
        df = pd.DataFrame(execute_readonly(query))
    except Exception as e:
        return f"Query error: {e}", None
    if df.empty:
        return "Query returned no rows.", None
    missing = [c for c in (x, y, color) if c and c not in df.columns]
    if missing:
        return f"Columns not in result: {missing}. Available: {list(df.columns)}", None

    df[y] = pd.to_numeric(df[y], errors="coerce")   # Decimal -> float
    if chart_type == "pie":
        fig = px.pie(df, names=x, values=y, title=title)
    elif chart_type in ("bar", "line", "scatter"):
        fig = getattr(px, chart_type)(df, x=x, y=y, color=color, title=title)
    else:
        return "chart_type must be bar, line, pie or scatter.", None
    return f"Chart created ({chart_type}, {len(df)} rows).", fig.to_json()