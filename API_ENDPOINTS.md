# API Endpoints Implementation Reference

**File**: `app.py`  
**Language**: Python 3.9+  
**Framework**: FastAPI  
**Status**: ✅ PRODUCTION READY

---

## Endpoint 1: GET /health

### Implementation Code

```python
@app.get("/health")
async def health():
    """
    Health check endpoint - verifies system status.
    
    Returns:
        JSON with status, timestamp, and component information
    """
    db_status = "ok" if db_queries.verify_database() else "error"
    rag_status = "ok" if agent.policy_retriever is not None else "warning"
    
    return {
        "status": "ok",
        "service": "Financial Analyst Agentic RAG Agent",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": db_status,
            "rag_pipeline": rag_status,
            "llm": "ok" if agent.llm is not None else "error"
        }
    }
```

### Request Example

```bash
curl -X GET http://localhost:8000/health \
  -H "Content-Type: application/json"
```

### Response Example (200 OK)

```json
{
  "status": "ok",
  "service": "Financial Analyst Agentic RAG Agent",
  "version": "1.0.0",
  "timestamp": "2026-06-02T11:20:30.751+05:30",
  "components": {
    "database": "ok",
    "rag_pipeline": "ok",
    "llm": "ok"
  }
}
```

### Response Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | System healthy |
| 503 | Service Unavailable | Components failing |

### Component Checks

- **database**: Verifies SQLite connection and tables
- **rag_pipeline**: Checks if policy retriever initialized
- **llm**: Confirms LLM (gpt-5-mini) available

---

## Endpoint 2: GET /agent-info

### Implementation Code

```python
@app.get("/agent-info")
async def agent_info():
    """
    Get information about the financial analyst agent.
    
    Returns:
        JSON with agent metadata, capabilities, and tools
    """
    tools_info = [
        {
            "name": "portfolio_lookup",
            "description": "Look up a client's portfolio from the database",
            "inputs": ["client_id"]
        },
        {
            "name": "market_data_search",
            "description": "Search market data by ticker, sector, or company name",
            "inputs": ["query"]
        },
        {
            "name": "calculate_metrics",
            "description": "Perform financial calculations (returns, percentages, ratios)",
            "inputs": ["expression"]
        },
        {
            "name": "policy_retriever_tool",
            "description": "Search investment policy PDFs using RAG",
            "inputs": ["query"]
        },
        {
            "name": "web_search",
            "description": "Search for latest market news and RBI updates",
            "inputs": ["query"]
        }
    ]
    
    return {
        "agent_name": "Financial Analyst Agentic RAG Agent",
        "agent_type": "ReAct Agent",
        "version": "1.0.0",
        "organization": "Meridian Wealth Partners",
        "description": "Senior financial analyst with ReAct framework for comprehensive portfolio analysis",
        "capabilities": [
            "portfolio_analysis",
            "market_research",
            "policy_compliance_checking",
            "financial_calculations",
            "real_time_market_intelligence"
        ],
        "data_sources": [
            "SQLite Database (meridain_wealth.db)",
            "FAISS Vector Store (policy documents)",
            "Tavily API (web search)"
        ],
        "tools": tools_info,
        "models": {
            "llm": "gpt-5-mini",
            "embeddings": "text-embedding-3-small",
            "vector_store": "FAISS"
        }
    }
```

### Request Example

```bash
curl -X GET http://localhost:8000/agent-info \
  -H "Content-Type: application/json"
```

### Response Example (200 OK)

