"""
Run the real financial agent from the command line and print its trace.

Needs OPENAI_API_KEY and TAVILY_API_KEY in the .env file (this costs API credits).
Run from the project root:
    python examples/run_agent.py            # runs sample question 1
    python examples/run_agent.py 3          # runs sample question 3
    python examples/run_agent.py "your own question about CLT-004"
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Src import agent

SAMPLE_QUERIES = {
    "1": """Prepare a quarterly briefing for Client CLT-001 (Rajesh Mehta).
Include: portfolio performance summary with per-holding returns, relevant market conditions
for his sectors, check if his current allocation complies with our investment policies for
his risk profile (Moderate-Aggressive), and provide any recommended rebalancing actions.
Also check for latest news on sectors he is most exposed to.""",
    "2": """Compare the IT sector exposure of Client CLT-001 and Client CLT-002.
Which client is more overweight in IT? Check our sector concentration policy limits
from the policy documents and recommend if either client needs to trim IT positions.
Also look up the latest market outlook for Indian IT sector.""",
    "3": """Client CLT-003 (Amit Choudhury) wants to increase his position in Adani Enterprises.
Check his current Adani holding as a percentage of his total portfolio from the database,
then search our policy documents for the single-stock concentration limit and the stop-loss
framework for his risk profile (Aggressive). Advise whether this purchase is permissible.""",
    "4": """Client CLT-005 (Karan Malhotra) has heavy exposure to Telecom and Auto sectors.
Look up his portfolio from the database, then search the web for the latest news on RBI
monetary policy decisions and their potential impact on these sectors.
Summarize the outlook and recommend any portfolio actions.""",
}


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "1"
    query = SAMPLE_QUERIES.get(arg, arg)

    agent.initialize_agent_components()   # loads LLM, builds the RAG index, web search
    print(f"\nQUESTION:\n{query}\n")

    result = agent.invoke_agent(query)

    print(agent.format_agent_trace(result))   # CONCEPT: Observability - see every step
    print("\nFINAL ANSWER:\n")
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
