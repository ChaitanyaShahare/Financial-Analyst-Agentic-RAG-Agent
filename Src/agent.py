"""
ReAct (Reasoning + Acting) Agent for financial analysis.

This module implements the financial analyst agent with tools for:
- Portfolio lookup (SQL database)
- Market data search (SQL database)
- Financial metric calculations
- Policy document retrieval (RAG)
- Live web search
- Agent orchestration and response generation
"""

import json
import re
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

# Load environment variables FIRST - use absolute path to .env
from dotenv import load_dotenv
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=str(_env_path), override=True)

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_tavily import TavilySearch

from . import db_queries
from . import schemas


# Global variables initialized at module import time
embedding_model = None
llm = None
policy_retriever = None
web_search = None


def initialize_agent_components():
    """Initialize all agent components (LLM, tools, retriever)."""
    global embedding_model, llm, policy_retriever, web_search
    
    # Validate API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    
    print(f"DEBUG: OPENAI_API_KEY present: {bool(openai_key)}")
    print(f"DEBUG: TAVILY_API_KEY present: {bool(tavily_key)}")
    
    if not openai_key:
        raise ValueError("OPENAI_API_KEY not found in environment. Check .env file.")
    if not tavily_key:
        raise ValueError("TAVILY_API_KEY not found in environment. Check .env file.")
    
    from langchain_openai import OpenAIEmbeddings
    from .rag_pipeline import initialize_rag_pipeline
    
    print("Initializing embedding model...")
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-small", api_key=openai_key)
    print("✅ Embedding model initialized")
    
    print("Initializing LLM (gpt-5-mini)...")
    llm = ChatOpenAI(model="gpt-5-mini", api_key=openai_key, temperature=0.7)
    print("✅ LLM initialized")
    
    # Initialize RAG pipeline
    try:
        _, policy_retriever, _ = initialize_rag_pipeline(data="policy_documents")
        print("✅ RAG pipeline initialized")
    except Exception as e:
        print(f"⚠️  RAG pipeline initialization failed: {e}")
        policy_retriever = None
    
    # Initialize web search
    print("Initializing web search...")
    web_search = TavilySearch(max_results=3, topic="news", api_key=tavily_key)
    print("✅ Web search initialized")


# Tool Definitions (from notebook cells 30-31)

