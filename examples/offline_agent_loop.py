"""
Offline teaching demo: watch the agent loop run WITHOUT any API keys.

Run from the project root:
    python examples/offline_agent_loop.py

The real agent uses OpenAI's gpt-5-mini to decide what to do. Here we swap in a
"scripted" fake model that replies with pre-written decisions, so you can see
the loop, the step limit and short-term memory work for free and repeatably.
The TOOLS are the real ones from Src/agent.py and read the real SQLite database.
"""

import sys
from pathlib import Path

# Make "from Src import ..." work when this file is run directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError

from Src.agent import portfolio_lookup, calculate_metrics, format_agent_trace


class ScriptedLLM(GenericFakeChatModel):
    """A fake LLM that returns pre-written replies in order.

    A real LLM would *choose* these replies after reading the conversation.
    bind_tools() is normally how the tool list is sent to the model; the fake
    model already knows its script, so it just ignores the list.
    """

    def bind_tools(self, tools, **kwargs):
        return self


def call(tool_name: str, args: dict, call_id: str) -> AIMessage:
    """An AIMessage that asks for one tool call (what a real LLM would send)."""
    return AIMessage(content="", tool_calls=[{"name": tool_name, "args": args, "id": call_id}])


def demo_operating_loop():
    # CONCEPT: Core operating loop (perceive -> reason -> act -> observe -> repeat)
    print("\n### DEMO 1: the operating loop ###\n")
    script = iter([
        # Reason: "I need the client's portfolio first."      -> Act
        call("portfolio_lookup", {"client_id": "CLT-001"}, "call_1"),
        # Reason: "Now compute the return from what I observed." -> Act
        call("calculate_metrics", {"expression": "return on 2532500 vs cost 1894000"}, "call_2"),
        # Reason: "I have enough information." -> final answer (no tool call ends the loop)
        AIMessage(content="Rajesh Mehta's portfolio is worth about Rs 25.3 lakh, a +33.71% return on cost."),
    ])
    agent = create_agent(model=ScriptedLLM(messages=script), tools=[portfolio_lookup, calculate_metrics])
    result = agent.invoke({"messages": [{"role": "user", "content": "How is client CLT-001 doing?"}]})
    print(format_agent_trace(result, preview_chars=120))


def demo_step_limit():
    # CONCEPT: Safety limit - a model that never stops calling tools is cut off.
    print("\n### DEMO 2: the step limit (safety) ###\n")
    endless = (call("calculate_metrics", {"expression": "compare 2 vs 1"}, f"c{i}") for i in range(1000))
    agent = create_agent(model=ScriptedLLM(messages=endless), tools=[calculate_metrics])
    try:
        agent.invoke({"messages": [{"role": "user", "content": "loop forever"}]},
                     config={"recursion_limit": 6})
    except GraphRecursionError:
        print("Stopped by recursion_limit=6: the agent was not allowed to loop forever.")
        print("The real app uses MAX_AGENT_STEPS = 25 (see Src/agent.py).")


def demo_short_term_memory():
    # CONCEPT: Short-term memory - a checkpointer keeps the conversation per thread.
    print("\n### DEMO 3: short-term memory ###\n")
    script = iter([AIMessage(content="Noted: you look after CLT-002."),
                   AIMessage(content="You told me you look after CLT-002."),
                   AIMessage(content="I don't know yet - this is a new conversation.")])
    agent = create_agent(model=ScriptedLLM(messages=script), tools=[], checkpointer=InMemorySaver())

    session_a = {"configurable": {"thread_id": "session-A"}}
    session_b = {"configurable": {"thread_id": "session-B"}}

    r1 = agent.invoke({"messages": [{"role": "user", "content": "I look after CLT-002."}]}, session_a)
    print(f"session-A, turn 1: {len(r1['messages'])} messages in memory")
    r2 = agent.invoke({"messages": [{"role": "user", "content": "Which client do I look after?"}]}, session_a)
    print(f"session-A, turn 2: {len(r2['messages'])} messages in memory (turn 1 was remembered)")
    r3 = agent.invoke({"messages": [{"role": "user", "content": "Which client do I look after?"}]}, session_b)
    print(f"session-B, turn 1: {len(r3['messages'])} messages in memory (a separate conversation)")


if __name__ == "__main__":
    demo_operating_loop()
    demo_step_limit()
    demo_short_term_memory()
