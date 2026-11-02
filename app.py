import asyncio
import streamlit as st
from agents.sql_analyst import build_agent, extract_text

st.set_page_config(page_title="NileMart BI Assistant", page_icon="📊")
# Arabic/English: each paragraph picks its own direction
st.markdown(
    "<style>.stMarkdown p, .stMarkdown li {unicode-bidi: plaintext; text-align: start;}</style>",
    unsafe_allow_html=True,
)
st.title("📊 NileMart BI Assistant")

@st.cache_resource(show_spinner="Starting agent...")
def get_agent():
    return asyncio.run(build_agent())

agent = get_agent()

if "messages" not in st.session_state:
    st.session_state.messages = []  # {"role", "content", "sql"}

with st.sidebar:
    if st.button("New chat"):
        st.session_state.messages = []
        st.rerun()

def show_sql(queries):
    if queries:
        with st.expander("SQL used"):
            for q in queries:
                st.code(q, language="sql")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        show_sql(m.get("sql"))

if prompt := st.chat_input("Ask about sales, returns, inventory..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Send only text turns (no tool messages) and cap the history
    history = [(m["role"], m["content"]) for m in st.session_state.messages][-10:]

    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                result = asyncio.run(agent.ainvoke({"messages": history}))
                answer = extract_text(result["messages"][-1])
                sql = [
                    tc["args"].get("query", "")
                    for msg in result["messages"]
                    for tc in (getattr(msg, "tool_calls", None) or [])
                    if tc["name"] == "run_sql_query"
                ]
            except Exception as e:
                answer, sql = f"Error: {e}", []
        st.markdown(answer)
        show_sql(sql)

    st.session_state.messages.append({"role": "assistant", "content": answer, "sql": sql})