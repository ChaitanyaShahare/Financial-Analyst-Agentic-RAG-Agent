# Extracted from notebook
================================================================================

# CELL 2
# ----------------------------------------------------------------------------
# Required packages for this lab — already installed in your local venv.
# To install standalone, uncomment the line(s) below:
# !pip install -q 'langchain>=1.0' 'langchain-core>=1.0' 'langchain-openai>=1.0' 'langchain-community>=0.3' 'langgraph>=1.0' 'langchain-tavily>=0.1' faiss-cpu pypdf langchain-text-splitters tavily-python
%pip install sqlite3

# CELL 4
# ----------------------------------------------------------------------------
import os

# Local-venv pattern: load from .env if python-dotenv is available, otherwise rely on
# environment variables already set in your shell or venv activation script.
try:
    from dotenv import load_dotenv
    load_dotenv("..\\.env")
except ImportError:
    pass

for key in ['OPENAI_API_KEY', 'TAVILY_API_KEY']:
    status = '✅ Loaded' if os.environ.get(key) else '❌ MISSING'
    print(f'{key}: {status}')


# CELL 6
# ----------------------------------------------------------------------------
from openai import OpenAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.tools import tool
# from langgraph.prebuilt import create_react_agent  # langchain 0.3.3
from langchain.agents import create_agent  # as per langchain v1.01
from langchain_tavily import TavilySearch

client = OpenAI()
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
llm = ChatOpenAI(model="gpt-5-mini")

print("All clients initialized ✅")
print(f"  Agent LLM: gpt-5-mini (via ChatOpenAI)")
print(f"  Embeddings: text-embedding-3-small")
print(f"  Web Search: Tavily API")

# CELL 9
# ----------------------------------------------------------------------------
# !unzip policy_documents.zip -d .
!tar -xf policy_documents.zip

# CELL 11
# ----------------------------------------------------------------------------
import sqlite3 
DB_PATH = "meridian_wealth.db"

# Verify database exists and has data
assert os.path.exists(DB_PATH), f"❌ Database not found at {DB_PATH}. Run Lab_04_Data_Setup.ipynb first!"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print(f"✅ Connected to database: {DB_PATH}")
print(f"   File size: {os.path.getsize(DB_PATH) / 1024:.1f} KB\n")

for table in ["clients", "holdings", "market_data"]:
    count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"   📋 {table}: {count} rows")

# Preview clients
print("\n👤 Clients:")
for row in cursor.execute("SELECT client_id, name, risk_profile, aum_inr FROM clients"):
    print(f"   {row[0]}: {row[1]} | {row[2]} | AUM: ₹{row[3]:,.0f}")

conn.close()

# CELL 13
# ----------------------------------------------------------------------------
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

POLICY_DIR = "policy_documents"
assert os.path.exists(POLICY_DIR), f"❌ Policy documents not found at {POLICY_DIR}/. Upload the policy_documents folder!"

# Step 1: Load all PDFs using LangChain's PyPDFLoader
all_pages = []
pdf_files = sorted([f for f in os.listdir(POLICY_DIR) if f.endswith(".pdf")])

print(f"📄 Loading {len(pdf_files)} policy PDFs...\n")
for pdf_file in pdf_files:
    loader = PyPDFLoader(os.path.join(POLICY_DIR, pdf_file))
    pages = loader.load()
    all_pages.extend(pages)
    print(f"   {pdf_file}: {len(pages)} pages loaded")

print(f"\n✅ Total pages extracted: {len(all_pages)}")

# CELL 14
# ----------------------------------------------------------------------------
type(all_pages[0])

# CELL 15
# ----------------------------------------------------------------------------
# Step 2: Split into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,         # ~125 words per chunk — good for policy docs
    chunk_overlap=300,       # 100 char overlap prevents losing context at chunk boundaries
    length_function=len,
    separators=["\n\n", "\n", ". ", " ", ""]  # split on paragraphs first, then sentences
)

chunks = text_splitter.split_documents(all_pages)
print(f"✅ Split into {len(chunks)} chunks (chunk_size=500, overlap=100)")