@tool
def portfolio_lookup(client_id: str) -> str:
    """Look up a client's portfolio from the database: holdings, allocation, total value, and risk profile.
    Use this when you need to know what a specific client owns or their investment profile.
    Input: client ID like 'CLT-001', 'CLT-002', etc."""
    
    portfolio = db_queries.get_client_portfolio(client_id.upper())
    if not portfolio:
        available = db_queries.get_all_clients()
        client_ids = [r["client_id"] for r in available]
        return f"Client {client_id} not found. Available: {', '.join(client_ids)}"

    c = portfolio["client"]
    holdings = portfolio["holdings"]

    total_current = sum(h["shares"] * h["current_price"] for h in holdings)
    total_cost = sum(h["shares"] * h["avg_cost_basis"] for h in holdings)
    overall_return = ((total_current - total_cost) / total_cost) * 100 if total_cost > 0 else 0

    # Sector allocation
    sector_values = {}
    for h in holdings:
        val = h["shares"] * h["current_price"]
        sector_values[h["sector"]] = sector_values.get(h["sector"], 0) + val
    sector_pct = {s: round((v / total_current) * 100, 1) for s, v in sector_values.items()} if total_current > 0 else {}

    # Per-holding detail
    holdings_detail = []
    for h in holdings:
        cv = h["shares"] * h["current_price"]
        gain = ((h["current_price"] - h["avg_cost_basis"]) / h["avg_cost_basis"]) * 100 if h["avg_cost_basis"] > 0 else 0
        wt = (cv / total_current) * 100 if total_current > 0 else 0
        holdings_detail.append({
            "ticker": h["ticker"], "company": h["company_name"],
            "shares": h["shares"], "avg_cost": h["avg_cost_basis"],
            "current_price": h["current_price"], "current_value": cv,
            "unrealized_gain_pct": round(gain, 1), "portfolio_weight_pct": round(wt, 1),
            "sector": h["sector"], "ytd_return": h["ytd_return_pct"],
            "analyst_rating": h["analyst_rating"], "purchase_date": h["purchase_date"]
        })

    result = {
        "client_id": c["client_id"], "name": c["name"],
        "risk_profile": c["risk_profile"],
        "aum_inr": c["aum_inr"],
        "total_portfolio_value": round(total_current),
        "total_cost_basis": round(total_cost),
        "overall_return_pct": round(overall_return, 1),
        "sector_allocation": sector_pct,
        "holdings": holdings_detail
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


@tool
def market_data_search(query: str) -> str:
    """Search the market database for stock tickers or sectors. Returns current price, YTD returns,
    PE ratio, analyst ratings, 52-week range, and market cap. Use this when you need market
    performance data for specific stocks or want to compare sector performance.
    Input: a stock ticker (e.g. 'RELIANCE'), sector name (e.g. 'IT', 'Banking'), or company name."""
    
    results = db_queries.search_market_data(query)
    if not results:
        all_tickers = [r["ticker"] for r in db_queries.query_db("SELECT ticker FROM market_data")]
        return f"No data found for '{query}'. Available: {', '.join(all_tickers[:10])}"

    formatted = [{
        "ticker": r["ticker"], "company": r["company_name"], "sector": r["sector"],
        "price": r["current_price"], "ytd_return": r["ytd_return_pct"],
        "pe_ratio": r.get("pe_ratio"), "analyst_rating": r.get("analyst_rating"),
        "52w_range": f"{r['low_52w']} - {r['high_52w']}",
        "market_cap_cr": r.get("market_cap_cr")
    } for r in results]
    return json.dumps(formatted, indent=2, ensure_ascii=False)


@tool
def calculate_metrics(expression: str) -> str:
    """Perform financial calculations: returns, percentages, allocations, comparisons.
    Input: describe the calculation, e.g. 'return on 596000 vs cost 430000'
    or 'percentage of 350000 out of 2530000' or 'compare 18.5 vs 12.3'."""
    try:
        numbers = [float(x.replace(',', '')) for x in re.findall(r'[\d,]+\.?\d*', expression)]

        if "return" in expression.lower() or "gain" in expression.lower():
            if len(numbers) >= 2:
                current, cost = numbers[0], numbers[1]
                ret = ((current - cost) / cost) * 100 if cost != 0 else 0
                return f"Return: (₹{current:,.0f} - ₹{cost:,.0f}) / ₹{cost:,.0f} = {ret:+.2f}%"

        if "percentage" in expression.lower() or "allocation" in expression.lower() or "weight" in expression.lower():
            if len(numbers) >= 2:
                part, whole = numbers[0], numbers[1]
                pct = (part/whole)*100 if whole != 0 else 0
                return f"Percentage: ₹{part:,.0f} / ₹{whole:,.0f} = {pct:.2f}%"

        if "compare" in expression.lower() and len(numbers) >= 2:
            a, b = numbers[0], numbers[1]
            diff_pct = ((a-b)/b)*100 if b != 0 else 0
            return f"Comparison: {a:,.2f} vs {b:,.2f} | Diff: {a-b:+,.2f} ({diff_pct:+.2f}%)"

        if len(numbers) == 2:
            a, b = numbers
            ratio = a/b if b != 0 else 0
            return f"Values: {a:,.2f} and {b:,.2f} | Sum: {a+b:,.2f} | Diff: {a-b:+,.2f} | Ratio: {ratio:.4f}"

        return f"Provide two numbers with operation type (return, percentage, compare). Got: '{expression}'"
    except Exception as e:
        return f"Calculation error: {str(e)}"


@tool
def policy_retriever_tool(query: str) -> str:
    """Search Meridian Wealth Partners' investment policy PDF documents using RAG (vector similarity search).
    Use this when you need to check investment guidelines, allocation rules, rebalancing triggers,
    risk limits, concentration limits, suitability standards, or reporting requirements.
    Returns relevant excerpts with source document name and page number.
    Input: a natural language query about investment policies."""
    
    if policy_retriever is None:
        return "Policy retriever not available. RAG pipeline failed to initialize."
    
    try:
        docs = policy_retriever.invoke(query)
        results = []
        for i, doc in enumerate(docs, 1):
            src = os.path.basename(doc.metadata.get("source", "unknown"))
            pg = doc.metadata.get("page", "?")
            results.append(f"[Policy Doc {i}: {src} | Page {pg}]\n{doc.page_content}")
        return "\n\n---\n\n".join(results)
    except Exception as e:
        return f"Policy search error: {str(e)}"


def create_financial_agent():
    """
    Create and return the ReAct financial analyst agent.
    
    Returns:
        Configured agent executor
    """
    if llm is None:
        raise RuntimeError("Agent not initialized. Call initialize_agent_components() first.")
    
    # System prompt from notebook cell 33
    SYSTEM_PROMPT = """You are a senior financial analyst at Meridian Wealth Partners, a SEBI-registered wealth
management firm managing Rs 2,000 Crore in assets across 800 high-net-worth Indian clients.

Your job is to prepare comprehensive client briefings and answer investment queries using your tools.

AVAILABLE DATA SOURCES:
1. portfolio_lookup — queries the SQL database for client holdings, allocation, and risk profile
2. market_data_search — queries the SQL database for stock/sector data (price, YTD, PE, analyst ratings)
3. calculate_metrics — computes financial metrics (returns, allocation percentages, comparisons)
4. policy_retriever_tool — RAG search over the firm's investment policy PDFs
5. tavily_search — searches the web for latest market news, RBI updates, sector analysis

GUIDELINES:
- Always check the client's risk profile before making recommendations
- When checking policy compliance, ALWAYS use the policy_retriever_tool — never guess the rules
- Cite specific policy document names and page numbers when referencing guidelines
- Do not provide compliance conclusions without first using policy_retriever_tool
- Do not provide market-news claims without using web search
- If required data is missing, say so explicitly instead of inferring
- Use Indian Rupee (₹) for all amounts. Use lakhs and crores for large values.
- Include specific numbers: exact returns, allocation percentages, policy thresholds
- For briefings, structure as: Portfolio Summary → Market Context → Policy Compliance → Recommendations
"""
    
    tools = [portfolio_lookup, market_data_search, calculate_metrics, policy_retriever_tool, web_search]
    
    agent = create_agent(
        model="openai:gpt-5-mini",
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )
    
    return agent


def invoke_agent(query: str, agent=None) -> Dict[str, Any]:
    """
    Invoke the agent with a query.
    
    Args:
        query: User query string
        agent: Agent instance (if None, creates new one)
        
    Returns:
        Agent response with messages and tool usage
    """
    if agent is None:
        agent = create_financial_agent()
    
    result = agent.invoke({
        "messages": [
            {"role": "user", "content": query}
        ]
    })
    
    return result

