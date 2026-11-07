import os, json, re
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import time
from psycopg2 import sql

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

mcp = FastMCP("bi-database")

MAX_ROWS = 200
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|call|do)\b", re.I
)


BUSINESS_RULES = """
BUSINESS RULES
- orders has NO total column. Line revenue = quantity*unit_price - discount_amount
  (discount_amount is PER LINE, not per unit). Exclude order_status='cancelled'.
- "Profit" = gross profit = line revenue - quantity*order_items.unit_cost
  (use order_items.unit_cost, NOT products.unit_cost). Subtract refunds only if the user asks for net profit.
- Refunds are in return_items.refund_amount (not payments). Count returns with return_status IN ('approved','completed').
- "By branch": use COALESCE(orders.branch_id, orders.fulfillment_branch_id).
  In-store orders have branch_id (where sold); online orders have NULL branch_id
  (65% of orders) and fall back to the fulfilling branch. State this assumption in one line.
- Join return_items to returns / order_items on BOTH ids (composite keys).
- Relative dates ("last month", "this year") are anchored to MAX(order_date), not today's date.
"""

_cache = {"t": 0.0, "doc": ""}
CACHE_TTL = 600  # seconds

def build_schema_doc() -> str:
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    conn.set_session(readonly=True, autocommit=True)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema='public'
            ORDER BY table_name, ordinal_position
        """)
        tables = {}
        for t, c, d in cur.fetchall():
            tables.setdefault(t, []).append((c, d))

        out = ["DATABASE SCHEMA (PostgreSQL, auto-generated)\n"]
        for t, cols in tables.items():
            exprs = [sql.SQL("COUNT(*)")] + [
                sql.SQL("COUNT({})").format(sql.Identifier(c)) for c, _ in cols
            ]
            cur.execute(sql.SQL("SELECT {} FROM {}").format(
                sql.SQL(", ").join(exprs), sql.Identifier(t)))
            total, *nonnull = cur.fetchone()
            out.append(f"{t} ({total:,} rows)")

            for (c, d), nn in zip(cols, nonnull):
                notes = []
                if nn < total:
                    notes.append(f"{(total - nn) / total:.1%} NULL")
                ci, ti = sql.Identifier(c), sql.Identifier(t)
                if nn and (d == "date" or d.startswith("timestamp")):
                    cur.execute(sql.SQL("SELECT MIN({0}), MAX({0}) FROM {1}").format(ci, ti))
                    lo, hi = cur.fetchone()
                    notes.append(f"range {lo} to {hi}")
                elif nn and d in ("character varying", "text"):
                    cur.execute(sql.SQL(
                        "SELECT DISTINCT {0} FROM {1} WHERE {0} IS NOT NULL ORDER BY 1 LIMIT 31"
                    ).format(ci, ti))
                    vals = [r[0] for r in cur.fetchall()]
                    if len(vals) <= 30:
                        notes.append("values: " + ", ".join(vals))
                extra = f"  [{'; '.join(notes)}]" if notes else ""
                out.append(f"  - {c}: {d}{extra}")
            out.append("")

        cur.execute("""
            SELECT conrelid::regclass::text, contype, pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE connamespace = 'public'::regnamespace AND contype IN ('p','f')
            ORDER BY 1, 2 DESC
        """)
        out.append("KEYS")
        for t, kind, definition in cur.fetchall():
            out.append(f"  {t}: {definition}")
        return "\n".join(out) + "\n" + BUSINESS_RULES
    finally:
        conn.close()

@mcp.tool()
def get_schema_info() -> str:
    """Return the live database schema, keys, valid values, NULL stats, and business rules. Call this first."""
    if not _cache["doc"] or time.time() - _cache["t"] > CACHE_TTL:
        _cache["doc"] = build_schema_doc()
        _cache["t"] = time.time()
    return _cache["doc"]


def execute_readonly(query: str) -> list[dict]:
    q = query.strip().rstrip(";").strip()
    if not re.match(r"^(select|with)\b", q, re.I):
        raise ValueError("Only SELECT/WITH queries are allowed.")
    if ";" in q or FORBIDDEN.search(q):
        raise ValueError("Query contains forbidden keywords or multiple statements.")
    conn = None
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SET statement_timeout = 10000;")
            cur.execute(q)
            return cur.fetchmany(MAX_ROWS)
    finally:
        if conn:
            conn.close()


@mcp.tool()
def run_sql_query(query: str) -> str:
    """Run a read-only SELECT query (max 200 rows). Returns JSON rows or an error message."""
    try:
        rows = execute_readonly(query)
        return json.dumps({"row_count": len(rows), "rows": rows}, default=str, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
    

if __name__ == "__main__":
    mcp.run()