# CELL 16
# ----------------------------------------------------------------------------
# Preview a few chunks
print(f"\n📋 Sample Chunks:")
for i in [0, len(chunks)//3, 2*len(chunks)//3]:
    c = chunks[i]
    src = os.path.basename(c.metadata.get("source", "?"))
    pg = c.metadata.get("page", "?")
    print(f"\n  Chunk [{i}] from {src} (page {pg}):")
    print(f"  \"{c.page_content[:120]}...\"")


# CELL 17
# ----------------------------------------------------------------------------
print(chunks[1].metadata["page"], "\n",  chunks[1].page_content)

# CELL 18
# ----------------------------------------------------------------------------
print(chunks[2].metadata["page"], chunks[2].page_content)

# CELL 19
# ----------------------------------------------------------------------------
print(chunks[3].metadata["page"], chunks[3].page_content)

# CELL 20
# ----------------------------------------------------------------------------
print(chunks[4].metadata["page"], chunks[4].page_content)

# CELL 21
# ----------------------------------------------------------------------------
print(chunks[5].metadata["page"], chunks[5].page_content)

# CELL 22
# ----------------------------------------------------------------------------
print(chunks[6].metadata["page"], chunks[6].page_content)

# CELL 23
# ----------------------------------------------------------------------------


# CELL 24
# ----------------------------------------------------------------------------
# Step 3 & 4: Embed and build FAISS vector store
print(f"\n⏳ Embedding {len(chunks)} chunks with text-embedding-3-small...")
policy_vectorstore = FAISS.from_documents(chunks, embedding_model)
policy_retriever_chain = policy_vectorstore.as_retriever(search_kwargs={"k": 4})

print(f"\n✅ FAISS vector store built:")
print(f"   Vectors: {policy_vectorstore.index.ntotal}")
print(f"   Embedding dimensions: 1,536")
print(f"   Retriever: top-4 similarity search")

# CELL 26
# ----------------------------------------------------------------------------
test_queries = [
    "What is the maximum single stock concentration allowed?",
    "What are the drawdown limits for an Aggressive profile?",
    "How should we rebalance when tax year end is approaching?"
]

for q in test_queries:
    docs = policy_retriever_chain.invoke(q)
    print(f"🔍 Query: \"{q}\"")
    for i, d in enumerate(docs[:2], 1):  # show top-2
        src = os.path.basename(d.metadata.get("source", "?"))
        pg = d.metadata.get("page", "?")
        print(f"   [{i}] {src} (p{pg}): {d.page_content[:120]}...")
    print()

# CELL 28
# ----------------------------------------------------------------------------
def query_db(sql, params=()):
    """Execute a SQL query against the Meridian Wealth database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_client_portfolio(client_id):
    """Get full portfolio for a client with enriched market data."""
    client = query_db("SELECT * FROM clients WHERE client_id = ?", (client_id,))
    if not client:
        return None

    holdings = query_db("""
        SELECT h.ticker, h.company_name, h.shares, h.avg_cost_basis, h.current_price,
               h.sector, h.purchase_date,
               m.ytd_return_pct, m.pe_ratio, m.analyst_rating, m.high_52w, m.low_52w
        FROM holdings h
        LEFT JOIN market_data m ON h.ticker = m.ticker
        WHERE h.client_id = ?
        ORDER BY (h.shares * h.current_price) DESC
    """, (client_id,))

    return {"client": client[0], "holdings": holdings}


def search_market_data(query):
    """Search market data by ticker, sector, or company name."""
    q = query.upper().strip()
    results = query_db("SELECT * FROM market_data WHERE ticker = ?", (q,))
    if not results:
        results = query_db(
            "SELECT * FROM market_data WHERE UPPER(sector) LIKE ? OR UPPER(company_name) LIKE ? OR ticker LIKE ?",
            (f"%{q}%", f"%{q}%", f"%{q}%")
        )
    return results


# Quick test
portfolio = get_client_portfolio("CLT-001")
print(f"✅ DB helpers ready. Test: {portfolio['client']['name']} has {len(portfolio['holdings'])} holdings")

# CELL 30
# ----------------------------------------------------------------------------
@tool
def portfolio_lookup(client_id: str) -> str:
    """Look up a client's portfolio from the database: holdings, allocation, total value, and risk profile.
    Use this when you need to know what a specific client owns or their investment profile.
    Input: client ID like 'CLT-001', 'CLT-002', etc."""

    portfolio = get_client_portfolio(client_id.upper())
    if not portfolio:
        available = [r["client_id"] for r in query_db("SELECT client_id FROM clients")]
        return f"Client {client_id} not found. Available: {', '.join(available)}"

    c = portfolio["client"]
    holdings = portfolio["holdings"]

    total_current = sum(h["shares"] * h["current_price"] for h in holdings)
    total_cost = sum(h["shares"] * h["avg_cost_basis"] for h in holdings)
    overall_return = ((total_current - total_cost) / total_cost) * 100

    # Sector allocation
    sector_values = {}
    for h in holdings:
        val = h["shares"] * h["current_price"]
        sector_values[h["sector"]] = sector_values.get(h["sector"], 0) + val
    sector_pct = {s: round((v / total_current) * 100, 1) for s, v in sector_values.items()}

    # Per-holding detail
    holdings_detail = []
    for h in holdings:
        cv = h["shares"] * h["current_price"]
        gain = ((h["current_price"] - h["avg_cost_basis"]) / h["avg_cost_basis"]) * 100
        wt = (cv / total_current) * 100
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
        "relationship_manager": c["relationship_mgr"], "risk_profile": c["risk_profile"],
        "investment_horizon": c["investment_horizon"], "aum_inr": c["aum_inr"],
        "last_review": c["last_review"],
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

    results = search_market_data(query)
    if not results:
        all_tickers = [r["ticker"] for r in query_db("SELECT ticker FROM market_data")]
        return f"No data found for '{query}'. Available: {', '.join(all_tickers)}"

    formatted = [{
        "ticker": r["ticker"], "company": r["company_name"], "sector": r["sector"],
        "price": r["current_price"], "ytd_return": r["ytd_return_pct"],
        "pe_ratio": r["pe_ratio"], "analyst_rating": r["analyst_rating"],
        "52w_range": f"{r['low_52w']} - {r['high_52w']}",
        "market_cap_cr": r["market_cap_cr"]
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
                ret = ((current - cost) / cost) * 100
                return f"Return: (₹{current:,.0f} - ₹{cost:,.0f}) / ₹{cost:,.0f} = {ret:+.2f}%"

        if "percentage" in expression.lower() or "allocation" in expression.lower() or "weight" in expression.lower():
            if len(numbers) >= 2:
                part, whole = numbers[0], numbers[1]
                return f"Percentage: ₹{part:,.0f} / ₹{whole:,.0f} = {(part/whole)*100:.2f}%"

        if "compare" in expression.lower() and len(numbers) >= 2:
            a, b = numbers[0], numbers[1]
            return f"Comparison: {a:,.2f} vs {b:,.2f} | Diff: {a-b:+,.2f} ({((a-b)/b)*100:+.2f}%)"

        if len(numbers) == 2:
            a, b = numbers
            return f"Values: {a:,.2f} and {b:,.2f} | Sum: {a+b:,.2f} | Diff: {a-b:+,.2f} | Ratio: {a/b:.4f}"

        return f"Provide two numbers with operation type (return, percentage, compare). Got: '{expression}'"
    except Exception as e:
        return f"Calculation error: {str(e)}"


@tool
def policy_retriever(query: str) -> str:
    """Search Meridian Wealth Partners' investment policy PDF documents using RAG (vector similarity search).
    Use this when you need to check investment guidelines, allocation rules, rebalancing triggers,
    risk limits, concentration limits, suitability standards, or reporting requirements.
    Returns relevant excerpts with source document name and page number.
    Input: a natural language query about investment policies."""

    docs = policy_retriever_chain.invoke(query)
    results = []
    for i, doc in enumerate(docs, 1):
        src = os.path.basename(doc.metadata.get("source", "unknown"))
        pg = doc.metadata.get("page", "?")
        results.append(f"[Policy Doc {i}: {src} | Page {pg}]\n{doc.page_content}")
    return "\n\n---\n\n".join(results)



# CELL 31
# ----------------------------------------------------------------------------
# Tavily web search — live market news
web_search = TavilySearch(max_results=3, topic="news")

# All tools
tools = [portfolio_lookup, market_data_search, calculate_metrics, policy_retriever, web_search]

print(f"✅ {len(tools)} tools defined:")
for t in tools:
    print(f"   🔧 {t.name}: {t.description[:80]}...")

# CELL 33
# ----------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a senior financial analyst at Meridian Wealth Partners, a SEBI-registered wealth
management firm managing Rs 2,000 Crore in assets across 800 high-net-worth Indian clients.

Your job is to prepare comprehensive client briefings and answer investment queries using your tools.

AVAILABLE DATA SOURCES:
1. portfolio_lookup — queries the SQL database for client holdings, allocation, and risk profile
2. market_data_search — queries the SQL database for stock/sector data (price, YTD, PE, analyst ratings)
3. calculate_metrics — computes financial metrics (returns, allocation percentages, comparisons)
4. policy_retriever — RAG search over the firm's 5 investment policy PDFs (asset allocation, risk management,
   suitability standards, rebalancing protocol, reporting standards)
5. tavily_search — searches the web for latest market news, RBI updates, sector analysis

GUIDELINES:
- Always check the client's risk profile before making recommendations
- When checking policy compliance, ALWAYS use the policy_retriever tool — never guess the rules
- Cite specific policy document names and page numbers when referencing guidelines
- Do not provide compliance conclusions without first using policy_retriever.
- Do not provide market-news claims without using tavily_search.
- If required data is missing, say so explicitly instead of inferring.
- Use Indian Rupee (₹) for all amounts. Use lakhs and crores for large values.
- Include specific numbers: exact returns, allocation percentages, policy thresholds
- For briefings, structure as: Portfolio Summary → Market Context → Policy Compliance → Recommendations
"""

# agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)

agent = create_agent(
    model="openai:gpt-5-mini",
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
)

print("✅ ReAct agent created")
print(f"   LLM: gpt-5-mini (ChatOpenAI)")
print(f"   Tools: {[t.name for t in tools]}")
print(f"   Data: SQLite DB + FAISS (from 5 PDFs) + Tavily web search")

# CELL 34
# ----------------------------------------------------------------------------
from graphviz import Digraph
from IPython.display import display

def draw_financial_react_diagram():
    dot = Digraph("financial_react", format="png")
    dot.attr(rankdir="TB", splines="spline", nodesep="0.45", ranksep="0.6")
    dot.attr(bgcolor="white")

    edge_color = "#666666"
    node_outline = "#8E7CC3"
    node_fill = "#F3F0FA"

    dot.attr(
        "node",
        style="rounded,filled",
        color=node_outline,
        fillcolor=node_fill,
        fontname="Helvetica",
        fontsize="14",
        penwidth="1.5",
        margin="0.20,0.13",
    )

    dot.node("request", "user request", shape="oval")
    dot.node("model", "LLM / agent model", shape="box")
    dot.node("tools", "tools\nportfolio_lookup\nmarket_data_search\ncalculate_metrics", shape="box")
    dot.node("result", "final answer", shape="oval")

    with dot.subgraph() as s:
        s.attr(rank="same")
        s.node("tools")
        s.node("result")

    dot.edge("request", "model", color=edge_color)
    dot.edge("model", "tools", label="action", color=edge_color)
    dot.edge("tools", "model", label="observation", color=edge_color)
    dot.edge("model", "result", style="dashed", color=edge_color)

    return dot

display(draw_financial_react_diagram())

# CELL 35
# ----------------------------------------------------------------------------
from IPython.display import Image, display
display(Image(agent.get_graph().draw_mermaid_png()))

# CELL 37
# ----------------------------------------------------------------------------
query1 = """Prepare a quarterly briefing for Client CLT-001 (Rajesh Mehta).
Include: portfolio performance summary with per-holding returns, relevant market conditions
for his sectors, check if his current allocation complies with our investment policies for
his risk profile (Moderate-Aggressive), and provide any recommended rebalancing actions.
Also check for latest news on sectors he is most exposed to."""

print(f"📋 Query: {query1}")
print(f"{'='*80}\n")

# result1 = agent.invoke({"messages": [("user", query1)]})
result1 = agent.invoke(
    {
        "messages": [
            {"role": "user", "content": query1}
        ]
    }
)

print("\n🤖 AGENT RESPONSE:")
print(f"{'─'*80}")
# print(result1["messages"][-1].content)
final_msg = result1["messages"][-1]
print(final_msg.content if hasattr(final_msg, "content") else final_msg)

# CELL 39
# ----------------------------------------------------------------------------
print("🔍 AGENT TRACE — Full Message History")
print(f"{'='*80}\n")

for i, msg in enumerate(result1["messages"]):
    msg_type = type(msg).__name__

    if msg_type == "HumanMessage":
        print(f"Step {i} | 👤 USER:")
        print(f"   {msg.content[:200]}...")

    elif msg_type == "AIMessage":
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            print(f"\nStep {i} | 🧠 AGENT → calls {len(msg.tool_calls)} tool(s):")
            for tc in msg.tool_calls:
                args_str = json.dumps(tc['args'], ensure_ascii=False)[:120]
                print(f"   🔧 {tc['name']}({args_str})")
        else:
            print(f"\nStep {i} | 🤖 FINAL ANSWER ({len(msg.content)} chars)")

    elif msg_type == "ToolMessage":
        print(f"\nStep {i} | 📦 TOOL: {msg.name}")
        print(f"   {str(msg.content)[:200]}...")

print(f"\n{'='*80}")
tool_msgs = [m for m in result1["messages"] if type(m).__name__ == "ToolMessage"]
print(f"Total steps: {len(result1['messages'])} | Tool calls: {len(tool_msgs)}")
print(f"Tools used: {[m.name for m in tool_msgs]}")

# CELL 41
# ----------------------------------------------------------------------------
def call_agent(query):
  print(f"📋 Query: {query2}")
  print(f"{'='*80}\n")

  result = agent.invoke(
      {
          "messages": [
              {"role": "user", "content": query}
          ]
      }
  )

  print("\n🤖 AGENT RESPONSE:")
  print(f"{'─'*80}")

  final_msg = result["messages"][-1]
  print(final_msg.content if hasattr(final_msg, "content") else final_msg)

  tool_calls = [m for m in result["messages"] if type(m).__name__ == "ToolMessage"]
  print(f"\n📊 Tools used: {[m.name for m in tool_calls]}")

  web_calls = [m for m in result["messages"] if type(m).__name__ == "ToolMessage" and m.name == "tavily_search"]
  print(f"\n🌐 Web search called: {len(web_calls)} time(s)")

  # Verify policy_retriever was used
  policy_calls = [m for m in result["messages"] if type(m).__name__ == "ToolMessage" and m.name == "policy_retriever"]
  print(f"\n📚 Policy retriever called: {len(policy_calls)} time(s)")
  for pc in policy_calls:
      pdf_refs = re.findall(r'[A-Za-z_]+\.pdf', pc.content)
      if pdf_refs:
          print(f"   Referenced PDFs: {', '.join(set(pdf_refs))}")

  return result

# CELL 42
# ----------------------------------------------------------------------------
query2 = """Compare the IT sector exposure of Client CLT-001 and Client CLT-002.
Which client is more overweight in IT? Check our sector concentration policy limits
from the policy documents and recommend if either client needs to trim IT positions.
Also look up the latest market outlook for Indian IT sector."""

result2 = call_agent(query2)

# CELL 44
# ----------------------------------------------------------------------------
query3 = """Client CLT-003 (Amit Choudhury) wants to increase his position in Adani Enterprises.
Check his current Adani holding as a percentage of his total portfolio from the database,
then search our policy documents for the single-stock concentration limit and the stop-loss
framework for his risk profile (Aggressive). Advise whether this purchase is permissible."""

result3 = call_agent(query3)

# CELL 46
# ----------------------------------------------------------------------------
query4 = """Client CLT-005 (Karan Malhotra) has heavy exposure to Telecom and Auto sectors.
Look up his portfolio from the database, then search the web for the latest news on RBI
monetary policy decisions and their potential impact on these sectors.
Summarize the outlook and recommend any portfolio actions."""

result4 = call_agent(query4)

# CELL 48
# ----------------------------------------------------------------------------
all_results = [
    ("Client Briefing (CLT-001)", result1),
    ("IT Sector Comparison", result2),
    ("Concentration Policy Check", result3),
    ("Web Search + Sector Outlook", result4)
]

print("📊 Agent Tool Usage Summary")
print(f"{'='*70}")
print(f"{'Query':<35} {'# Tools':<10} {'Tools Used'}")
print(f"{'─'*70}")

total_calls = 0
tool_freq = {}

for name, result in all_results:
    tmsgs = [m for m in result["messages"] if type(m).__name__ == "ToolMessage"]
    tnames = [m.name for m in tmsgs]
    total_calls += len(tnames)
    for tn in tnames:
        tool_freq[tn] = tool_freq.get(tn, 0) + 1
    print(f"{name:<35} {len(tnames):<10} {', '.join(tnames)}")

print(f"{'─'*70}")
print(f"{'TOTAL':<35} {total_calls}")

print(f"\n📈 Tool Frequency:")
for tn, cnt in sorted(tool_freq.items(), key=lambda x: -x[1]):
    print(f"   {tn:<25} {cnt:>2} {'█' * cnt}")

# Data infrastructure summary
conn = sqlite3.connect(DB_PATH)
print(f"\n🏗️ Data Infrastructure Summary:")
print(f"   SQLite: {DB_PATH} ({os.path.getsize(DB_PATH)/1024:.0f} KB)")
for table in ["clients", "holdings", "market_data"]:
    cnt = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"     → {table}: {cnt} rows")
conn.close()
print(f"   FAISS: {policy_vectorstore.index.ntotal} vectors from {len(pdf_files)} policy PDFs")
print(f"   Web: Tavily API (live search)")

# CELL 50
# ----------------------------------------------------------------------------
# 1. Zip the policy_documents folder and the meridian_wealth.db file
# !zip -r backup.zip policy_documents/ meridian_wealth.db

# 2. Unzip the file (uncomment the line below to run it)
# !unzip backup.zip -d unzipped_backup/

# CELL 51
# ----------------------------------------------------------------------------
# !rm -rf policy_documents

# CELL 52
# ----------------------------------------------------------------------------
# !unzip policy_documents.zip -d .

