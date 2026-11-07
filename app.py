import asyncio, json, threading, uuid
import pandas as pd
import plotly.io as pio
import streamlit as st
from agents.graph import build_graph
from agents.sql_analyst import extract_text

st.set_page_config(page_title="NileMart BI Assistant", page_icon="📊")
st.markdown(
    "<style>.stMarkdown p, .stMarkdown li {unicode-bidi: plaintext; text-align: start;}</style>",
    unsafe_allow_html=True,
)
st.title("📊 NileMart BI Assistant")


@st.cache_resource
def get_loop():
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    return loop

loop = get_loop()

def run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, loop).result()

@st.cache_resource(show_spinner="Starting agents...")
def get_agents():
    return run_async(build_graph())

agent, viz_agent = get_agents()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

with st.sidebar:
    if st.button("New chat"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()


def parse_turn(turn):
    """SQL queries used + rows of the last successful run_sql_query, taken from tool messages."""
    queries = {}
    for m in turn:
        for tc in (getattr(m, "tool_calls", None) or []):
            if tc["name"] == "run_sql_query":
                queries[tc["id"]] = tc["args"].get("query", "")
    rows = []
    for m in turn:
        if m.type == "tool" and getattr(m, "tool_call_id", None) in queries:
            try:
                data = json.loads(extract_text(m))
            except ValueError:
                continue
            if "rows" in data:
                rows = data["rows"]
    return list(queries.values()), rows

def to_df(rows):
    df = pd.DataFrame(rows)
    for c in df.columns:          
        try:
            df[c] = pd.to_numeric(df[c])
        except (ValueError, TypeError):
            pass
    return df

def build_dashboard(m):
    brief = (f"User question: {m['question']}\n\nSQL already used:\n"
             + "\n\n".join(m["sql"]) + f"\n\nAnalyst answer:\n{m['content']}")
    result = run_async(viz_agent.ainvoke({"messages": [("user", brief)]}))
    msgs = result["messages"]
    figs = [t.artifact for t in msgs
            if t.type == "tool" and t.name == "create_chart" and t.artifact]
    note = next((txt for x in reversed(msgs)
                 if x.type == "ai" and (txt := extract_text(x).strip())), "")
    return figs, note

def show_sql(queries):
    if queries:
        with st.expander("SQL used"):
            for q in queries:
                st.code(q, language="sql")

def render_extras(m, i):
    show_sql(m.get("sql"))
    rows = m.get("rows")
    if rows:
        df = to_df(rows)
        with st.expander(f"Raw data ({len(df)} rows)"):
            st.dataframe(df)
            st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8-sig"),
                               "result.csv", "text/csv", key=f"dl_{i}")
    if m.get("figs"):
        for j, f in enumerate(m["figs"]):
            st.plotly_chart(pio.from_json(f), key=f"fig_{i}_{j}")
        if m.get("viz_note"):
            st.caption(m["viz_note"])
    elif rows and st.button("📊 Show dashboard", key=f"dash_{i}"):
        with st.spinner("Building dashboard..."):
            try:
                figs, note = build_dashboard(m)
            except Exception as e:
                figs, note = [], f"Dashboard error: {e}"
        if figs:
            m["figs"], m["viz_note"] = figs, note
            st.rerun()
        else:
            st.warning(note or "No charts were produced. Try again.")


for i, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m["role"] == "assistant":
            render_extras(m, i)

if prompt := st.chat_input("Ask about sales, returns, inventory..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                result = run_async(agent.ainvoke({"messages": [("user", prompt)]}, config))
                msgs = result["messages"]
                start = max(i for i, x in enumerate(msgs) if x.type == "human") + 1
                turn = msgs[start:]   
                answer = next(
                    (t for x in reversed(turn) if x.type == "ai" and (t := extract_text(x).strip())),
                    "No answer returned.",
                )
                sql, rows = parse_turn(turn)
            except Exception as e:
                answer, sql, rows = f"Error: {e}", [], []

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sql": sql, "rows": rows, "question": prompt}
    )
    st.rerun()   