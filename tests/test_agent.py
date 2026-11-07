import asyncio
from agents.sql_analyst import build_sql_agent, extract_text


QUESTIONS = [
    # "What are the top 5 products by profit?",
    "إيه أكتر فرع بيرتجع منتجات؟",
    # "3ayez a3raf ad eh el revenue bta3 el online vs in_store?",
]


async def main():
    agent = await build_sql_agent()

    with open(r'./agent_output.txt', mode='w', encoding='utf-8') as f:

        for i, q in enumerate(QUESTIONS):
            f.write(f"\nQ{i+1}: {q}")
            result = await agent.ainvoke({"messages":[("user", q)]})
            f.write(f"\n\nA{i+1}: {extract_text(result["messages"][-1])}\n")

    print("\nDone successfully!")

asyncio.run(main())