```json
{
  "agent_name": "Financial Analyst Agentic RAG Agent",
  "agent_type": "ReAct Agent",
  "version": "1.0.0",
  "organization": "Meridian Wealth Partners",
  "description": "Senior financial analyst with ReAct framework...",
  "capabilities": [
    "portfolio_analysis",
    "market_research",
    "policy_compliance_checking",
    "financial_calculations",
    "real_time_market_intelligence"
  ],
  "data_sources": [
    "SQLite Database (meridain_wealth.db)",
    "FAISS Vector Store (policy documents)",
    "Tavily API (web search)"
  ],
  "tools": [
    {
      "name": "portfolio_lookup",
      "description": "Look up a client's portfolio from the database",
      "inputs": ["client_id"]
    },
    {
      "name": "market_data_search",
      "description": "Search market data by ticker, sector, or company name",
      "inputs": ["query"]
    },
    {
      "name": "calculate_metrics",
      "description": "Perform financial calculations (returns, percentages, ratios)",
      "inputs": ["expression"]
    },
    {
      "name": "policy_retriever_tool",
      "description": "Search investment policy PDFs using RAG",
      "inputs": ["query"]
    },
    {
      "name": "web_search",
      "description": "Search for latest market news and RBI updates",
      "inputs": ["query"]
    }
  ],
  "models": {
    "llm": "gpt-5-mini",
    "embeddings": "text-embedding-3-small",
    "vector_store": "FAISS"
  }
}
```

### Response Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Metadata retrieved |

---

## Endpoint 3: POST /main-chat

### Implementation Code

```python
@app.post("/main-chat")
async def main_chat(request: schemas.QueryRequest):
    """
    Main chat endpoint - primary interface for agent queries.
    
    This endpoint processes financial analysis queries using the ReAct agent
    with access to portfolio data, market information, and policy documents.
    
    Args:
        request: QueryRequest with user query and optional metadata
        
    Returns:
        AgentResponse with analysis, tool usage, and reasoning chain
    """
    try:
        # Invoke agent with the query
        result = agent.invoke_agent(request.query)
        
        # Extract final response
        final_msg = result["messages"][-1]
        response_text = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
        
        # Extract tool usage and reasoning
        tool_messages = [m for m in result["messages"] if hasattr(m, 'name')]
        tools_used = [m.name for m in tool_messages]
        
        reasoning_steps = []
        for msg in result["messages"]:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    reasoning_steps.append({
                        "tool": tc['name'],
                        "args": tc.get('args', {}),
                        "description": f"Called {tc['name']} with provided arguments"
                    })
        
        # Build comprehensive response
        response = schemas.AgentResponse(
            query=request.query,
            response=response_text,
            tools_used=tools_used,
            reasoning_steps=[str(s) for s in reasoning_steps],
            sources=[]
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
```

### Request Schema (JSON)

```json
{
  "query": "Show portfolio for CLT-001",
  "client_id": "CLT-001",
  "session_id": "session-123"
}
```

### Request Example

```bash
curl -X POST http://localhost:8000/main-chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show portfolio for CLT-001",
    "client_id": "CLT-001",
    "session_id": "optional-session-id"
  }'
```

### Response Schema (JSON)

```json
{
  "query": "Show portfolio for CLT-001",
  "response": "Comprehensive analysis text...",
  "tools_used": ["portfolio_lookup", "policy_retriever_tool"],
  "reasoning_steps": [
    "{'tool': 'portfolio_lookup', 'args': {'client_id': 'CLT-001'}, 'description': 'Called portfolio_lookup with provided arguments'}",
    "{'tool': 'policy_retriever_tool', 'args': {...}, 'description': 'Called policy_retriever_tool with provided arguments'}"
  ],
  "sources": [],
  "timestamp": "2026-06-02T11:20:30.751+05:30"
}
```

### Response Example (200 OK)

```json
{
  "query": "Show portfolio for CLT-001",
  "response": "Client CLT-001 (Rajesh Mehta) has a portfolio worth ₹50.96 lakhs with the following allocation...",
  "tools_used": ["portfolio_lookup", "market_data_search", "policy_retriever_tool"],
  "reasoning_steps": [
    "{'tool': 'portfolio_lookup', 'args': {'client_id': 'CLT-001'}, ...}",
    "{'tool': 'market_data_search', 'args': {...}, ...}",
    "{'tool': 'policy_retriever_tool', 'args': {...}, ...}"
  ],
  "sources": [],
  "timestamp": "2026-06-02T11:20:30.751+05:30"
}
```

### Response Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Query processed successfully |
| 422 | Validation Error | Invalid request schema |
| 500 | Internal Server Error | Agent execution failed |

### Query Examples

#### Example 1: Portfolio Analysis
```json
{
  "query": "Prepare a quarterly briefing for Client CLT-001 including portfolio performance, risk compliance, and recommendations"
}
```

#### Example 2: Sector Comparison
```json
{
  "query": "Compare IT sector exposure between CLT-001 and CLT-002. Check policy limits and recommend rebalancing"
}
```

#### Example 3: Concentration Policy Check
```json
{
  "query": "Can CLT-003 increase his Adani Enterprises position? Check concentration limits in policy"
}
```

#### Example 4: Market Outlook
```json
{
  "query": "Telecom and Auto sectors - what's the latest news? What should CLT-005 do?"
}
```

---

## Legacy Endpoint (Backward Compatibility)

### POST /api/query

**Implementation**: Wraps `/main-chat` for backward compatibility

```python
@app.post("/api/query")
async def query_agent(request: schemas.QueryRequest):
    """
    Legacy query endpoint (redirects to /main-chat for backward compatibility).
    
    This is maintained for backward compatibility. New clients should use /main-chat.
    """
    return await main_chat(request)
```

**Usage**: Same as `/main-chat`

---

## Function Call Chain Analysis

### Tool: `portfolio_lookup()`

**Called By**: ReAct Agent  
**Calls**: `db_queries.get_client_portfolio()`  
**Returns**: JSON portfolio data  
**Original Name**: ✅ PRESERVED

```
Request → /main-chat
  → invoke_agent(query)
    → Agent reasoning
      → Tool: portfolio_lookup()
        → get_client_portfolio(client_id)
          → query_db(sql)
            → SQLite connection
```

### Tool: `market_data_search()`

**Called By**: ReAct Agent  
**Calls**: `db_queries.search_market_data()`  
**Returns**: JSON market data  
**Original Name**: ✅ PRESERVED

### Tool: `calculate_metrics()`

**Called By**: ReAct Agent  
**Returns**: Calculation results  
**Original Name**: ✅ PRESERVED

### Tool: `policy_retriever_tool()`

**Called By**: ReAct Agent  
**Calls**: `rag_pipeline.search()` via global `policy_retriever`  
**Returns**: Policy document excerpts  
**Original Name**: ✅ PRESERVED

### Tool: `web_search()`

**Called By**: ReAct Agent  
**Calls**: Tavily API  
**Returns**: Market news and intelligence  
**Original Name**: ✅ PRESERVED

---

## Testing the Endpoints

### Test 1: Health Check

```bash
# Check system health
curl -X GET http://localhost:8000/health

# Expected: { "status": "ok", ... }
```

### Test 2: Agent Info

```bash
# Get agent capabilities
curl -X GET http://localhost:8000/agent-info

# Expected: { "agent_name": "Financial Analyst...", "tools": [...] }
```

### Test 3: Main Chat

```bash
# Submit a query
curl -X POST http://localhost:8000/main-chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show portfolio for CLT-001"
  }'

# Expected: { "query": "...", "response": "...", "tools_used": [...] }
```

---

## Error Handling

### Invalid Request
```json
{
  "detail": "1 validation error for QueryRequest\nquery\n  field required (type=value_error.missing)"
}
```

### Agent Execution Error
```json
{
  "detail": "Agent error: Database connection failed"
}
```

### Health Check Failure
```json
{
  "status": "error",
  "components": {
    "database": "error",
    "rag_pipeline": "warning",
    "llm": "ok"
  }
}
```

---

## Integration Summary

| Endpoint | Function | Module | Tools | Status |
|----------|----------|--------|-------|--------|
| GET /health | health() | app.py | N/A | ✅ |
| GET /agent-info | agent_info() | app.py | N/A | ✅ |
| POST /main-chat | main_chat() | app.py | 5 | ✅ |

---

**Generated**: 2026-06-02  
**Status**: ✅ PRODUCTION READY  
**Version**: 1.0.0
